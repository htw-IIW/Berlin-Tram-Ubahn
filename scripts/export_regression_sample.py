#!/usr/bin/env python3
"""Exportiert eine geschichtete Zufallsstichprobe der Abfahrten als flache CSV.

Zweck: eine externe Regressionsanalyse außerhalb dieses Repos. Der Export
enthält deshalb bewusst **keine** aggregierten Kennzahlen als Hauptprodukt,
sondern die Beobachtungsebene — eine Zeile je Abfahrt, mit genau den Feldern,
die das JSON-Dokument in Elasticsearch führt.

── Was erzeugt wird ─────────────────────────────────────────────────────────

    data/export/messpunkte_tram_sample.csv     eine Zeile = ein Messpunkt
    data/export/segmente_tram_mittelwerte.csv  mittlere erzeugte Verspätung
                                               je Haltestellenpaar (Grundgesamtheit)
    data/export/CODEBOOK.md                    Spaltenbeschreibung + Designnotizen

── Wie gezogen wird ─────────────────────────────────────────────────────────

Zweistufig, weil die interessante Zielgröße — die zwischen zwei Haltestellen
*erzeugte* Verspätung — nur innerhalb einer Fahrt gebildet werden kann. Eine
Zufallsstichprobe einzelner Abfahrten würde die Fahrtstruktur zerreißen und
delta_delay unberechenbar machen.

  Stufe 1  Je Schicht (Erhebungstag x Stunde) werden `--trips-je-schicht`
           Abfahrten zufällig gezogen (Elasticsearch `random_score` mit festem
           Seed, damit der Lauf reproduzierbar ist). Behalten wird nur ihre
           `trip_id`.

  Stufe 2  Für diese Fahrten werden **alle** Halte geladen, auch die ohne
           Echtzeitwert. Innerhalb der Fahrt werden die Halte nach
           `planned_when` sortiert und die Differenzen gebildet — dieselbe
           Definition wie in `src/analysis/segmente.py`.

Die Schichtung sorgt dafür, dass jede Stunde und jeder Erhebungstag ähnlich
stark vertreten sind. Das ist ein *balanciertes* Design, kein repräsentatives:
Nachtstunden sind gegenüber ihrem tatsächlichen Verkehrsaufkommen deutlich
überrepräsentiert. Für Regressionen, die die Uhrzeit als Regressor führen, ist
das der Normalfall und gewollt. Für deskriptive Mittelwerte über den ganzen Tag
liegt die Spalte `gewicht` bei (siehe CODEBOOK.md).

── Aufruf ───────────────────────────────────────────────────────────────────

    python scripts/export_regression_sample.py
    python scripts/export_regression_sample.py --trips-je-schicht 8
    python scripts/export_regression_sample.py --netz ubahn
    python scripts/export_regression_sample.py --probelauf   # 3 Tage, schnell
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from config.settings import ES_HOST, ES_USER, ES_PASSWORD          # noqa: E402
from src.analysis.quality import (                                  # noqa: E402
    ANALYSE_START,
    ANALYSE_ENDE,
    COLLECTOR_AUSFALL_START,
    COLLECTOR_AUSFALL_ENDE,
    FREMDLINIEN,
    ist_betriebliche_haltestelle,
)
from src.analysis.segmente import (                                 # noqa: E402
    MAX_ABS_DELTA_S,
    MIN_BEOBACHTUNGEN_JE_SEGMENT,
    MIN_HALTE_JE_FAHRT,
)

# Die Indexnamen in config/settings.py zeigen auf die erste Generation der
# Indizes; erhoben wird seit dem Umbau in die v2-Indizes. Die Notebooks
# benutzen ebenfalls die hier stehenden Namen.
INDEX = {"tram": "tram-departures-v2", "ubahn": "ubahn-departures-v2"}

SEGMENT_PARQUET = WURZEL / "data" / "processed" / "segmente_tram_gesamt.parquet"
ZIEL = WURZEL / "data" / "export"

# Fester Seed: Zwei Läufe auf demselben Datenbestand ziehen dieselbe Stichprobe.
# Weil die Erhebung weiterläuft, ist das keine Garantie über Wochen hinweg —
# neu hinzugekommene Dokumente verschieben die Zufallsreihenfolge.
SEED = 20260809

# Vollständige Feldliste des Abfahrts-Dokuments. Wird explizit aufgeführt statt
# `_source: true` zu benutzen, damit die Spaltenreihenfolge der CSV stabil ist
# und ein neu hinzugekommenes Feld nicht stillschweigend die Datei verändert.
JSON_FELDER = [
    "collected_at", "planned_when", "when", "delay_s", "cancelled",
    "line_name", "line_id", "direction",
    "stop_id", "stop_name", "stop_location", "stop_sequence",
    "trip_id", "hour_of_day", "day_of_week", "is_weekend",
]

# Ein Tag, der weniger als diesen Anteil des Median-Tages erfasst hat, war kein
# Regelbetrieb des Collectors (14./15.05.2026, siehe DATASET.md 2b). Aus einer
# Handvoll Dokumente eine ganze Schicht zu ziehen würde die Stichprobe mit
# unvollständigen Fahrten füllen.
MIN_ANTEIL_JE_TAG = 0.5

# Stufe 1 zieht Dokumente, gebraucht werden aber verschiedene Fahrten. Da eine
# Fahrt rund 20 Halte hat, treffen zwei Ziehungen gelegentlich dieselbe Fahrt.
# Der Faktor gibt den Puffer.
UEBERZIEHFAKTOR = 4


# ── Elasticsearch ────────────────────────────────────────────────────────────

def verbinde() -> Elasticsearch:
    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=180)
    if not es.ping():
        raise SystemExit(f"Keine Verbindung zu {ES_HOST}")
    return es


def _grundfilter(netz: str) -> list[dict]:
    """Filterklauseln, die für jede Abfrage dieses Exports gelten."""
    return [{"exists": {"field": "delay_s"}}]


def _must_not(netz: str) -> list[dict]:
    # Fremdbetriebe (Linie 88, SRS) gehören nicht zur Grundgesamtheit
    # "BVG-Straßenbahn". Für die U-Bahn ist die Klausel wirkungslos.
    return [{"terms": {"line_name": list(FREMDLINIEN)}}]


def werktage(netz: str, es: Elasticsearch) -> list[pd.Timestamp]:
    """Werktage im Analysefenster ohne Collector-Ausfall und ohne Teiltage."""
    tage = pd.date_range(ANALYSE_START, ANALYSE_ENDE, freq="D", inclusive="both")
    ausfall_von = pd.Timestamp(COLLECTOR_AUSFALL_START)
    ausfall_bis = pd.Timestamp(COLLECTOR_AUSFALL_ENDE)

    kandidaten = [t for t in tage
                  if t.weekday() <= 4 and not (ausfall_von <= t < ausfall_bis)]

    # Dokumente je Tag zählen, um Teiltage zu erkennen.
    anfragen = []
    for tag in kandidaten:
        anfragen.append({"index": INDEX[netz]})
        anfragen.append({
            "size": 0, "track_total_hits": True,
            "query": {"bool": {
                "filter": _grundfilter(netz) + [{"range": {"planned_when": {
                    "gte": tag.strftime("%Y-%m-%d"),
                    "lt": (tag + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                }}}],
                "must_not": _must_not(netz),
            }},
        })
    antwort = es.msearch(searches=anfragen)
    zahlen = [r["hits"]["total"]["value"] for r in antwort["responses"]]

    median = pd.Series(zahlen).median()
    behalten, verworfen = [], []
    for tag, n in zip(kandidaten, zahlen):
        (behalten if n >= MIN_ANTEIL_JE_TAG * median else verworfen).append((tag, n))

    if verworfen:
        print("  Teiltage ausgeschlossen (< "
              f"{MIN_ANTEIL_JE_TAG:.0%} des Median-Tages von {median:,.0f} Dok.):")
        for tag, n in verworfen:
            print(f"    {tag.date()}  {n:>8,} Dokumente")

    return [tag for tag, _ in behalten]


def ziehe_fahrten(es: Elasticsearch, netz: str, tage: list[pd.Timestamp],
                  je_schicht: int) -> pd.DataFrame:
    """
    Stufe 1: je (Tag, Stunde) `je_schicht` zufällige Fahrten.

    Rückgabe: eine Zeile je gezogener Fahrt mit trip_id, Schicht und dem
    Gewicht, das sich aus der Schichtgröße ergibt.
    """
    zeilen: list[dict] = []
    gesehen: set[str] = set()

    for i, tag in enumerate(tage, 1):
        von = tag.strftime("%Y-%m-%d")
        bis = (tag + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        anfragen = []
        for stunde in range(24):
            anfragen.append({"index": INDEX[netz]})
            anfragen.append({
                "size": je_schicht * UEBERZIEHFAKTOR,
                "track_total_hits": True,
                "_source": ["trip_id"],
                "query": {"function_score": {
                    "query": {"bool": {
                        "filter": _grundfilter(netz) + [
                            {"range": {"planned_when": {"gte": von, "lt": bis}}},
                            {"term": {"hour_of_day": stunde}},
                        ],
                        "must_not": _must_not(netz),
                    }},
                    # Zufällige, aber reproduzierbare Reihenfolge. `_seq_no` als
                    # Feld ist die von Elasticsearch empfohlene Wahl; ohne
                    # Feldangabe wechselt das Ergebnis mit jedem Shard-Refresh.
                    "random_score": {"seed": SEED + stunde, "field": "_seq_no"},
                    "boost_mode": "replace",
                }},
                # Wie viele verschiedene Fahrten die Schicht überhaupt enthält —
                # Grundlage des Gewichts.
                "aggs": {"fahrten": {"cardinality": {"field": "trip_id"}}},
            })

        antwort = es.msearch(searches=anfragen)

        for stunde, r in enumerate(antwort["responses"]):
            treffer = r["hits"]["hits"]
            n_fahrten_schicht = r["aggregations"]["fahrten"]["value"]

            gewaehlt = []
            for t in treffer:
                tid = t["_source"]["trip_id"]
                if tid in gesehen:
                    continue
                gesehen.add(tid)
                gewaehlt.append(tid)
                if len(gewaehlt) >= je_schicht:
                    break

            for tid in gewaehlt:
                zeilen.append({
                    "trip_id": tid,
                    "stratum_datum": von,
                    "stratum_stunde": stunde,
                    "stratum_n_fahrten": n_fahrten_schicht,
                    "stratum_n_gezogen": len(gewaehlt),
                })

        print(f"  [{i:>2}/{len(tage)}] {tag.date()}  "
              f"{len(zeilen):>6,} Fahrten gezogen", end="\r")

    print()
    fahrten = pd.DataFrame(zeilen)
    # Designgewicht auf Fahrtebene: Kehrwert der Ziehungswahrscheinlichkeit.
    fahrten["gewicht"] = (fahrten["stratum_n_fahrten"]
                          / fahrten["stratum_n_gezogen"].clip(lower=1))
    return fahrten


def lade_halte(es: Elasticsearch, netz: str,
               trip_ids: list[str], block: int = 400) -> pd.DataFrame:
    """
    Stufe 2: alle Halte der gezogenen Fahrten, mit vollständigem _source.

    Anders als in Stufe 1 wird hier **nicht** auf `delay_s` gefiltert. Halte
    ohne Echtzeitwert gehören zur Fahrt und sind für die Frage, wo Echtzeitdaten
    fehlen, selbst eine Information.
    """
    zeilen: list[dict] = []
    for start in range(0, len(trip_ids), block):
        teil = trip_ids[start:start + block]
        treffer = scan(
            es, index=INDEX[netz], size=5_000, scroll="30m",
            query={"query": {"terms": {"trip_id": teil}}},
            _source=JSON_FELDER,
        )
        for t in treffer:
            quelle = t["_source"]
            quelle["doc_id"] = t["_id"]
            zeilen.append(quelle)
        print(f"  {min(start + block, len(trip_ids)):>6,}/{len(trip_ids):,} "
              f"Fahrten geladen — {len(zeilen):>8,} Halte", end="\r")
    print()
    return pd.DataFrame(zeilen)


# ── Aufbereitung ─────────────────────────────────────────────────────────────

def flach_machen(df: pd.DataFrame) -> pd.DataFrame:
    """`stop_location` ist im JSON ein Objekt — hier wird es zu zwei Spalten."""
    ort = df["stop_location"].apply(
        lambda o: (o or {}) if isinstance(o, dict) else {})
    df["stop_lat"] = ort.apply(lambda o: o.get("lat"))
    df["stop_lon"] = ort.apply(lambda o: o.get("lon"))
    return df.drop(columns=["stop_location"])


def erzeugte_verspaetung(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bildet je Fahrt die Differenz aufeinanderfolgender Halte.

    Gleiche Definition wie `src.analysis.segmente.segmente_aus_fahrten`:
    Reihenfolge aus `planned_when` (das Feld `stop_sequence` ist im Index
    durchgängig leer), Differenz nur über Halte mit Echtzeitwert.

    Abweichung: Es wird hier weder gekappt noch nach Mindestzahl gefiltert.
    Die Kappungsgrenze steht stattdessen als Merker `delta_plausibel` in der
    Zeile, damit der Ausschluss außerhalb dieses Repos sichtbar bleibt.
    """
    df = df.sort_values(["trip_id", "planned_when"]).copy()
    df["halt_index"] = df.groupby("trip_id").cumcount() + 1
    df["n_halte_fahrt"] = df.groupby("trip_id")["stop_name"].transform("size")

    # Differenzen nur über die Halte mit Echtzeitwert bilden. Fehlt ein Halt in
    # der Mitte, überspannt das entstehende Paar zwei echte Abschnitte — solche
    # Pseudo-Abschnitte erkennt man später am kleinen `segment_n`.
    mit_echtzeit = df[df["delay_s"].notna()].copy()
    gruppe = mit_echtzeit.groupby("trip_id")
    mit_echtzeit["stop_from"] = gruppe["stop_name"].shift(1)
    mit_echtzeit["stop_from_id"] = gruppe["stop_id"].shift(1)
    mit_echtzeit["delay_vorher_s"] = gruppe["delay_s"].shift(1)
    mit_echtzeit["delta_delay_s"] = (mit_echtzeit["delay_s"]
                                     - mit_echtzeit["delay_vorher_s"])

    neu = ["stop_from", "stop_from_id", "delay_vorher_s", "delta_delay_s"]
    df = df.join(mit_echtzeit[neu])

    # Nullable boolean: Wo keine Differenz gebildet werden konnte, ist die
    # Frage nach der Plausibilität leer und nicht "False".
    df["delta_plausibel"] = (df["delta_delay_s"].abs() <= MAX_ABS_DELTA_S
                             ).astype("boolean")
    df.loc[df["delta_delay_s"].isna(), "delta_plausibel"] = pd.NA
    return df


