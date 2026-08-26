#!/usr/bin/env python3
"""Die Obergrenze der Verspätungsbekämpfung — als PNG für den Videoschnitt.

    python3 scripts/grafik_ohne_verspaetung.py

Erzeugt DREI Bilder (je 1920×1080) und schreibt die Werte nach
`video/animationen/ohne-verspaetung.json` für die Animation:

    video/bild/ohne_verspaetung.png    Szene 7   — keine Fahrt mehr zu spät
    video/bild/ohne_verfruehung.png    Szene 8/9 — keine Fahrt mehr zu früh
    video/bild/abfahrtsdisziplin.png   Szene 9b  — Verfrühung auf U-Bahn-Niveau

Alle drei teilen sich Aufbau UND y-Achse (bis 100 %) und lassen sich deshalb im
Schnitt übereinanderlegen. Wer eine skaliert, muss die anderen mitziehen.

Die dritte ist die einzige, deren Annahme nicht unmöglich ist: Sie setzt die
Verfrühung der Tram nicht auf null, sondern auf das, was die U-Bahn im selben
Monat nachweislich schon fährt (rund 1 % gegen rund 10 %). Die Verspätung bleibt
dabei ausdrücklich auf ihrem gemessenen Wert stehen — die Linie zeigt, was
allein die Abfahrtsdisziplin hergibt. Ergebnis: 92,8 % mengengewichtet, Ziel in
drei von vier Monaten erreicht. Die Einschränkungen unten gelten unverändert
auch für sie.

── Wozu ────────────────────────────────────────────────────────────────────

Zu Szene 7: „Selbst wenn ab morgen keine einzige Tram mehr zu spät käme,
stiege die Quote auf 89,6 Prozent. Vertraglich geschuldet sind 92,3."

Die Grafik ist der Monatswertegrafik der Senatsverwaltung nachgebaut
(`video/bild/Monatswerte pünktlichkeit.png`), aber vollständig aus der eigenen
Erhebung gerechnet — eine Quelle, eine Schwelle, kein Umrechnungsfaktor:

    so pünktlich war die Tram          Fenster ]−120 s, +240 s[
    ohne jede zu späte Abfahrt         100 minus Verfrühungsanteil
    ohne jede zu frühe Abfahrt         100 minus Verspätungsanteil
    vertraglich geschuldet             92,3 %, Jahressollwert aus data/bvg/

Die zweite Hypothese gehört in die spätere Szene und dreht das Ergebnis um:
Ohne Verfrühungen wäre das Ziel in drei der vier Monate erreicht (Juni
verfehlt es mit 92,21 gegen 92,30 % knapp). Mengengewichtet 93,80 % gegen
89,51 % der Verspätungsfassung.

── Die Monatsgrenzen sind nicht die Kalendergrenzen ────────────────────────

Der Collector-Ausfall (27.06.–08.07., `quality.py`) wird über die Grenzen
ausgeklammert statt gefiltert. Juni endet deshalb am 26., Juli beginnt am 8.
August ist ein angebrochener Monat — die Erhebung läuft weiter.

**Das steht NICHT im Bild.** Eine Fußzeile mit diesen Einschränkungen war da
und ist auf Wunsch der Nutzerin wieder raus: Die Grafik ist der Senatsvorlage
nachgebaut, und die trägt unten nur die Quellenzeile. Wer die Monatspunkte
gegen einen Kalendermonat rechnet, muss die Grenzen oben in MONATE nachsehen.

── Zwei Einschränkungen, die in den Sprechtext gehören ─────────────────────

1. Der Sollwert gilt JE FAHRT, diese Erhebung misst JE ABFAHRT AN EINEM HALT.
   Der bekannte Versatz beträgt bei der Tram −2,4 bis −3,3 Prozentpunkte, und
   er zeigt nach unten: Die eigene Messung liegt tiefer als die amtliche.
   Rechnet man ihn auf die Hypothesenlinie auf, landet sie bei rund 92,3 % —
   auf dem Sollwert. **Die Lücke ist damit nicht größer als der bekannte
   Instrumentenversatz.** „Über die Verspätung allein ist es nicht erreichbar"
   bleibt richtig; „knapp verfehlt" wäre es nicht.

2. Die Verfrühungsschwelle ist mit −120 s strenger als die amtliche (−60 s).
   Sie kann den Anteil deshalb nur unterschätzen — in dieser Richtung ist die
   Lücke konservativ.

── Das Wort, das hier nicht vorkommen darf ─────────────────────────────────

Was übrig bleibt, sind die verfrühten Abfahrten — und genau das sagt die
Grafik NICHT. Die Verfrühung ist die Auflösung von Szene 8, Szene 7 läuft
davor. Dieselbe Regel wie bei `richtung_spaet.png` und `lsa_zu_spaet.png`.

**Texte ändern:** Block `TEXTE_OHNE_VERSPAETUNG` in `src/analysis/grafiken.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

from elasticsearch import Elasticsearch                        # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER      # noqa: E402
from src.analysis.grafiken import (                            # noqa: E402
    abfahrtsdisziplin, fuers_video, ohne_verfruehung, ohne_verspaetung,
    ohne_verspaetung_reihe,
)
from validierung_bvg import lies_csv                           # noqa: E402

from export_grafiken import BREITE, HOEHE                      # noqa: E402

STANDARDZIEL = WURZEL / "video" / "bild" / "ohne_verspaetung.png"
ZIEL_VERFRUEHUNG = WURZEL / "video" / "bild" / "ohne_verfruehung.png"
ZIEL_DISZIPLIN = WURZEL / "video" / "bild" / "abfahrtsdisziplin.png"
WERTEZIEL = WURZEL / "video" / "animationen" / "ohne-verspaetung.json"

INDEX = "tram-departures-v2"
INDEX_UBAHN = "ubahn-departures-v2"
NETZ = "Straßenbahn"

# `bis` ist exklusiv. April fehlt: die Erhebung beginnt am 24.04. und die
# ersten drei Tage sind unvollständig.
MONATE = [
    ("Mai 26", "2026-05-01", "2026-06-01"),
    ("Jun 26", "2026-06-01", "2026-06-27"),   # Collector-Ausfall ab 27.06.
    ("Jul 26", "2026-07-08", "2026-08-01"),   # Ausfall bis 08.07.
    ("Aug 26", "2026-08-01", "2026-08-20"),   # angebrochen, Erhebung läuft
]


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ziel", type=Path, default=STANDARDZIEL)
    args = p.parse_args()

    sollwert = next(iter(lies_csv("Pünktlichkeit").values()))[
        f"Jahressollwert {NETZ}"]

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=900)
    werte = ohne_verspaetung_reihe(es, INDEX, MONATE,
                                   index_vergleich=INDEX_UBAHN)

    print(f"{'Monat':8} {'pünktlich':>10} {'zu früh':>9} {'zu spät':>9}   "
          f"{'o. Versp.':>10} {'o. Verfrüh.':>12} {'U-Bahn früh':>12} "
          f"{'Disziplin':>10} {'ggü. Soll':>10}")
    for _, z in werte.iterrows():
        print(f"{z['Monat']:8} {z['ist']:8.2f} % {z['zu_frueh']:7.2f} % "
              f"{z['zu_spaet']:7.2f} %   {z['ohne_verspaetung']:8.2f} % "
              f"{z['ohne_verfruehung']:10.2f} % "
              f"{z['verfrueht_vergleich']:10.2f} % "
              f"{z['wie_vergleich']:8.2f} % "
              f"{z['wie_vergleich'] - sollwert:+9.2f}")

    gewicht = werte["n"] / werte["n"].sum()
    mittel = float((werte["ohne_verspaetung"] * gewicht).sum())
    mittel_frueh = float((werte["ohne_verfruehung"] * gewicht).sum())
    mittel_disziplin = float((werte["wie_vergleich"] * gewicht).sum())
    mittel_ubahn_frueh = float((werte["verfrueht_vergleich"] * gewicht).sum())
    mittel_tram_frueh = float((werte["zu_frueh"] * gewicht).sum())
    bester = werte.loc[werte["ohne_verspaetung"].idxmax()]
    treffer = int((werte["ohne_verfruehung"] >= sollwert).sum())
    treffer_disziplin = int((werte["wie_vergleich"] >= sollwert).sum())
    print(f"\nOhne Verspätung, über alle vier Monate: {mittel:.2f} % — "
          f"{sollwert - mittel:.2f} Punkte unter dem Sollwert {sollwert} %.")
    print(f"  bester Monat {bester['Monat']} mit {bester['ohne_verspaetung']:.2f} %, "
          f"immer noch {sollwert - bester['ohne_verspaetung']:.2f} Punkte darunter.")
    print(f"Ohne Verfrühung: {mittel_frueh:.2f} % — Ziel in {treffer} von "
          f"{len(werte)} Monaten erreicht.")
    print(f"Mit der Abfahrtsdisziplin der U-Bahn "
          f"(Verfrühung {mittel_tram_frueh:.2f} % → {mittel_ubahn_frueh:.2f} %, "
          f"Verspätung unverändert): {mittel_disziplin:.2f} % — Ziel in "
          f"{treffer_disziplin} von {len(werte)} Monaten erreicht.")

    # Titel und Unterzeile stehen hier IM Bild — anders als bei den übrigen
    # Videografiken, weil der Aufbau der Senatsvorlage folgen soll.
    fig = fuers_video(ohne_verspaetung(werte, sollwert))
    fig.update_layout(margin=dict(t=190, b=90, l=130, r=430))

    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(args.ziel), width=BREITE, height=HOEHE, scale=1)
    print(f"\ngeschrieben: {args.ziel.relative_to(WURZEL)}")

    fig2 = fuers_video(ohne_verfruehung(werte, sollwert))
    fig2.update_layout(margin=dict(t=190, b=90, l=130, r=430))
    fig2.write_image(str(ZIEL_VERFRUEHUNG), width=BREITE, height=HOEHE, scale=1)
    print(f"geschrieben: {ZIEL_VERFRUEHUNG.relative_to(WURZEL)}")

    fig3 = fuers_video(abfahrtsdisziplin(werte, sollwert))
    fig3.update_layout(margin=dict(t=190, b=90, l=130, r=430))
    fig3.write_image(str(ZIEL_DISZIPLIN), width=BREITE, height=HOEHE, scale=1)
    print(f"geschrieben: {ZIEL_DISZIPLIN.relative_to(WURZEL)}")

    # Für die Animation, damit sie dieselben Zahlen zeichnet wie die PNG.
    WERTEZIEL.parent.mkdir(parents=True, exist_ok=True)
    WERTEZIEL.write_text(json.dumps({
        "sollwert": sollwert,
        "mittel_ohne_verspaetung": round(mittel, 2),
        "mittel_ohne_verfruehung": round(mittel_frueh, 2),
        "mittel_abfahrtsdisziplin": round(mittel_disziplin, 2),
        "verfruehung_tram": round(mittel_tram_frueh, 2),
        "verfruehung_ubahn": round(mittel_ubahn_frueh, 2),
        "monate": werte.to_dict(orient="records"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geschrieben: {WERTEZIEL.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
