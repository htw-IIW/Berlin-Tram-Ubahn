# src/analysis/takt.py
# Rekonstruiert den tatsächlichen Takt je Linie aus den Fahrplandaten und
# bewertet Verfrühungen nach ihren Folgekosten für Fahrgäste.
#
# Hintergrund: Eine verspätete Bahn kostet den Fahrgast die Verspätung.
# Eine zu frühe Bahn kostet ihn den gesamten Takt — wer pünktlich zur
# Fahrplanzeit an der Haltestelle steht, findet die Bahn bereits abgefahren
# vor und wartet bis zur nächsten. Die Bewertung einer Verfrühung hängt
# deshalb nicht von ihrer Größe ab, sondern vom Takt der Linie.
#
# ── Das Astproblem ───────────────────────────────────────────────────────────
#
# Die meisten Berliner Tramlinien verkehren nicht auf einem einzigen Linienweg,
# sondern in mehreren Ästen mit unterschiedlichen Endhaltestellen. Die Linie 27
# etwa bedient Mahlsdorf-Süd, Weißensee/Pasedagplatz, S Friedrichsfelde Ost und
# Hohenschönhausen/Gehrenseestr.
#
# Daraus folgen zwei verschiedene, jeweils korrekte Taktbegriffe:
#
#   Takt_Ast   Abstand zweier Fahrten desselben Astes. Maßgeblich für Fahrgäste,
#              die zu einer Endhaltestelle wollen, die nur ein Ast bedient.
#              Bei der 27: 20 Minuten.
#   Takt_alle  Abstand aufeinanderfolgender Fahrten der Linie an einer
#              Haltestelle, unabhängig vom Ast. Maßgeblich für Fahrgäste, die
#              nur wenige Stationen auf dem Stammabschnitt fahren und denen es
#              gleich ist, welcher Ast kommt. Bei der 27: 8 Minuten.
#
# Beide Gruppen existieren. Der effektive Takt ist deshalb eine Mischung:
#
#   Takt_eff = p · Takt_alle + (1 − p) · Takt_Ast
#
# Der Anteil p wird nicht geschätzt, sondern aus der Netzstruktur abgeleitet:
# Haltestellen, die von mehr als einem Ast bedient werden, sind mit jedem
# Fahrzeug der Linie erreichbar. Ihr Anteil an allen Haltestellen der Linie ist
# der Anteil der Fahrgäste, für die der Ast keine Rolle spielt — unter der
# Annahme gleichverteilter Fahrtziele.
#
# Für die 27 ergibt das p = 0,79 und einen effektiven Takt von rund
# 10,6 Minuten statt der 20 Minuten des Einzelastes.

import numpy as np
import pandas as pd
from elasticsearch.helpers import scan

# Referenzwoche für die Taktbestimmung: eine vollständige Woche im
# Regelbetrieb, außerhalb von Ferien und Collector-Ausfall.
TAKT_REFERENZ_VON = "2026-05-04"
TAKT_REFERENZ_BIS = "2026-05-09"

# Taktbestimmung nur im Tagesverkehr — nachts gelten andere Takte.
TAKT_STUNDE_VON = 6
TAKT_STUNDE_BIS = 20

# Abstände außerhalb dieser Grenzen sind keine Takte, sondern
# Doppelerfassungen bzw. Betriebspausen.
_ABSTAND_MIN_MIN = 1
_ABSTAND_MAX_MIN = 60


def _median_abstand(teil: pd.DataFrame, min_beobachtungen: int = 20) -> float:
    """Median-Abstand aufeinanderfolgender Fahrplanabfahrten in Minuten."""
    sortiert = teil.drop_duplicates("planned_when").sort_values("planned_when")
    abstaende = sortiert["planned_when"].diff().dt.total_seconds().dropna() / 60
    abstaende = abstaende[(abstaende > _ABSTAND_MIN_MIN) & (abstaende < _ABSTAND_MAX_MIN)]
    if len(abstaende) < min_beobachtungen:
        return np.nan
    return float(abstaende.median())


def _lade_fahrplan(es, index: str, linie: str, von: str, bis: str) -> pd.DataFrame:
    """Fahrplanabfahrten einer Linie in der Referenzwoche, ohne Betriebsfahrten."""
    from src.analysis.quality import ist_betriebliche_haltestelle

    treffer = scan(
        es, index=index, size=5000,
        query={"query": {"bool": {"filter": [
            {"term":  {"line_name": linie}},
            {"range": {"planned_when": {"gte": von, "lt": bis}}},
            {"range": {"hour_of_day": {"gte": TAKT_STUNDE_VON,
                                       "lte": TAKT_STUNDE_BIS}}},
        ]}}},
        _source=["planned_when", "stop_id", "stop_name", "direction"],
    )
    df = pd.DataFrame([t["_source"] for t in treffer])
    if df.empty:
        return df

    df["planned_when"] = pd.to_datetime(df["planned_when"], utc=True)
    # Ein- und Aussetzfahrten zum Betriebshof sind keine Fahrgastfahrten
    df = df[~df["direction"].str.contains("Betriebshof", na=False)]
    df = df[~df["stop_name"].apply(ist_betriebliche_haltestelle)]
    return df


