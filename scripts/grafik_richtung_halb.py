#!/usr/bin/env python3
"""Schreibt die Richtungsgrafik als zwei Hälften — je eine PNG-Datei.

    python3 scripts/grafik_richtung_halb.py
    python3 scripts/grafik_richtung_halb.py --grenze 20     # Achse erzwingen

Erzeugt beide Bilder in einem Lauf (je 1920×1080):

    video/bild/richtung_spaet.png   Szene 5  — nur die Verspätung, nach rechts
    video/bild/richtung_frueh.png   Szene 8  — nur die Verfrühung, nach links

Es ist dieselbe Grafik wie `richtungen_frueh_spaet.png`, an der Nulllinie
zerlegt. Im Film läuft die rechte Hälfte in Szene 5 und die linke erst in
Szene 8 — der Zuschauer hält die erste also eine Weile für das ganze Bild.

── Warum beide Bilder ein Skript sind ───────────────────────────────────────

Der Achsenrand wird EINMAL aus beiden Richtungen berechnet und an beide Hälften
weitergereicht. Getrennt gezeichnet bekäme jede Hälfte ihren eigenen Maßstab,
und der jeweils längste Balken wäre in beiden Bildern gleich lang: 6,2 % in
Szene 5 sähen aus wie 10,5 % in Szene 8. Die Pointe der Verfrühungsszene hängt
genau an diesem Größenunterschied — deshalb gibt es hier keinen Schalter, um nur
eine Hälfte zu schreiben.

Wer den Ausschnitt trotzdem festlegen will, nimmt `--grenze`; der Wert gilt dann
für beide.

**Texte ändern:** im Block `TEXTE_HALB` in `src/analysis/grafiken.py`. Gezeichnet
wird hier nichts, das Skript ruft `richtungsvergleich_halb()` auf.
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
    VERFRUEHT_SCHWELLE_S, achsenrand, anteile_pro_richtung, fuers_video,
    richtungsvergleich_halb,
)
from src.analysis.quality import VERSPAETET_SCHWELLE_S        # noqa: E402

from export_grafiken import BREITE, HOEHE                     # noqa: E402

ORDNER = WURZEL / "video" / "bild"
ZIELE = {"spaet": ORDNER / "richtung_spaet.png",
         "frueh": ORDNER / "richtung_frueh.png"}


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
    p.add_argument("--grenze", type=float, default=None,
                   help="Achsenrand in Prozent für BEIDE Hälften "
                        "(Vorgabe: aus den Daten)")
    p.add_argument("--ordner", type=Path, default=ORDNER)
    args = p.parse_args()

    schwelle_frueh = -abs(args.frueh)

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=300)
    anteile = anteile_pro_richtung(es, schwelle_frueh, args.spaet)
    print(anteile.round(2).to_string(index=False))

    grenze = args.grenze if args.grenze is not None else achsenrand(anteile)
    werte = anteile.set_index("Netz")
    print(f"\ngemeinsamer Achsenrand: {grenze:.0f} %")

    args.ordner.mkdir(parents=True, exist_ok=True)
    for richtung, schwelle, spalte in [("spaet", args.spaet, "zu spät (%)"),
                                       ("frueh", schwelle_frueh, "zu früh (%)")]:
        fig = fuers_video(richtungsvergleich_halb(anteile, richtung, schwelle,
                                                  grenze))
        # fuers_video setzt den Rand pauschal auf l=90/r=60. Zu wenig für die
        # Netznamen — „U-Bahn" lief in den Rand hinein. Die Namen stehen auf der
        # Seite der Nulllinie, der breite Rand wandert deshalb mit der Richtung.
        #
        # Oben nur 60 px: Das Bild hat keinen Titel mehr, der Platz gehört den
        # Balken.
        rand = 175
        fig.update_layout(margin=dict(
            t=60, b=110,
            l=rand if richtung == "spaet" else 70,
            r=70 if richtung == "spaet" else rand))
        ziel = args.ordner / ZIELE[richtung].name
        fig.write_image(str(ziel), width=BREITE, height=HOEHE, scale=1)
        faktor = werte.loc["Tram", spalte] / werte.loc["U-Bahn", spalte]
        print(f"  {richtung:5}  Tram {werte.loc['Tram', spalte]:5.2f} %   "
              f"U-Bahn {werte.loc['U-Bahn', spalte]:5.2f} %   "
              f"Faktor {faktor:5.2f}×   → {ziel.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
