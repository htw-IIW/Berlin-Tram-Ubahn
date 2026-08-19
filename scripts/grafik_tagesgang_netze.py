#!/usr/bin/env python3
"""Tagesgang der Verspätung, Tram gegen U-Bahn — als PNG für den Videoschnitt.

    python3 scripts/grafik_tagesgang_netze.py

Erzeugt `video/bild/tagesgang_netze.png` (1920×1080): zwei übereinanderliegende
Felder, oben die Straßenbahn, unten die U-Bahn, dazu die schattierten
Hauptverkehrszeiten.

── Wozu ────────────────────────────────────────────────────────────────────

Die Grafik prüft die naheliegendste Erklärung für Verspätung: den
Berufsverkehr. Wären volle Bahnen und langer Fahrgastwechsel die Ursache,
müsste das Maximum in der Hauptverkehrszeit liegen.

    U-Bahn   Maximum 16 Uhr, 4,1 %   — genau dort, wo man es erwartet
    Tram     Maximum 22 Uhr, 9,9 %   — mit einem Nebengipfel um 16 Uhr

Um 22 Uhr wechselt der Tram-Fahrplan vom 10- auf den 20-Minuten-Takt
(Referenzwoche 04.–08.05.2026). Die U-Bahn wechselt zur selben Zeit von 5 auf
10 Minuten und bekommt trotzdem keinen Gipfel — die Taktumstellung allein
erklärt den Befund also **nicht**. Belegt ist nur, dass es nicht der
Berufsverkehr ist.

── Nur Werktage ────────────────────────────────────────────────────────────

`is_weekend: false`. Am Wochenende gibt es keinen Berufsverkehr, gegen den sich
prüfen ließe; die Wochenendfahrten würden die Hauptverkehrszeiten verwischen.

── Gemessen wird der Anteil zu später Abfahrten, nicht der Mittelwert ───────

Der Mittelwert über alle Abfahrten verrechnet Verfrühung gegen Verspätung. Um
19 Uhr fährt die Tram so oft zu früh, dass ihr Mittelwert auf 9,8 s fällt — die
Kurve sähe dort nach einem Bestwert aus, obwohl 27,8 % ihrer Abfahrten
verspätet sind. Der Anteil jenseits von `VERSPAETET_SCHWELLE_S` hat dieses
Problem nicht: Verfrühte Abfahrten zählen nicht mit und können nichts
ausgleichen.

**Texte ändern:** Block `TEXTE_TAGESGANG_NETZE` in `src/analysis/grafiken.py`.
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
    INDIZES_NETZE, SPALTE_SPAET, fuers_video, tagesgang_netze_anteile,
    tagesgang_netzvergleich,
)

from export_grafiken import BREITE, HOEHE                      # noqa: E402

STANDARDZIEL = WURZEL / "video" / "bild" / "tagesgang_netze.png"
INDIZES = INDIZES_NETZE
SPALTE = SPALTE_SPAET


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--alle-tage", action="store_true",
                   help="auch Samstag und Sonntag (Vorgabe: nur Mo–Fr)")
    p.add_argument("--ziel", type=Path, default=STANDARDZIEL)
    args = p.parse_args()

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=900)
    w = tagesgang_netze_anteile(es, nur_werktage=not args.alle_tage)

    for netz in INDIZES:
        t = w[w["Netz"] == netz]
        gipfel = t.loc[t[SPALTE].idxmax()]
        mittel = (t[SPALTE] * t["n"]).sum() / t["n"].sum()
        print(f"  {netz:7} Tagesmittel {mittel:5.2f} %   "
              f"Maximum {gipfel[SPALTE]:5.2f} % um {int(gipfel['stunde']):2d} Uhr   "
              f"n = {int(t['n'].sum()):,}")

    fig = fuers_video(tagesgang_netzvergleich(w, SPALTE))
    # Kein Titel im Bild — die Überschrift kommt im Schnitt dazu.
    fig.update_layout(margin=dict(t=70, b=110, l=140, r=80))

    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(args.ziel), width=BREITE, height=HOEHE, scale=1)
    print(f"\ngeschrieben: {args.ziel.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