def takt_je_linie(
    es,
    index: str,
    linien: list[str],
    von: str = TAKT_REFERENZ_VON,
    bis: str = TAKT_REFERENZ_BIS,
    min_haltestellen: int = 5,
) -> pd.DataFrame:
    """
    Takt je Linie in drei Varianten: Ast, Haltestelle, effektiv.

    Rückgabe je Linie:
        Aeste            Anzahl unterschiedlicher Fahrtziele (ohne Betriebshof)
        p_astunabhaengig Anteil der Haltestellen, die von >1 Ast bedient werden
        Takt_Ast_min     Median-Takt eines einzelnen Astes
        Takt_alle_min    Median-Takt aller Fahrten an einer Haltestelle
        Takt_eff_min     gewichteter effektiver Takt (siehe Modulkopf)
    """
    zeilen = []
    for linie in linien:
        df = _lade_fahrplan(es, index, linie, von, bis)
        if df.empty or df["stop_name"].nunique() < min_haltestellen:
            continue

        n_aeste = df["direction"].nunique()
        # p aus der Netzstruktur: Anteil der Haltestellen mit mehr als einem Ast
        aeste_je_halt = df.groupby("stop_name")["direction"].nunique()
        p = float((aeste_je_halt > 1).mean()) if n_aeste > 1 else 1.0

        je_halt = []
        for _, gruppe in df.groupby("stop_name"):
            t_alle = _median_abstand(gruppe)
            if np.isnan(t_alle):
                continue
            t_aeste = [
                _median_abstand(teil)
                for _, teil in gruppe.groupby("direction")
            ]
            t_aeste = [t for t in t_aeste if not np.isnan(t)]
            t_ast = float(np.median(t_aeste)) if t_aeste else t_alle
            je_halt.append({"t_alle": t_alle, "t_ast": t_ast,
                            "t_eff": p * t_alle + (1 - p) * t_ast})

        if not je_halt:
            continue
        h = pd.DataFrame(je_halt)
        zeilen.append({
            "Linie": linie,
            "Aeste": n_aeste,
            "p_astunabhaengig": p,
            "Takt_Ast_min":  h["t_ast"].median(),
            "Takt_alle_min": h["t_alle"].median(),
            "Takt_eff_min":  h["t_eff"].median(),
            "n_Haltestellen": len(h),
        })

    return pd.DataFrame(zeilen).sort_values("Takt_eff_min").reset_index(drop=True)


def puenktlichkeit_je_linie(
    es,
    index: str,
    frueh_schwelle_s: int = -60,
    spaet_schwelle_s: int = 180,
    max_linien: int = 30,
) -> pd.DataFrame:
    """Anteil zu früher, pünktlicher und zu später Abfahrten je Linie."""
    resp = es.search(
        index=index, size=0,
        query={"exists": {"field": "delay_s"}},
        aggs={"linien": {
            "terms": {"field": "line_name", "size": max_linien},
            "aggs": {
                "frueh": {"filter": {"range": {"delay_s": {"lte": frueh_schwelle_s}}}},
                "spaet": {"filter": {"range": {"delay_s": {"gte": spaet_schwelle_s}}}},
            },
        }},
    )
    zeilen = []
    for b in resp["aggregations"]["linien"]["buckets"]:
        n = b["doc_count"]
        zeilen.append({
            "Linie": b["key"],
            "n_Abfahrten": n,
            "zu_frueh_pct": b["frueh"]["doc_count"] / n * 100,
            "zu_spaet_pct": b["spaet"]["doc_count"] / n * 100,
        })
    df = pd.DataFrame(zeilen)
    df["puenktlich_pct"] = 100 - df["zu_frueh_pct"] - df["zu_spaet_pct"]
    return df


def verfruehungskosten(puenktlichkeit: pd.DataFrame, takte: pd.DataFrame) -> pd.DataFrame:
    """
    Erwarteter Zeitverlust je Fahrgastfahrt durch Verfrühungen.

        E[Verlust] = P(Abfahrt zu früh) × Takt_eff

    Als Taktgröße dient der effektive Takt, der Stamm- und Astfahrgäste
    gewichtet (siehe Modulkopf).

    **Annahme und ihre Grenzen:** Die Formel unterstellt, dass ein Fahrgast, der
    zur Fahrplanzeit eintrifft, die zu früh abgefahrene Bahn verpasst und den
    vollen Takt wartet. Das trifft auf Linien mit langem Takt zu, bei denen
    Fahrgäste den Fahrplan konsultieren. Bei kurzen Takten (unter etwa 5 Minuten)
    treffen Fahrgäste dagegen zufällig ein und richten sich nicht nach dem
    Fahrplan — dort überschätzt die Formel den Verlust.

    Die Kennzahl ist deshalb für den *Vergleich zwischen Linien mit langem Takt*
    belastbar, nicht als absoluter Schadenswert über alle Linien.
    """
    df = puenktlichkeit.merge(
        takte[["Linie", "Takt_eff_min", "Takt_Ast_min", "Takt_alle_min",
               "Aeste", "p_astunabhaengig"]],
        on="Linie", how="inner",
    )
    df["Verlust_frueh_min"] = df["zu_frueh_pct"] / 100 * df["Takt_eff_min"]
    df["Verlust_frueh_s"]   = df["Verlust_frueh_min"] * 60
    return df.sort_values("Verlust_frueh_min", ascending=False).reset_index(drop=True)
