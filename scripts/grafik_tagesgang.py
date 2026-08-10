#!/usr/bin/env python3
"""Schreibt den Tagesgang „zu früh gegen zu spät" als PNG — ohne Notebook-Lauf.

    python3 scripts/grafik_tagesgang.py
    python3 scripts/grafik_tagesgang.py --netz ubahn --ziel /tmp/probe.png

Erzeugt `video/bild/tagesgang_frueh_spaet.png` (1920×1080).

Die Grafik gehört zu der Szene, in der aus einem Befund zwei Maßnahmen werden:
Die Verspätung folgt dem Straßenverkehr und hat ihr Maximum am Nachmittag, die
Verfrühung folgt der Nebenverkehrszeit und hat ihres am frühen Abend. Wer beides
in eine Kennzahl zusammenzieht, sieht keins von beidem.

Gezeichnet wird hier nichts — die Logik steht in `src/analysis/grafiken.py`,
dieselbe Quelle, die auch das Notebook benutzt. Beschriftungen ändert man dort im
Block `TEXTE_TAGESGANG` und ruft dieses Skript erneut auf; das dauert Sekunden
statt eines Notebook-Laufs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

from elasticsearch import Elasticsearch                        # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER      # noqa: E402
from src.analysis.grafiken import (                            # noqa: E402
    VERFRUEHT_SCHWELLE_S, fuers_video, tagesgang, tagesgang_anteile,
)
from src.analysis.quality import VERSPAETET_SCHWELLE_S         # noqa: E402

from export_grafiken import BREITE, HOEHE                      # noqa: E402

INDIZES = {"tram": "tram-departures-v2", "ubahn": "ubahn-departures-v2"}
STANDARDZIEL = WURZEL / "video" / "bild" / "tagesgang_frueh_spaet.png"


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frueh", type=int, default=abs(VERFRUEHT_SCHWELLE_S),
                   help=f"Verfrühung ab … Sekunden "
                        f"(Vorgabe: {abs(VERFRUEHT_SCHWELLE_S)})")
    p.add_argument("--spaet", type=int, default=VERSPAETET_SCHWELLE_S,
                   help=f"Verspätung ab … Sekunden "
                        f"(Vorgabe: {VERSPAETET_SCHWELLE_S})")
    p.add_argument("--netz", choices=["tram", "ubahn"], default="tram")
    p.add_argument("--ziel", type=Path, default=STANDARDZIEL)
    args = p.parse_args()

    schwelle_frueh = -abs(args.frueh)

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=300)
    werte = tagesgang_anteile(es, INDIZES[args.netz], schwelle_frueh, args.spaet)

    print(f"Fenster ]{schwelle_frueh} s, +{args.spaet} s[ — {args.netz}")
    print(werte.round(2).to_string(index=False))

    for spalte in ("zu früh (%)", "zu spät (%)"):
        i, j = werte[spalte].idxmax(), werte[spalte].idxmin()
        print(f"\n{spalte}: Maximum {werte.loc[i, spalte]:.1f} % um "
              f"{werte.loc[i, 'stunde']} Uhr, Minimum "
              f"{werte.loc[j, spalte]:.1f} % um {werte.loc[j, 'stunde']} Uhr")

    fig = tagesgang(werte, schwelle_frueh, args.spaet)
    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    fuers_video(fig).write_image(str(args.ziel), width=BREITE, height=HOEHE,
                                 scale=1)
    print(f"\ngeschrieben: {args.ziel.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