def anreichern(df: pd.DataFrame, fahrten: pd.DataFrame,
               segmente: pd.DataFrame | None) -> pd.DataFrame:
    df = df.merge(
        fahrten[["trip_id", "stratum_datum", "stratum_stunde",
                 "stratum_n_fahrten", "stratum_n_gezogen", "gewicht"]],
        on="trip_id", how="left",
    )

    zeit = pd.to_datetime(df["planned_when"], format="ISO8601", utc=True)
    lokal = zeit.dt.tz_convert("Europe/Berlin")
    df["datum"] = lokal.dt.date.astype(str)
    df["uhrzeit"] = lokal.dt.strftime("%H:%M")
    df["minute_im_tag"] = lokal.dt.hour * 60 + lokal.dt.minute

    df["hat_echtzeit"] = df["delay_s"].notna()
    df["ist_betriebshalt"] = df["stop_name"].fillna("").apply(
        ist_betriebliche_haltestelle)

    if segmente is not None:
        df = df.merge(
            segmente.rename(columns={
                "mittel_delta": "segment_mittel_delta_s",
                "std_delta": "segment_std_delta_s",
                "n": "segment_n",
            })[["stop_from", "stop_to", "segment_mittel_delta_s",
                "segment_std_delta_s", "segment_n"]],
            left_on=["stop_from", "stop_name"],
            right_on=["stop_from", "stop_to"],
            how="left",
        ).drop(columns=["stop_to"])
    else:
        for spalte in ("segment_mittel_delta_s", "segment_std_delta_s",
                       "segment_n"):
            df[spalte] = pd.NA

    return df


