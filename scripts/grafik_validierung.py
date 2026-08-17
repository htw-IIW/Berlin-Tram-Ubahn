#!/usr/bin/env python3
"""Schreibt die Validierungsgrafik für Szene 3 als PNG — ohne Notebook-Lauf.

    python3 scripts/grafik_validierung.py
    python3 scripts/grafik_validierung.py --monat "Jun 26" --ziel /tmp/probe.png

Erzeugt `video/bild/validierung_abstaende.png` (1920×1080).

Gezeigt wird der **Abstand zwischen Straßenbahn und U-Bahn**, einmal aus der
eigenen Erhebung und einmal aus dem Qualitätsmonitor der Senatsverwaltung — für
die Pünktlichkeit und für die Zuverlässigkeit.

── Warum keine absoluten Quoten ─────────────────────────────────────────────

Der Monitor zählt je Fahrt, diese Erhebung je Abfahrt an einer Haltestelle. Die
Niveaus liegen deshalb systematisch auseinander (Mai 2026: eigen 84,4 % gegen
amtlich 86,9 % bei der Tram) und dürfen nicht nebeneinandergestellt werden — das
sähe wie eine gescheiterte Replikation aus, obwohl der Unterschied erklärbar und
stabil ist. Übereinstimmen tun die Abstände, und nur die stehen im Bild.

Die Zahlen stammen aus derselben Rechnung wie `scripts/validierung_bvg.py` —
dieses Skript importiert sie von dort, damit Konsolenausgabe und Grafik nicht
auseinanderlaufen können. Die Zeichenlogik steht in `src/analysis/grafiken.py`
unter `validierungsvergleich()`; Beschriftungen dort im Block
`TEXTE_VALIDIERUNG` ändern und dieses Skript erneut aufrufen.

Voreingestellt ist **Mai 2026** — der einzige Monat, den die Erhebung vollständig
abdeckt. April beginnt am 27., Juni endet am 26. mit dem Collector-Ausfall.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

import pandas as pd                                             # noqa: E402
from elasticsearch import Elasticsearch                         # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER       # noqa: E402
from src.analysis.grafiken import (                             # noqa: E402
    fuers_video, validierungsvergleich,
)

from export_grafiken import BREITE, HOEHE                       # noqa: E402
from validierung_bvg import INDIZES, MONATE, eigene_werte, lies_csv  # noqa: E402

STANDARDZIEL = WURZEL / "video" / "bild" / "validierung_abstaende.png"

# Welche Kennzahlen ins Bild kommen. Links steht die Pünktlichkeit, rechts die
# Ausfälle — dass die Tram bei der einen zurückliegt und bei der anderen vorn,
# ist die zweite Aussage der Grafik und die Saat für Szene 8.
#
# Beide werden NEGATIV gewendet: `Pünktlichkeit` wird zu „außerhalb des
# Fensters", `Zuverlässigkeit` zu „ausgefallen". Begründung in
# src/analysis/grafiken.py über validierungsvergleich() — in der positiven
# Fassung liegen alle vier Balken zwischen 84 und 99 % und sehen gleich aus.
#
# Regelmäßigkeit und Verfrühungsvermeidung fehlen mit Absicht: Die erste lässt
# sich nicht nachrechnen (Zuordnung Fahrt -> Takt fehlt), die zweite ist der
# Überraschungsbefund und gehört nicht in die Validierungsszene.
KENNZAHLEN = [("unpünktlich", "Pünktlichkeit"),
              ("ausgefallen", "Zuverlässigkeit")]


def werte_fuer(es, monat: str) -> pd.DataFrame:
    """Anteile je Kennzahl, Quelle und Netz für einen Monat."""
    passend = [m for m in MONATE if m[0] == monat]
    if not passend:
        raise SystemExit(f"Monat {monat!r} nicht in MONATE — "
                         f"möglich: {', '.join(m[0] for m in MONATE)}")
    _, von, bis, hinweis = passend[0]

    eigen = {netz: eigene_werte(es, index, von, bis)
             for netz, index in INDIZES.items()}
    fehlend = [netz for netz, werte in eigen.items() if not werte]
    if fehlend:
        raise SystemExit(f"Keine eigenen Daten für {', '.join(fehlend)} "
                         f"im Zeitraum {von} bis {bis}")

    zeilen = []
    for kennzahl, amtlicher_name in KENNZAHLEN:
        amt = lies_csv(amtlicher_name).get(monat, {})
        if "Straßenbahn" not in amt or "U-Bahn" not in amt:
            raise SystemExit(
                f"Amtliche Werte für {amtlicher_name} fehlen in {monat}")
        # 100 minus, weil beide amtlichen Kennzahlen positiv definiert sind
        # (Anteil pünktlich bzw. Anteil erbracht) und die Grafik den Gegenwert
        # zeigt. Für die eigene Messung gilt dasselbe.
        zeilen.append({"Kennzahl": kennzahl, "Quelle": "meine Messung",
                       "Tram": 100 - eigen["Straßenbahn"][amtlicher_name],
                       "U-Bahn": 100 - eigen["U-Bahn"][amtlicher_name]})
        zeilen.append({"Kennzahl": kennzahl, "Quelle": "amtlich",
                       "Tram": 100 - amt["Straßenbahn"],
                       "U-Bahn": 100 - amt["U-Bahn"]})

    print(f"Monat {monat} ({hinweis}), n = "
          + ", ".join(f"{netz} {eigen[netz]['_n']:,}" for netz in INDIZES))
    return pd.DataFrame(zeilen)


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--monat", default="Mai 26",
                   help="Monat wie in validierung_bvg.MONATE (Vorgabe: Mai 26)")
    p.add_argument("--ziel", type=Path, default=STANDARDZIEL)
    args = p.parse_args()

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=600)
    werte = werte_fuer(es, args.monat)

    print()
    for zeile in werte.to_dict("records"):
        print(f"  {zeile['Kennzahl']:<12} {zeile['Quelle']:<14}"
              f"  Tram {zeile['Tram']:6.2f} %   U-Bahn {zeile['U-Bahn']:6.2f} %"
              f"   Verhältnis {max(zeile['Tram'], zeile['U-Bahn']) / min(zeile['Tram'], zeile['U-Bahn']):5.2f}×")

    fig = validierungsvergleich(werte, monat=args.monat.replace(" 26", " 2026"))
    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    fig = fuers_video(fig)
    # fuers_video setzt den oberen Rand pauschal auf 110 px. Der zweizeilige
    # Untertitel dieser Grafik braucht mehr, sonst laeuft der erste
    # Facettentitel hinein. Deshalb hier danach zurechtruecken.
    fig.update_layout(margin=dict(t=185, l=170, r=90, b=80))
    fig.write_image(str(args.ziel), width=BREITE, height=HOEHE, scale=1)
    print(f"\ngeschrieben: {args.ziel.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
