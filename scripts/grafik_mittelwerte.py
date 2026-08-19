#!/usr/bin/env python3
"""Schreibt die beiden Mittelwerte für Szene 4 als eine PNG-Grafik.

    python3 scripts/grafik_mittelwerte.py

Erzeugt `video/bild/mittelwerte_netze.png` (1920×1080): zwei große Zahlen
nebeneinander, Straßenbahn rot und U-Bahn blau.

Ersetzt die zwei Kibana-Kacheln aus `scripts/kibana_kacheln.py` durch ein
einziges Bild. Grund: In einer Lens-Metric teilen sich alle Kacheln dieselbe
statische Farbe, sobald ein Breakdown gesetzt ist — Rot und Blau nebeneinander
gibt es dort nur als zwei getrennte Panels, und die werden im Dashboard schnell
riesig. Die Kibana-Fassung bleibt trotzdem nützlich, wenn im Video einmal die
Datenbank selbst zu sehen sein soll.

Gerechnet wird mit demselben Filter wie die Kibana-Kacheln — Basisfilter aus
KIBANA.md Abschnitt 0.3 und der Zeitraum der Erhebung —, damit beide Fassungen
dieselbe Zahl zeigen.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

from elasticsearch import Elasticsearch                         # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER       # noqa: E402
from src.analysis.grafiken import (                             # noqa: E402
    fuers_video, kennzahl_kacheln,
)

from export_grafiken import BREITE, HOEHE                       # noqa: E402
from kibana_kacheln import BIS, VON                             # noqa: E402

STANDARDZIEL = WURZEL / "video" / "bild" / "mittelwerte_netze.png"

INDIZES = {"Tram": "tram-departures-v2", "U-Bahn": "ubahn-departures-v2"}

# Dieselben Ausschlüsse wie der Basisfilter in KIBANA.md 0.3. Als Wildcard-Query
# statt KQL, weil hier direkt gegen Elasticsearch gefragt wird.
AUSSCHLUSS = ["Betriebshof*", "*[Ausstieg]", "*[Endstelle]"]


def mittelwerte(es) -> dict[str, float]:
    heraus = {}
    for netz, index in INDIZES.items():
        antwort = es.search(
            index=index, size=0, track_total_hits=True,
            query={"bool": {
                "filter": [
                    {"exists": {"field": "delay_s"}},
                    {"range": {"collected_at": {"gte": VON, "lte": BIS}}},
                ],
                "must_not": [{"wildcard": {"stop_name": {"value": muster}}}
                             for muster in AUSSCHLUSS],
            }},
            aggs={"mittel": {"avg": {"field": "delay_s"}}})
        heraus[netz] = antwort["aggregations"]["mittel"]["value"]
        print(f"  {netz:7} n = {antwort['hits']['total']['value']:>10,}   "
              f"Ø {heraus[netz]:6.2f} s   → im Bild "
              f"{round(heraus[netz]):.0f} s")
    return heraus


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ziel", type=Path, default=STANDARDZIEL)
    args = p.parse_args()

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=600)
    werte = mittelwerte(es)

    zeitraum = f"{VON[8:10]}.{VON[5:7]}. bis {BIS[8:10]}.{BIS[5:7]}.{BIS[:4]}"
    fig = fuers_video(kennzahl_kacheln(werte, zeitraum))
    # fuers_video setzt den oberen Rand auf 110 px; der zweizeilige Titel
    # dieser Grafik braucht mehr.
    fig.update_layout(margin=dict(t=200, l=60, r=60, b=60))

    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(args.ziel), width=BREITE, height=HOEHE, scale=1)
    print(f"\ngeschrieben: {args.ziel.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