SPALTEN_REIHENFOLGE = [
    # Schlüssel
    "doc_id", "trip_id",
    # Feld für Feld das JSON-Dokument
    "collected_at", "planned_when", "when", "delay_s", "cancelled",
    "line_name", "line_id", "direction",
    "stop_id", "stop_name", "stop_lat", "stop_lon", "stop_sequence",
    "hour_of_day", "day_of_week", "is_weekend",
    # abgeleitete Zeitangaben
    "datum", "uhrzeit", "minute_im_tag",
    # Position in der Fahrt und erzeugte Verspätung
    "halt_index", "n_halte_fahrt",
    "stop_from", "stop_from_id", "delay_vorher_s",
    "delta_delay_s", "delta_plausibel",
    "segment_mittel_delta_s", "segment_std_delta_s", "segment_n",
    # Qualitätsmerker
    "hat_echtzeit", "ist_betriebshalt",
    # Stichprobendesign
    "stratum_datum", "stratum_stunde", "stratum_n_fahrten",
    "stratum_n_gezogen", "gewicht",
]


# ── Codebook ─────────────────────────────────────────────────────────────────

def schreibe_codebook(pfad: Path, netz: str, df: pd.DataFrame,
                      n_fahrten: int, n_tage: int, je_schicht: int,
                      segment_datei: str | None) -> None:
    anteil_echtzeit = df["hat_echtzeit"].mean()
    stunden = df["hour_of_day"].value_counts().sort_index()
    stunden_zeile = "  ".join(f"{h:02d}h {n:,}" for h, n in stunden.items())

    pfad.write_text(f"""# Codebook — Stichprobenexport für die externe Regressionsanalyse

Erzeugt von `scripts/export_regression_sample.py` am {time.strftime('%d.%m.%Y')}.
Netz: **{netz}**, Index `{INDEX[netz]}`.

## Dateien

| Datei | Inhalt |
|---|---|
| `messpunkte_{netz}_sample.csv` | eine Zeile je Abfahrt (Messpunkt), {len(df):,} Zeilen |
| `{segment_datei or '—'}` | mittlere erzeugte Verspätung je Haltestellenpaar, Grundgesamtheit |

## Stichprobendesign

Geschichtete Zufallsstichprobe **auf Fahrtebene**, Schicht = Erhebungstag x Stunde.

| | |
|---|---|
| Analysefenster | {ANALYSE_START} bis {ANALYSE_ENDE}, nur Werktage |
| Ausgeschlossen | Collector-Ausfall {COLLECTOR_AUSFALL_START} bis {COLLECTOR_AUSFALL_ENDE}, Teiltage, Linie {'/'.join(FREMDLINIEN)} (Fremdbetrieb) |
| Erhebungstage | {n_tage} |
| Schichten | {n_tage} x 24 = {n_tage * 24:,} |
| Fahrten je Schicht (Soll) | {je_schicht} |
| Gezogene Fahrten | {n_fahrten:,} |
| Halte (Zeilen) | {len(df):,} |
| davon mit Echtzeitwert | {anteil_echtzeit:.1%} |
| Zufallsseed | {SEED} |

Gezogen wird die **Fahrt**, nicht der einzelne Halt: Die erzeugte Verspätung
zwischen zwei Haltestellen ist eine Differenz innerhalb einer Fahrt und lässt
sich aus unabhängig gezogenen Einzelabfahrten nicht bilden. Von jeder gezogenen
Fahrt sind **alle** Halte enthalten, auch die ohne Echtzeitwert.

Die Schicht bezieht sich auf die Abfahrt, über die die Fahrt in die Stichprobe
kam. Eine Fahrt läuft über eine Stundengrenze hinweg, deshalb ist die
Stundenverteilung der **Zeilen** nur annähernd, nicht exakt gleichmäßig:

```
{stunden_zeile}
```

### Gewichtung

Das Design ist über Stunden **balanciert**, nicht proportional: Nachtstunden
sind gegenüber ihrem tatsächlichen Verkehrsaufkommen stark überrepräsentiert.

* Für **Regressionen**, die die Uhrzeit als Regressor führen, ist das gewollt
  und die Spalte `gewicht` wird nicht gebraucht — die Schichtvariable steht im
  Modell.
* Für **deskriptive Mittelwerte über den ganzen Tag** muss mit `gewicht`
  gewichtet werden, sonst zieht der Nachtverkehr das Ergebnis.

`gewicht` = Zahl der Fahrten in der Schicht / Zahl der daraus gezogenen Fahrten.
Näherung: Die Schichtgröße stammt aus einer `cardinality`-Aggregation
(HyperLogLog++, bei diesen Größenordnungen praktisch exakt), und eine Fahrt, die
zwei Stunden überspannt, hätte in beiden Schichten gezogen werden können.

## Spalten

### Das JSON-Dokument, Feld für Feld

| Spalte | Typ | Bedeutung |
|---|---|---|
| `doc_id` | text | Elasticsearch `_id`: `trip_id-stop_id-planned_when` |
| `trip_id` | text | BVG-Fahrt-ID. Enthält das Datum, ist also nicht tagesübergreifend |
| `collected_at` | ISO-8601 (UTC) | Zeitpunkt der letzten Erfassung dieser Abfahrt |
| `planned_when` | ISO-8601 (+02:00) | Fahrplanmäßige Abfahrt |
| `when` | ISO-8601 (+02:00) | Prognostizierte/tatsächliche Abfahrt, leer ohne Echtzeitdaten |
| `delay_s` | ganze Zahl | Verspätung in Sekunden, negativ = zu früh |
| `cancelled` | bool | Fahrt ausgefallen |
| `line_name` | text | Linie, z. B. `M2` |
| `line_id` | text | interne VBB-Linien-ID |
| `direction` | text | Fahrtziel (Endhaltestelle) |
| `stop_id` | text | BVG-Haltestellen-ID |
| `stop_name` | text | Haltestellenname |
| `stop_lat`, `stop_lon` | Dezimalgrad | aus dem `geo_point`-Objekt `stop_location` aufgetrennt |
| `stop_sequence` | — | im Index durchgängig leer (die API liefert es nicht) |
| `hour_of_day` | 0–23 | aus `planned_when` abgeleitet, im Index gespeichert |
| `day_of_week` | 0–6 | 0 = Montag |
| `is_weekend` | bool | fast durchgängig `False` (nur Werktage); `True` nur für die Halte einer Freitagnacht-Fahrt nach Mitternacht |

### Abgeleitete Zeitangaben

| Spalte | Bedeutung |
|---|---|
| `datum` | Kalendertag der planmäßigen Abfahrt, Ortszeit Berlin |
| `uhrzeit` | `HH:MM` der planmäßigen Abfahrt, Ortszeit |
| `minute_im_tag` | 0–1439, für stetige Tageszeitverläufe (Splines, Fourier-Terme) |

`datum` weicht bei Fahrten über Mitternacht vom `stratum_datum` ab: Gezogen wird
die Fahrt über eine ihrer Abfahrten, enthalten sind alle ihre Halte — auch die
jenseits des Datumswechsels. Die Zahl der Kalendertage in der Datei ist deshalb
um eins höher als die Zahl der Erhebungstage.

### Erzeugte Verspätung zwischen den Haltestellen

| Spalte | Bedeutung |
|---|---|
| `halt_index` | Position dieses Halts in der Fahrt, 1 = erster erfasster Halt |
| `n_halte_fahrt` | Zahl der erfassten Halte dieser Fahrt |
| `stop_from` | vorhergehender Halt **mit Echtzeitwert** derselben Fahrt |
| `stop_from_id` | dessen `stop_id` |
| `delay_vorher_s` | `delay_s` an `stop_from` |
| `delta_delay_s` | **`delay_s` − `delay_vorher_s`** — die auf dem Abschnitt `stop_from` → `stop_name` erzeugte Verspätung |
| `delta_plausibel` | `False`, wenn \\|`delta_delay_s`\\| > {MAX_ABS_DELTA_S} s |
| `segment_mittel_delta_s` | Mittel von `delta_delay_s` für dieses Haltestellenpaar über den **gesamten** Erhebungszeitraum |
| `segment_std_delta_s` | dessen Standardabweichung |
| `segment_n` | Zahl der Beobachtungen, auf denen der Mittelwert beruht |

`delta_delay_s` ist die eigentlich auswertbare Größe. Die Verspätung an einer
Haltestelle ist überwiegend **geerbt** — eine Fahrt, die spät im Linienverlauf
steht, ist verspätet, unabhängig davon, was an dieser Haltestelle geschieht. Wer
Haltestellen nach mittlerer `delay_s` sortiert, misst deshalb vor allem die
Position in der Linie. Die Differenz ist um diesen Upstream-Effekt bereinigt.

Zwei Fallstricke:

1. **`delta_delay_s` ist minutenquantisiert.** Alle `delay_s`-Werte sind exakte
   Vielfache von 60 — die BVG-API meldet ganze Minuten, die Sekundenangabe ist
   eine Umrechnung, keine Messung. Differenzen springen deshalb in
   60-s-Schritten. Mittelwerte über viele Beobachtungen bleiben präzise (die
   Rundung trägt rund 17,3/√n Sekunden zum Standardfehler bei), Mediane
   einzelner Abfahrten liegen fast immer auf 0.
2. **Pseudo-Abschnitte.** Fehlt ein Zwischenhalt in der Erfassung, verbindet
   `stop_from` → `stop_name` zwei echte Abschnitte und weist deren Verspätung
   zusammen aus. Solche Paare sind selten und erkennbar an kleinem `segment_n`;
   die Analysen in diesem Projekt filtern auf `segment_n >= {MIN_BEOBACHTUNGEN_JE_SEGMENT:,}`
   (das lässt {'763 von 5.724 Paaren übrig, deckt aber 98,8 % aller Beobachtungen ab'}).
   Fahrten mit weniger als {MIN_HALTE_JE_FAHRT} Halten erlauben keine sinnvolle
   Differenzbildung.

### Qualitätsmerker

| Spalte | Bedeutung |
|---|---|
| `hat_echtzeit` | `delay_s` vorhanden. Fehlende Echtzeitdaten sind vermutlich **nicht** zufällig verteilt |
| `ist_betriebshalt` | Betriebshof, `[Ausstieg]`, `[Endstelle]` — dort steht das Fahrzeug planmäßig länger, die „Verspätung" erlebt kein Fahrgast. **Vor der Auswertung ausschließen.** |

Eckige Klammern im Haltestellennamen sind für sich **kein** Ausschlussgrund:
Die meisten unterscheiden nur Bahnsteige derselben Haltestelle
(`U Alexanderplatz (Berlin) [Tram]`) und sind reguläre Halte.

### Stichprobendesign

| Spalte | Bedeutung |
|---|---|
| `stratum_datum`, `stratum_stunde` | Schicht, über die die Fahrt gezogen wurde |
| `stratum_n_fahrten` | Zahl der Fahrten in dieser Schicht (Grundgesamtheit) |
| `stratum_n_gezogen` | Zahl der daraus gezogenen Fahrten |
| `gewicht` | `stratum_n_fahrten / stratum_n_gezogen` |

## Was diese Daten nicht hergeben

* **Keine Jahresaussagen.** Erhoben wurde vom 27.04. an, also Frühjahr und
  Sommer — rund ein Viertel des Jahres. Vereisung, Laubfall und Schneeräumung
  liegen außerhalb des Fensters und treffen ausschließlich die Tram.
* **Keine Zeittrends über den 08.07.2026 hinweg.** Die Echtzeitabdeckung springt
  an diesem Tag in beiden Netzen deutlich nach oben (Tram 81 % → 96 %). Ein
  Anstieg der gemessenen Verspätung über diese Grenze hinweg kann allein aus der
  veränderten Erfassung stammen. Querschnittsvergleiche über das ganze Fenster
  sind zulässig.
* **`cancelled` ist nach dem 08.07. für die U-Bahn unbrauchbar** (Quote fällt von
  1,16 % auf 0,06 %, mehrere Tage mit exakt null Ausfällen bei ~76.000
  Abfahrten). Die Tram macht den Bruch nicht mit.

Vollständig in `DATASET.md`, Abschnitt *Known Data Characteristics*.
""", encoding="utf-8")


