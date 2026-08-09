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
#
# ── Warum es zwei Deltas gibt ────────────────────────────────────────────────
#
# `delta_delay` hat eine Eigenschaft, die man kennen muss: Es behandelt eine
# Verfrühung als negative Verspätung und rechnet beides gegeneinander auf. Eine
# Fahrt, die 60 s zu früh ankommt und 120 s zu früh weiterfährt, bekommt
# delta_delay = −60 — sie sieht aus, als hätte sie Verspätung abgebaut,
# obwohl sie in Wahrheit weiter aus dem Fahrplan gelaufen ist.
#
# Das ist keine Kleinigkeit. Gemessen über den Erhebungszeitraum:
#
#     19,5 %  aller Segmentbeobachtungen starten verfrüht
#     +9,87 s Ø delta_delay, wenn die Fahrt verfrüht startet
#     −0,68 s Ø delta_delay, wenn sie es nicht tut
#     50,5 %  aller negativen Deltas sind Fahrzeuge, die weiter vorlaufen
#
# Der positive Netzmittelwert von +1,38 s entsteht also praktisch vollständig
# dadurch, dass verfrühte Fahrzeuge zum Fahrplan zurückkehren.
#
#     delta_verspaetung = max(delay_(i+1), 0) − max(delay_i, 0)
#
# schneidet den Fahrplan bei null ab und misst nur noch die Veränderung der
# Verspätung. Eine Verfrühung trägt überall 0 bei und kann deshalb keine
# Verspätung ausgleichen. Beispiele:
#
#     vorher   nachher   delta_delay   delta_verspaetung
#     +120 s   +180 s        +60 s          +60 s   wird später
#     +180 s   +120 s        −60 s          −60 s   holt auf
#      −60 s   −120 s        −60 s            0 s   läuft weiter vor
#     −120 s    −60 s        +60 s            0 s   nähert sich dem Fahrplan
#      +30 s    −30 s        −60 s          −30 s   verliert nur seine 30 s
#
# Die Verfrühung geht dabei nicht verloren, sie wird nur woanders gemessen:
# als Anteil verfrühter Abfahrten je Haltestelle (Notebook 03, Abschnitt 5).
# Eine Änderung und ein Niveau sind zwei verschiedene Größen; sie in eine Zahl
# zu pressen war der Fehler.
#
# `delta_delay` bleibt erhalten und wird weiter berechnet — Notebook 04, 05
# und 06 und der Zwischenstand segmente_tram_gesamt.parquet rechnen damit.
# Für die Frage "wo entsteht Verspätung?" ist `delta_verspaetung` die richtige
# Größe.

import pathlib
from collections import defaultdict

import pandas as pd
from elasticsearch.helpers import scan

from src.analysis.quality import FREMDLINIEN

# Fahrten mit weniger Beobachtungen erlauben keine sinnvolle Differenzbildung.
MIN_HALTE_JE_FAHRT = 3

