"""LSA-Gruppen als Balken — mit und ohne Pünktlichkeitsfenster.

    python3 scripts/grafik_lsa_fenster.py                # zu spät, am Fenster
    python3 scripts/grafik_lsa_fenster.py --mittelwert   # Ø delay_s, ohne
    python3 scripts/grafik_lsa_fenster.py --verspaetung  # nur Verspätung, ab 0 s
    python3 scripts/grafik_lsa_fenster.py --ueberzug     # Sekunden AB dem Fenster

Erzeugt `video/bild/lsa_zu_spaet.png`, `lsa_mittelwert.png` bzw.
`lsa_ueberzug.png` (1920×1080): drei Balken in den Farben der Karte aus
derselben Szene — grau keine Ampel, grün Beeinflussung angenommen, rot belegt
abgeschaltet.

── Wozu die drei Fassungen ──────────────────────────────────────────────────

`szene3b_lsa_balken.png` (Notebook 03) zeigte bis zum 19.08.2026 nur
**`avg_delay_s`** — den Mittelwert der Abweichung je Haltestelle. Das
Pünktlichkeitsfenster kam darin nicht vor, und der Mittelwert verrechnet
Verfrühung gegen Verspätung. Genau diese Kennzahl führt Szene 4 des Films als
irreführend vor; mit ihr als Beleg widerspricht sich der Film selbst.

    Gruppe                        Halte   Ø delay_s   ab 0 s   zu spät   ab 3½ min
    keine Ampel                     134      25,0 s   41,6 s     4,6 %      10,0 s
    Beeinflussung angenommen        252      32,1 s   51,2 s     5,9 %      10,2 s
    Beeinflussung belegt inaktiv      7      41,1 s   52,7 s     6,1 %       9,8 s
    Verhältnis inaktiv / angenommen            1,28×    1,03×     1,03×       0,96×

Der Mittelwert zeigt ein Gefälle, das am Vertragsfenster verschwindet. Grund:
An den sieben Halten fährt die Tram nur halb so oft zu früh (5,6 % gegen
10,1 %), ihr Mittelwert wird also nicht von negativen Werten nach unten
gezogen.

**`--verspaetung` und `--ueberzug` schließen die Lücke zwischen den beiden.**
Der Einwand gegen die Prozentfassung ist, dass sie die Einheit wechselt und
deshalb nicht neben der Mittelwertgrafik steht — 6,1 % und 41,1 s sind nicht
vergleichbar. Beide Zusatzfassungen messen in Sekunden wie der Mittelwert,
rechnen aber Verfrühung nicht gegen: `mean(max(delay_s - schwelle, 0))`, einmal
mit der Fahrplanzeit und einmal mit der Vertragsgrenze als Null.

Ergebnis (Mann-Whitney, inaktiv gegen aktiv, je Haltestelle):

    Ø delay_s            p = 0,185   r = +0,30
    Ø Verspätung (s)     p = 0,629   r = +0,11
    zu spät (%)          p = 0,918   r = +0,02
    Ø über Fenster (s)   p = 0,820   r = -0,05     Kruskal-Wallis p = 0,589

Kein Effekt in keiner der vier Kennzahlen. **Der Abstand zerfällt in zwei
Teile:** Von den 9,0 s Vorsprung der inaktiven Gruppe bleiben 1,5 s, sobald
Verfrühung nicht mehr negativ zählt — rund vier Fünftel waren nie Verspätung,
sondern fehlende Verfrühung an den Vergleichsgruppen. Am Vertragsfenster kehrt
sich der Rest sogar um.

── Was --ueberzug beim grauen Balken zeigt ──────────────────────────────────

Der Vergleich keine Ampel gegen aktiv kippt zwischen den Fassungen: In Prozent
liegt Grau deutlich niedriger (4,6 % gegen 5,9 %, p < 0,0001), in Sekunden ab
dem Fenster ist der Abstand weg (10,0 gegen 10,2 s, p = 0,297). Ursache ist
nicht die Ampel, sondern die Netzlage. An den Halten ohne Anlage ist die Tram
selten zu spät, dann aber massiv — Wendenschloß, Rahnsdorf, Rosenthal Nord und
die übrigen Außenäste kommen auf 0,3 bis 0,5 % verspätete Abfahrten mit im
Mittel 13 bis 18 Minuten Überzug. Wenige, dafür sehr große Ausfälle ergeben
dieselbe Summe wie viele kleine Verspätungen in der Innenstadt.

Deshalb steht dieser Vergleich nicht im Film. Er misst Innenstadt gegen
Außenast, nicht Ampel gegen keine Ampel.

── Drei Gruppen, nicht vier ─────────────────────────────────────────────────

`potentiell_ineffektiv` ist entfallen. Die Gruppe war definiert als „aktiv und
Ø delay_s über Mittel + 1,5 σ der aktiven Gruppe" — also als das obere Ende der
grünen Gruppe. Schneidet man sie heraus, sinkt der Rest der grünen Gruppe
künstlich und der Abstand zu Rot wächst von **1,04×** auf **1,17×**. Die
Abspaltung erzeugt damit den Effekt, den die Grafik zeigen soll. `--getrennt`
stellt sie zum Vorführen wieder her.

── Und was trotzdem offen bleibt ────────────────────────────────────────────

Die Gruppe `inaktiv` sind **sieben Haltestellen** auf zwei Linien, belegt durch
eine parlamentarische Anfrage von **August 2024**. Was heute geschaltet ist,
sagen die öffentlichen Daten nicht — und dass die grüne Gruppe überhaupt eine
aktive Beeinflussung hat, ist eine Annahme aus der Entfernung zur nächsten
Anlage, keine Messung. Kein Unterschied dieser Gruppen ist belastbar, in keine
Richtung.

── Eine Aggregation für Notebook und Video ──────────────────────────────────

Gerechnet wird mit `anteile_je_haltestelle()` aus `src/analysis/karten.py` —
derselben Abfrage, die Notebook 03 in `sec2-agg` aufruft und mit der die Karten
gefärbt werden. Gezeichnet wird mit `lsa_balken()` aus
`src/analysis/grafiken.py`, die Notebook 03 in `sec3-barplot` ebenfalls aufruft.
Es gibt keine zweite Fassung, die abweichen könnte.

**Texte ändern:** Block `TEXTE_LSA_FENSTER` in `src/analysis/grafiken.py`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

import pandas as pd                                            # noqa: E402
from elasticsearch import Elasticsearch                        # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER      # noqa: E402
from src.analysis.grafiken import (                            # noqa: E402
    REIHENFOLGE_LSA, REIHENFOLGE_LSA_GETRENNT, SPALTE_UEBERZUG,
    SPALTE_VERSPAETUNG, VERFRUEHT_SCHWELLE_S, fuers_video, lsa_balken,
)
from src.analysis.karten import (                              # noqa: E402
    MIN_ABFAHRTEN, anteile_je_haltestelle,
)
from src.analysis.lsa import lade_lsa, lsa_je_haltestelle      # noqa: E402
from src.analysis.quality import VERSPAETET_SCHWELLE_S         # noqa: E402

from export_grafiken import BREITE, HOEHE                      # noqa: E402

STANDARDZIEL = WURZEL / "video" / "bild" / "lsa_zu_spaet.png"
INDEX = "tram-departures-v2"

# Wie Notebook 03, Zelle `sec3-barplot`: das obere Ende der aktiven Gruppe.
SIGMA_AUFFAELLIG = 1.5


def gruppen(es, getrennt: bool = False) -> pd.DataFrame:
    # Dieselbe Aggregation, die Notebook 03 in `sec2-agg` aufruft und mit der
    # auch die Karten gefärbt werden. Eine eigene Abfrage hier hatte 0,06
    # Prozentpunkte Abstand zu den Notebook-Zahlen — sie filterte zusätzlich auf
    # das Analysefenster, `anteile_je_haltestelle` tut das nicht. Der
    # Unterschied ändert keinen Befund, aber zwei Zahlen für dieselbe Sache
    # ändern das Vertrauen in beide.
    halte = lsa_je_haltestelle(
        anteile_je_haltestelle(es, INDEX, VERFRUEHT_SCHWELLE_S,
                               VERSPAETET_SCHWELLE_S),
        lade_lsa(es))
    halte = halte[halte["count"] >= MIN_ABFAHRTEN].copy()

    halte["gruppe"] = halte["lsa_status"]
    ordnung = REIHENFOLGE_LSA
    if getrennt:
        aktiv = halte.loc[halte["lsa_status"] == "aktiv", "avg_delay_s"]
        schwelle = aktiv.mean() + SIGMA_AUFFAELLIG * aktiv.std()
        halte.loc[(halte["lsa_status"] == "aktiv")
                  & (halte["avg_delay_s"] > schwelle),
                  "gruppe"] = "potentiell_ineffektiv"
        ordnung = REIHENFOLGE_LSA_GETRENNT
        print(f"Schwelle 'auffällig': Ø delay_s > {schwelle:.1f} s")

    t = (halte[halte["gruppe"].isin(ordnung)]
         .groupby("gruppe")
         .agg(**{"Halte": ("stop_name", "size"),
                 "zu früh (%)": ("anteil_frueh", "mean"),
                 "zu spät (%)": ("anteil_spaet", "mean"),
                 "Ø delay_s": ("avg_delay_s", "mean"),
                 SPALTE_VERSPAETUNG: ("verspaetung_s", "mean"),
                 SPALTE_UEBERZUG: ("ueberzug_s", "mean")})
         .reset_index())
    t["außerhalb (%)"] = t["zu früh (%)"] + t["zu spät (%)"]
    return t


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mittelwert", action="store_true",
                   help="Ø delay_s statt des Anteils zu später Abfahrten — "
                        "die Fassung OHNE Pünktlichkeitsfenster")
    p.add_argument("--verspaetung", action="store_true",
                   help="nur die Verspätungen, Nullpunkt Fahrplanzeit — "
                        "wie --mittelwert, aber ohne Verfrühung "
                        "gegenzurechnen")
    p.add_argument("--ueberzug", action="store_true",
                   help="Sekunden ab dem Pünktlichkeitsfenster statt des "
                        "Anteils: dieselbe Grenze wie die Vorgabe, aber in "
                        "der Einheit von --mittelwert")
    p.add_argument("--getrennt", action="store_true",
                   help="die Gruppe 'auffällig' wieder abspalten, nur zum "
                        "Vorführen (siehe Kopf)")
    p.add_argument("--ziel", type=Path, default=None)
    args = p.parse_args()
    if sum([args.mittelwert, args.verspaetung, args.ueberzug]) > 1:
        p.error("--mittelwert, --verspaetung und --ueberzug schließen "
                "sich gegenseitig aus")
    name = ("lsa_mittelwert.png" if args.mittelwert
            else "lsa_verspaetung.png" if args.verspaetung
            else "lsa_ueberzug.png" if args.ueberzug
            else STANDARDZIEL.name)
    if args.getrennt:
        name = name.replace(".png", "_getrennt.png")
    ziel = args.ziel or STANDARDZIEL.with_name(name)

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=900)
    t = gruppen(es, getrennt=args.getrennt)
    reihen = {g: i for i, g in enumerate(REIHENFOLGE_LSA_GETRENNT)}
    print()
    print(t.sort_values("gruppe", key=lambda s: s.map(reihen))
           .round(2).to_string(index=False))

    spalte = ("Ø delay_s" if args.mittelwert
              else SPALTE_VERSPAETUNG if args.verspaetung
              else SPALTE_UEBERZUG if args.ueberzug
              else "zu spät (%)")
    fig = fuers_video(lsa_balken(t, spalte))
    # Kein Titel im Bild. Unten Platz für die Halte-Zahlen unter den Balken.
    fig.update_layout(margin=dict(t=90, b=200, l=170, r=80))

    ziel.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(ziel), width=BREITE, height=HOEHE, scale=1)
    print(f"\ngeschrieben: {ziel.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