# ── Ablauf ───────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--netz", choices=("tram", "ubahn"), default="tram")
    p.add_argument("--trips-je-schicht", type=int, default=3,
                   help="Fahrten je (Tag, Stunde). 3 ergibt rund 110.000 Zeilen "
                        "bei rund 45 MB; der Wert skaliert linear.")
    p.add_argument("--probelauf", action="store_true",
                   help="nur die ersten drei Tage — für einen schnellen Test")
    args = p.parse_args()

    ZIEL.mkdir(parents=True, exist_ok=True)
    beginn = time.time()

    print(f"Netz: {args.netz}  ({INDEX[args.netz]})")
    es = verbinde()

    print("\n1/5  Erhebungstage bestimmen …")
    tage = werktage(args.netz, es)
    if args.probelauf:
        tage = tage[:3]
    print(f"  {len(tage)} Werktage, {len(tage) * 24:,} Schichten")

    print(f"\n2/5  Fahrten ziehen ({args.trips_je_schicht} je Schicht) …")
    fahrten = ziehe_fahrten(es, args.netz, tage, args.trips_je_schicht)
    print(f"  {len(fahrten):,} verschiedene Fahrten")

    print("\n3/5  Halte laden …")
    df = lade_halte(es, args.netz, fahrten["trip_id"].tolist())
    print(f"  {len(df):,} Halte")

    print("\n4/5  Erzeugte Verspätung berechnen und anreichern …")
    segmente = None
    segment_datei = None
    if args.netz == "tram" and SEGMENT_PARQUET.exists():
        segmente = pd.read_parquet(SEGMENT_PARQUET)
        segment_datei = f"segmente_{args.netz}_mittelwerte.csv"
        ziel_seg = ZIEL / segment_datei
        segmente.to_csv(ziel_seg, index=False, float_format="%.4f")
        print(f"  {len(segmente):,} Haltestellenpaare  ->  {ziel_seg.name}")
    elif args.netz == "ubahn":
        print("  Keine Segment-Mittelwerte für die U-Bahn vorhanden "
              "(segmente_tram_gesamt.parquet ist tram-spezifisch) — "
              "die Spalten segment_* bleiben leer.")

    df = flach_machen(df)
    df = erzeugte_verspaetung(df)
    df = anreichern(df, fahrten, segmente)
    df = df[SPALTEN_REIHENFOLGE].sort_values(
        ["stratum_datum", "stratum_stunde", "trip_id", "halt_index"])

    print("\n5/5  Schreiben …")
    ziel_csv = ZIEL / f"messpunkte_{args.netz}_sample.csv"
    df.to_csv(ziel_csv, index=False, float_format="%.6g")
    schreibe_codebook(ZIEL / "CODEBOOK.md", args.netz, df, len(fahrten),
                      len(tage), args.trips_je_schicht, segment_datei)

    mb = ziel_csv.stat().st_size / 1e6
    print(f"  {ziel_csv}  ({len(df):,} Zeilen, {mb:.1f} MB)")
    print(f"  {ZIEL / 'CODEBOOK.md'}")

    print("\nKontrolle")
    print(f"  Fahrten                 {df['trip_id'].nunique():,}")
    print(f"  Erhebungstage           {df['datum'].nunique()}")
    print(f"  Haltestellen            {df['stop_name'].nunique():,}")
    print(f"  Linien                  {df['line_name'].nunique()}")
    print(f"  mit Echtzeitwert        {df['hat_echtzeit'].mean():.1%}")
    print(f"  mit delta_delay_s       {df['delta_delay_s'].notna().mean():.1%}")
    print(f"  Betriebshalte           {df['ist_betriebshalt'].mean():.2%}")
    stunden = df["hour_of_day"].value_counts()
    print(f"  Zeilen je Stunde        min {stunden.min():,}  "
          f"median {int(stunden.median()):,}  max {stunden.max():,}")
    tage_n = df["datum"].value_counts()
    print(f"  Zeilen je Tag           min {tage_n.min():,}  "
          f"median {int(tage_n.median()):,}  max {tage_n.max():,}")
    print(f"\nLaufzeit {time.time() - beginn:.0f} s")


if __name__ == "__main__":
    main()
