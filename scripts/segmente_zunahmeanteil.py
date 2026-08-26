#!/usr/bin/env python3
"""Je Abschnitt: Anteil der Fahrten, auf denen die Verspätung zunimmt.

    python3 scripts/segmente_zunahmeanteil.py

Schreibt `data/processed/segmente_tram_zunahmeanteil.parquet` mit einer Zeile
je Haltestellenpaar:

    stop_from, stop_to, n, n_zunahme, anteil_zunahme

── Warum das ein eigener Lauf sein muss ────────────────────────────────────

`segmente_tram_gesamt.parquet` führt Summe, Quadratsumme und Anzahl je Paar mit
— daraus lassen sich Mittelwert und Streuung exakt rekonstruieren, aber **kein
Anteil**. Wie viele Fahrten oberhalb von null lagen, steht dort nicht und lässt
sich aus einer Summe nicht zurückrechnen. Dafür müssen die Einzelbeobachtungen
noch einmal durchlaufen werden.

Der Lauf dauert wie der ursprüngliche rund sieben Minuten. Deshalb schreibt er
sein Ergebnis daneben — **das bestehende Parquet wird nicht angefasst**, es ist
laut CLAUDE.md ein teuer berechneter Zwischenstand und wird von vier Notebooks
gelesen.

── Die Zählweise ───────────────────────────────────────────────────────────

Gezählt wird `delta_delay > 0`: Auf dieser Fahrt ist die Tram auf diesem
Abschnitt später geworden. Weil `delay_s` minutenquantisiert ist (DATASET.md
Nr. 1), heißt das in der Sache „mindestens eine Minute dazu" — kleinere
Zunahmen kann der Datensatz nicht auflösen.

Abschnitte, auf denen Verspätung ABGEBAUT wird, zählen als nicht zugenommen,
also mit 0 — sie ziehen den Anteil nicht ins Minus. Genau darin unterscheidet
sich diese Größe vom Mittelwert `mittel_delta`, in dem sich Zunahme und Abbau
gegenseitig aufheben.

Zeitraum, Werktagsregel und Collector-Ausfall folgen `segmente_gesamtzeitraum()`
— dieselben Tage, damit die beiden Parquets zusammenpassen.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

import pandas as pd                                            # noqa: E402
from elasticsearch import Elasticsearch                        # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER      # noqa: E402
from src.analysis.quality import (                             # noqa: E402
    ANALYSE_ENDE, ANALYSE_START,
    COLLECTOR_AUSFALL_ENDE, COLLECTOR_AUSFALL_START,
)
from src.analysis.segmente import (                            # noqa: E402
    lade_fahrten, segmente_aus_fahrten,
)

INDEX = "tram-departures-v2"
ZIEL = WURZEL / "data" / "processed" / "segmente_tram_zunahmeanteil.parquet"


def main() -> int:
    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=900)

    tage = pd.date_range(ANALYSE_START, ANALYSE_ENDE, freq="D", inclusive="both")
    ausfall_von = pd.Timestamp(COLLECTOR_AUSFALL_START)
    ausfall_bis = pd.Timestamp(COLLECTOR_AUSFALL_ENDE)

    anzahl: dict[tuple[str, str], int] = defaultdict(int)
    zunahme: dict[tuple[str, str], int] = defaultdict(int)
    genutzt = 0

    for tag in tage:
        if tag.weekday() > 4:
            continue
        if ausfall_von <= tag < ausfall_bis:
            continue

        naechster = (tag + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        df = lade_fahrten(es, INDEX, von=tag.strftime("%Y-%m-%d"),
                          bis=naechster, max_dokumente=400_000,
                          nur_werktags=False)
        if df.empty:
            continue
        segmente = segmente_aus_fahrten(df)
        if segmente.empty:
            continue

        for schluessel, werte in segmente.groupby(
                ["stop_from", "stop_to"])["delta_delay"]:
            anzahl[schluessel] += int(werte.size)
            zunahme[schluessel] += int((werte > 0).sum())

        genutzt += 1
        print(f"  {tag.date()}  {len(segmente):>7,} Segmente  (Tag {genutzt})",
              end="\r")

    print(f"\nVerarbeitete Tage: {genutzt}")

    ergebnis = pd.DataFrame([
        {"stop_from": a, "stop_to": b, "n": n,
         "n_zunahme": zunahme[(a, b)],
         "anteil_zunahme": zunahme[(a, b)] / n * 100}
        for (a, b), n in anzahl.items()
    ]).sort_values("anteil_zunahme", ascending=False).reset_index(drop=True)

    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    ergebnis.to_parquet(ZIEL, index=False)
    print(f"Paare: {len(ergebnis):,}")
    print(f"geschrieben: {ZIEL.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