# Mindestzahl Beobachtungen je Haltestellenpaar.
#
# Der Wert ist bewusst hoch. Wenn eine Zwischenhaltestelle nicht erfasst wurde,
# entsteht ein Paar, das zwei echte Abschnitte überspannt und deren Verspätung
# zusammen ausweist. Solche Pseudo-Abschnitte sind selten und fallen über eine
# Mindestanzahl heraus. Der Effekt ist erheblich: Über den Gesamtzeitraum liegt
# die höchste mittlere erzeugte Verspätung bei
#
#     n >=   20   ->  261 s   (überwiegend Pseudo-Abschnitte)
#     n >=  500   ->   59 s
#     n >= 2000   ->   59 s   (stabil)
#
# Bei n >= 2000 bleiben 763 von 5.724 Paaren übrig, die aber 98,8 % aller
# Beobachtungen abdecken — es geht praktisch keine Information verloren.
MIN_BEOBACHTUNGEN_JE_SEGMENT = 2000

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

    # Fremdbetriebe (siehe quality.FREMDLINIEN). Praktisch wirkungslos, weil
    # die betroffene Linie ohnehin keine delay_s-Werte liefert und schon an
    # der exists-Bedingung scheitert — steht hier, damit die Grundgesamtheit
    # nicht von einer Nebenbedingung abhängt, sondern ausgesprochen ist.
    # scroll="30m" statt der Voreinstellung von 5 Minuten: Der Suchkontext muss
    # zwischen zwei Batches am Leben bleiben. Auf dem Raspberry Pi dauert ein
    # Batch bei mehreren Wochen Zeitraum gelegentlich länger als fünf Minuten,
    # dann bricht der Lauf mit "NotFoundError: No search context found" ab —
    # nach mehreren Minuten Wartezeit und mitten in der Abfrage.
    treffer = scan(
        es, index=index, size=10_000, scroll="30m",
        query={"query": {"bool": {
            "filter": filter_klauseln,
            "must_not": [{"terms": {"line_name": list(FREMDLINIEN)}}],
        }}},
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
    # format="ISO8601" ist zwingend: Zeitstempel werden im Index mal mit,
    # mal ohne Mikrosekunden serialisiert; ohne Angabe leitet pandas das
    # Format aus dem ersten Wert ab und scheitert an der anderen Variante.
    df["planned_when"] = pd.to_datetime(df["planned_when"], utc=True,
                                        format="ISO8601")
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

    # Zweite Fassung derselben Differenz, in der eine Verfrühung nicht gegen
    # eine Verspätung aufgerechnet wird — siehe Kommentar oben, Abschnitt
    # "Warum es zwei Deltas gibt".
    df["delay_to"]   = df["delay_s"]
    df["delay_from"] = gruppe["delay_s"].shift(1)

    verspaetung     = df["delay_to"].clip(lower=0)
    verspaetung_vor = df["delay_from"].clip(lower=0)
    df["delta_verspaetung"] = verspaetung - verspaetung_vor

    segmente = df.dropna(subset=["stop_from", "delta_delay"]).copy()
    # Gefiltert wird weiter über delta_delay: Die Grenze fängt zurückgezogene
    # Prognosen ab, und die zeigen sich im rohen Sprung, nicht in der
    # abgeschnittenen Fassung.
    segmente = segmente[segmente["delta_delay"].abs() <= MAX_ABS_DELTA_S]
    # delay_from und delay_to werden mitgegeben, damit die Wahl des Deltas
    # nachprüfbar ist, ohne die Fahrten ein zweites Mal zu laden. Ohne sie
    # lässt sich aus den beiden Differenzen nicht mehr rekonstruieren, welche
    # Beobachtung verfrüht war — und genau das ist die Zahl, mit der die
    # Umstellung begründet wird.
    return segmente[["trip_id", "line_name", "stop_from", "stop_to",
                     "delay_from", "delay_to",
                     "delta_delay", "delta_verspaetung", "planned_when"]]


def segmente_gesamtzeitraum(
    es,
    index: str,
    von: str,
    bis: str,
    ausfall_ueberspringen: bool = True,
    nur_werktags: bool = True,
    cache_pfad: str | None = None,
    fortschritt: bool = True,
) -> pd.DataFrame:
    """
    Segmentaggregate über den **gesamten** Erhebungszeitraum.

    Warum tageweise: Der volle Zeitraum umfasst rund 9,8 Mio. Abfahrten mit
    Echtzeitdaten. Diese gleichzeitig im Speicher zu halten ist nicht praktikabel.
    Da eine Fahrt nie über Mitternacht hinaus dieselbe trip_id behält, lassen sich
    die Differenzen tageweise bilden, ohne dass Segmente verlorengehen. Mitgeführt
    werden nur die Aggregate je Haltestellenpaar — Summe, Quadratsumme und Anzahl —,
    aus denen sich Mittelwert und Streuung am Ende exakt rekonstruieren lassen.

    Der Collector-Ausfall wird standardmäßig übersprungen (siehe quality.py):
    An diesen Tagen fehlen einzelne Halte innerhalb von Fahrten, wodurch
    Haltestellenpaare entstünden, die im Linienverlauf nicht benachbart sind.

    Rückgabe: eine Zeile je (stop_from, stop_to) mit
        mittel_delta, std_delta, n, summe_delta, summe_positiv
    """
    from src.analysis.quality import (
        COLLECTOR_AUSFALL_START, COLLECTOR_AUSFALL_ENDE,
    )

    if cache_pfad:
        cache = pathlib.Path(cache_pfad)
        if cache.exists():
            if fortschritt:
                print(f"Lade zwischengespeichertes Ergebnis: {cache}")
            return pd.read_parquet(cache)

    tage = pd.date_range(von, bis, freq="D", inclusive="left")
    ausfall_von = pd.Timestamp(COLLECTOR_AUSFALL_START)
    ausfall_bis = pd.Timestamp(COLLECTOR_AUSFALL_ENDE)

    # Akkumulatoren je Haltestellenpaar
    summe:   dict[tuple[str, str], float] = defaultdict(float)
    quadrat: dict[tuple[str, str], float] = defaultdict(float)
    anzahl:  dict[tuple[str, str], int]   = defaultdict(int)
    positiv: dict[tuple[str, str], float] = defaultdict(float)

    n_tage_genutzt = 0
    for tag in tage:
        if nur_werktags and tag.weekday() > 4:
            continue
        if ausfall_ueberspringen and ausfall_von <= tag < ausfall_bis:
            continue

        naechster = (tag + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        tages_df = lade_fahrten(
            es, index, von=tag.strftime("%Y-%m-%d"), bis=naechster,
            max_dokumente=400_000, nur_werktags=False,
        )
        if tages_df.empty:
            continue

        tages_segmente = segmente_aus_fahrten(tages_df)
        if tages_segmente.empty:
            continue

        gruppiert = tages_segmente.groupby(["stop_from", "stop_to"])["delta_delay"]
        for schluessel, werte in gruppiert:
            summe[schluessel]   += float(werte.sum())
            quadrat[schluessel] += float((werte ** 2).sum())
            anzahl[schluessel]  += int(werte.size)
            positiv[schluessel] += float(werte[werte > 0].sum())

        n_tage_genutzt += 1
        if fortschritt:
            print(f"  {tag.date()}  {len(tages_segmente):>7,} Segmente  "
                  f"(Tag {n_tage_genutzt})", end="\r")

    if fortschritt:
        print(f"\nVerarbeitete Tage: {n_tage_genutzt}")

    zeilen = []
    for schluessel, n in anzahl.items():
        mittel = summe[schluessel] / n
        # Varianz aus Summe und Quadratsumme (numerisch ausreichend bei diesen Größen)
        varianz = max(quadrat[schluessel] / n - mittel ** 2, 0.0)
        zeilen.append({
            "stop_from": schluessel[0], "stop_to": schluessel[1],
            "mittel_delta": mittel,
            "std_delta": varianz ** 0.5,
            "n": n,
            "summe_delta": summe[schluessel],
            "summe_positiv": positiv[schluessel],
        })

    ergebnis = (pd.DataFrame(zeilen)
                .sort_values("mittel_delta", ascending=False)
                .reset_index(drop=True))
    ergebnis.attrs["n_tage"] = n_tage_genutzt

    if cache_pfad:
        cache = pathlib.Path(cache_pfad)
        cache.parent.mkdir(parents=True, exist_ok=True)
        ergebnis.to_parquet(cache, index=False)
        if fortschritt:
            print(f"Ergebnis zwischengespeichert: {cache}")

    return ergebnis


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
    spalte: str = "delta_delay",
) -> pd.DataFrame:
    """
    Erzeugte Verspätung je *Zielhaltestelle*, gemittelt über alle Zufahrten.

    Das ist die Größe, die mit der LSA-Ausstattung einer Haltestelle
    verglichen wird: Wie viel Verspätung entsteht auf dem Weg *zu* dieser
    Haltestelle — also im Zulauf auf die dortige Kreuzung.

    `spalte` wählt zwischen den beiden Deltas (siehe Kopf dieser Datei):
    `delta_delay` verrechnet Verfrühung gegen Verspätung, `delta_verspaetung`
    tut das nicht. Die Vorgabe bleibt `delta_delay`, damit die bestehenden
    Aufrufe in Notebook 04, 05 und 06 unverändert weiterrechnen; Notebook 03
    fordert seit dem 09.08.2026 ausdrücklich `delta_verspaetung` an.

    Die Ergebnisspalte heißt in beiden Fällen `erzeugte_verspaetung_s`. Welche
    Fassung darin steht, steht in `agg.attrs["quelle"]`.
    """
    agg = (
        segmente.groupby("stop_to")
        .agg(erzeugte_verspaetung_s=(spalte, "mean"),
             std_s=(spalte, "std"),
             n_beobachtungen=(spalte, "size"),
             n_linien=("line_name", "nunique"))
        .reset_index()
        .rename(columns={"stop_to": "stop_name"})
    )
    agg.attrs["quelle"] = spalte
    agg = agg[agg["n_beobachtungen"] >= min_beobachtungen]
    return agg.sort_values("erzeugte_verspaetung_s", ascending=False).reset_index(drop=True)
