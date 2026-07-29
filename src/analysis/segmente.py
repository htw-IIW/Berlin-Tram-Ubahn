# src/analysis/segmente.py
# Berechnet, wie viel Verspätung auf dem Weg zwischen zwei Haltestellen
# *entsteht* — im Unterschied zur Verspätung, die eine Fahrt dort bereits hat.
#
# ── Warum diese Größe gebraucht wird ─────────────────────────────────────────
#
# Die Verspätung an einer Haltestelle ist überwiegend geerbt: Eine Fahrt, die
# spät im Linienverlauf liegt, ist verspätet, unabhängig davon, was an dieser
# Haltestelle geschieht. Wer Haltestellen nach ihrer mittleren Verspätung
# sortiert, misst deshalb vor allem die Position in der Linie — nicht die
# örtliche Ursache.
#
# Die Differenz
#
#     delta_delay_i = delay_(i+1) − delay_i
#
# misst dagegen die *auf diesem Abschnitt erzeugte* Verspätung. Sie ist um den
# Upstream-Effekt bereinigt und damit die kausal auswertbare Größe.
#
# Für die LSA-Analyse in Notebook 03 ist das zusätzlich deshalb entscheidend,
# weil delta_delay unabhängig von der Ausreißerdefinition ist, mit der dort
# die Gruppe "potentiell ineffektiv" gebildet wurde. Ein Test auf delta_delay
# ist damit nicht zirkulär.

import pandas as pd
from elasticsearch.helpers import scan

# Fahrten mit weniger Beobachtungen erlauben keine sinnvolle Differenzbildung.
MIN_HALTE_JE_FAHRT = 3

# Segmente, die seltener beobachtet wurden, sind statistisch nicht belastbar.
MIN_BEOBACHTUNGEN_JE_SEGMENT = 20

# Differenzen jenseits dieser Grenze stammen aus zurückgezogenen Prognosen
# oder Fahrplanwechseln, nicht aus dem Betrieb (vgl. NB 01, Befund 5).
MAX_ABS_DELTA_S = 600


def lade_fahrten(
    es,
    index: str,
    von: str,
    bis: str,
    max_dokumente: int = 1_200_000,
    nur_werktags: bool = True,
) -> pd.DataFrame:
    """
    Lädt Abfahrten mit Echtzeitdaten für die Segmentanalyse.

    Es werden nur die fünf benötigten Felder geladen, damit auch Zeiträume von
    mehreren Wochen in den Speicher passen.
    """
    filter_klauseln = [
        {"exists": {"field": "delay_s"}},
        {"range": {"planned_when": {"gte": von, "lt": bis}}},
    ]
    if nur_werktags:
        filter_klauseln.append({"range": {"day_of_week": {"lte": 4}}})

    treffer = scan(
        es, index=index, size=10_000,
        query={"query": {"bool": {"filter": filter_klauseln}}},
        _source=["trip_id", "planned_when", "delay_s", "stop_name", "line_name"],
    )

    zeilen = []
    for i, t in enumerate(treffer):
        if i >= max_dokumente:
            break
        zeilen.append(t["_source"])

    df = pd.DataFrame(zeilen)
    if df.empty:
        return df
    df["planned_when"] = pd.to_datetime(df["planned_when"], utc=True)
    return df


def segmente_aus_fahrten(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bildet je Fahrt die Differenzen aufeinanderfolgender Halte.

    Die Reihenfolge innerhalb einer Fahrt ergibt sich aus `planned_when`.
    Das Feld `stop_sequence` wäre der direktere Weg, ist im Index aber
    durchgängig leer — die BVG-API liefert es beim Abfahrts-Endpunkt nicht
    (siehe DATASET.md).
    """
    df = df.sort_values(["trip_id", "planned_when"])

    gruppe = df.groupby("trip_id")
    # Nur Fahrten mit genügend Halten
    genug = gruppe["stop_name"].transform("size") >= MIN_HALTE_JE_FAHRT
    df = df[genug].copy()

    df["stop_to"]      = df["stop_name"]
    df["stop_from"]    = gruppe["stop_name"].shift(1)
    df["delta_delay"]  = df["delay_s"] - gruppe["delay_s"].shift(1)

    segmente = df.dropna(subset=["stop_from", "delta_delay"]).copy()
    segmente = segmente[segmente["delta_delay"].abs() <= MAX_ABS_DELTA_S]
    return segmente[["trip_id", "line_name", "stop_from", "stop_to",
                     "delta_delay", "planned_when"]]


def segment_aggregat(
    segmente: pd.DataFrame,
    min_beobachtungen: int = MIN_BEOBACHTUNGEN_JE_SEGMENT,
) -> pd.DataFrame:
    """Mittlere erzeugte Verspätung je Segment (stop_from → stop_to)."""
    agg = (
        segmente.groupby(["stop_from", "stop_to"])
        .agg(mittel_delta=("delta_delay", "mean"),
             std_delta=("delta_delay", "std"),
             n=("delta_delay", "size"))
        .reset_index()
    )
    agg = agg[agg["n"] >= min_beobachtungen]
    return agg.sort_values("mittel_delta", ascending=False).reset_index(drop=True)


def zufluss_je_haltestelle(
    segmente: pd.DataFrame,
    min_beobachtungen: int = 100,
) -> pd.DataFrame:
    """
    Erzeugte Verspätung je *Zielhaltestelle*, gemittelt über alle Zufahrten.

    Das ist die Größe, die mit der LSA-Ausstattung einer Haltestelle
    verglichen wird: Wie viel Verspätung entsteht auf dem Weg *zu* dieser
    Haltestelle — also im Zulauf auf die dortige Kreuzung.
    """
    agg = (
        segmente.groupby("stop_to")
        .agg(erzeugte_verspaetung_s=("delta_delay", "mean"),
             std_s=("delta_delay", "std"),
             n_beobachtungen=("delta_delay", "size"),
             n_linien=("line_name", "nunique"))
        .reset_index()
        .rename(columns={"stop_to": "stop_name"})
    )
    agg = agg[agg["n_beobachtungen"] >= min_beobachtungen]
    return agg.sort_values("erzeugte_verspaetung_s", ascending=False).reset_index(drop=True)
