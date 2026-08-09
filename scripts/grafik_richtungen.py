#!/usr/bin/env python3
"""Schreibt die Grafik „Verfrühung gegen Verspätung" als PNG — ohne Notebook-Lauf.

Gedacht zum Feilen an den Beschriftungen: Ein voller Export über `01_eda.ipynb`
dauert rund zehn Minuten, dieses Skript wenige Sekunden.

    python3 scripts/grafik_richtungen.py                    # Standardschwellen
    python3 scripts/grafik_richtungen.py --spaet 60         # zu spät ab 1 Minute
    python3 scripts/grafik_richtungen.py --ziel /tmp/x.png  # woanders hinschreiben

**Texte ändern:** im Block `TEXTE` in `src/analysis/grafiken.py`. Gezeichnet wird
hier nichts — das Skript ruft dieselbe Funktion auf, die auch das Notebook und
`scripts/export_grafiken.py` benutzen. Es kann deshalb nicht davon abweichen.

Die Schriftgrößen kommen aus `export_grafiken._lesbar_machen`, damit das Ergebnis
Pixel für Pixel dem regulären Export entspricht.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

from elasticsearch import Elasticsearch                       # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER     # noqa: E402
from src.analysis.grafiken import (                           # noqa: E402
    VERFRUEHT_SCHWELLE_S, anteile_pro_richtung, fuers_video, richtungsvergleich,
)
from src.analysis.quality import VERSPAETET_SCHWELLE_S        # noqa: E402

# Bildgröße aus dem Exportskript, damit sie nicht auseinanderlaufen kann. Die
# Schriftumrechnung liegt in src/analysis/grafiken.fuers_video und wird vom
# Export ebenfalls von dort geholt. Der Import ist gefahrlos — export_grafiken
# hat einen __main__-Riegel.
from export_grafiken import BREITE, HOEHE                     # noqa: E402

STANDARDZIEL = WURZEL / "video" / "bild" / "richtungen_frueh_spaet.png"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frueh", type=int, default=abs(VERFRUEHT_SCHWELLE_S),
                   help="Verfrühung ab … Sekunden (Vorgabe: 60)")
    p.add_argument("--spaet", type=int, default=VERSPAETET_SCHWELLE_S,
                   help="Verspätung ab … Sekunden (Vorgabe: 180)")
    p.add_argument("--ziel", type=Path, default=STANDARDZIEL)
    args = p.parse_args()

    schwelle_frueh = -abs(args.frueh)

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=300)
    anteile = anteile_pro_richtung(es, schwelle_frueh, args.spaet)
    print(anteile.round(2).to_string(index=False))

    tram, ubahn = anteile.set_index("Netz").loc["Tram"], anteile.set_index("Netz").loc["U-Bahn"]
    print(f"\nzu früh (ab {abs(schwelle_frueh) // 60} min): Faktor "
          f"{tram['zu früh (%)'] / ubahn['zu früh (%)']:.2f}")
    print(f"zu spät (ab {args.spaet // 60} min): Faktor "
          f"{tram['zu spät (%)'] / ubahn['zu spät (%)']:.2f}")

    fig = richtungsvergleich(anteile, schwelle_frueh, args.spaet)
    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    fuers_video(fig).write_image(str(args.ziel), width=BREITE, height=HOEHE,
                                 scale=1)
    print(f"\ngeschrieben: {args.ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
