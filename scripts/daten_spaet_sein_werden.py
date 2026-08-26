#!/usr/bin/env python3
"""Die zwei Ranglisten für Szene 6b: wo die Tram spät IST, wo sie spät WIRD.

    python3 scripts/daten_spaet_sein_werden.py

Schreibt `video/animationen/spaet-sein-werden.json` — die Animation liest daraus
und rechnet selbst nichts. Damit stehen die Zahlen genau einmal.

── Die beiden Spalten messen Verschiedenes ─────────────────────────────────

    links   verspaetung_s          je Haltestelle. Zustand: wie viel
                                   Verspätung die Tram DORT hat.
    rechts  summe_positiv / n      je Abschnitt (stop_from → stop_to).
                                   Zunahme: wie viel Verspätung auf DIESEM
                                   Weg dazukommt.

── Beide Spalten rechnen nur Verspätung ────────────────────────────────────

Verfrühte Abfahrten zählen links null, abgebaute Verspätung rechts ebenfalls.
Es wird nichts gegengerechnet. Die naheliegenden Spalten `avg_delay_s` und
`mittel_delta` täten genau das — und der verrechnete Mittelwert ist die
Kennzahl, die Szene 4 des Films als irreführend vorführt. Sie hier zu benutzen
hieße, im selben Film erst davor zu warnen und dann darauf zu bauen.

Beide Größen liegen längst vor und kosten keinen zusätzlichen Lauf:
`verspaetung_s` kommt aus `anteile_je_haltestelle()`, `summe_positiv` steht im
Segmentparquet.

Der Unterschied ist sichtbar, aber nicht dramatisch: Links steigen die Werte um
rund zehn Sekunden, rechts um zwei bis fünf, und in beiden Listen wandern
einzelne Ränge. Die Aussage der Szene bleibt dieselbe — die Listen sind
weiterhin disjunkt.

Die linke Zahl sagt nichts über die Ursache: Ein Halt am Ende einer langen
Linie erbt die Verspätung des ganzen Wegs, ohne selbst etwas beizutragen. Die
rechte ist die Differenz zwischen zwei aufeinanderfolgenden Halten derselben
Fahrt — sie hat eine Richtung und ist dem Abschnitt zurechenbar.

Die rechte Spalte stand zuerst je Haltestelle (Zufluss, gemittelt über alle
Zufahrten). Die Fassung je Abschnitt ist die aussagekräftigere: Sie nennt beide
Enden und damit die Fahrtrichtung, und sie mittelt nicht mehr Zufahrten
zusammen, die sich unterschiedlich verhalten.

── Woher die rechte Spalte kommt ───────────────────────────────────────────

Aus `segmente_tram_gesamt.parquet`, das bereits je Haltestellenpaar aggregiert
ist — dieselbe Auswertung wie Abschnitt 4 von Notebook 04 („Verspätungszunahme
je Abschnitt"), mit derselben Mindestzahl `MIN_BEOBACHTUNGEN_JE_SEGMENT`.

**Die Mindestzahl trägt hier das Ergebnis.** Fehlt in einer Fahrt eine
Zwischenhaltestelle, entsteht ein Paar, das zwei echte Abschnitte überspannt
und deren Verspätung zusammengefasst ausweist. Solche Pseudoabschnitte sind
selten, führen aber jede Rangliste an. Notebook 04 hat das durchgerechnet: Bei
n ≥ 20 steht oben ein Wert von 261 s, ab rund 500 ist er stabil, benutzt werden
2.000. Wer die Zahl hier senkt, bekommt eine andere und falsche Liste.

── Gleiche Grundgesamtheit ─────────────────────────────────────────────────

Die linke Liste wird auf die Haltestellen eingeschränkt, die in der rechten
überhaupt vorkommen können — also auf die Zielhalte der auswertbaren
Abschnitte. Ohne das stünde links ein Name, über den die rechte Spalte gar
nichts sagen kann, und der Zuschauer läse eine Aussage über die Haltestelle,
wo nur eine über die Datenlage steht.

── Betriebliche Halte ──────────────────────────────────────────────────────

Ausstiegs- und Endstellen sowie Betriebshöfe fallen raus (`quality.py`). Das ist
hier keine Formsache: Ohne die Regel führen „Altes Wasserwerk [Ausstieg]" mit
101 s und „Haeckelstr. [Ausstieg]" mit 94 s die linke Liste an. Dort steht das
Fahrzeug planmäßig länger — eine Verspätung, die kein Fahrgast erlebt, in einer
Grafik, die vom Erleben handelt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "scripts"))

from elasticsearch import Elasticsearch                        # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER      # noqa: E402
from src.analysis.karten import (                              # noqa: E402
    MIN_ABFAHRTEN, anteile_je_haltestelle,
)
from src.analysis.quality import (                             # noqa: E402
    VERSPAETET_SCHWELLE_S, analysefenster_query,
    ist_betriebliche_haltestelle, werktagsfilter,
)
from src.analysis.grafiken import VERFRUEHT_SCHWELLE_S         # noqa: E402
from src.analysis.segmente import (                            # noqa: E402
    MIN_BEOBACHTUNGEN_JE_SEGMENT,
)

INDEX = "tram-departures-v2"
SEGMENT_PARQUET = WURZEL / "data" / "processed" / "segmente_tram_gesamt.parquet"
ANTEIL_PARQUET = (WURZEL / "data" / "processed"
                  / "segmente_tram_zunahmeanteil.parquet")
ZIEL = WURZEL / "video" / "animationen" / "spaet-sein-werden.json"
ZIEL_ANTEIL = WURZEL / "video" / "animationen" / "spaet-sein-werden-anteil.json"

WIE_VIELE = 10


def main() -> int:
    import pandas as pd

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=600)

    # Analysezeitraum, ohne Collector-Ausfall, ohne Fremdlinien, nur Werktage.
    # Ohne diesen Filter läuft anteile_je_haltestelle() über den GANZEN Index —
    # dann stünde links eine Zahl aus Wochenenden und Ausfalltagen neben einer
    # rechten, die beides ausschließt. Kostet rund zwölf Sekunden.
    fenster = analysefenster_query()
    fenster["bool"]["must"].append(werktagsfilter())

    stops = anteile_je_haltestelle(es, INDEX, VERFRUEHT_SCHWELLE_S,
                                   VERSPAETET_SCHWELLE_S, query=fenster)
    stops = stops[stops["count"] >= MIN_ABFAHRTEN]
    print(f"Haltestellen mit mindestens {MIN_ABFAHRTEN:,} Abfahrten: {len(stops)}")

    seg = pd.read_parquet(SEGMENT_PARQUET)
    print(f"Haltestellenpaare im Parquet: {len(seg):,}")
    seg = seg[seg["n"] >= MIN_BEOBACHTUNGEN_JE_SEGMENT]
    print(f"davon mit mindestens {MIN_BEOBACHTUNGEN_JE_SEGMENT:,} "
          f"Beobachtungen: {len(seg)}")

    # Betriebshöfe, Ausstiegs- und Endstellen raus — an beiden Enden eines
    # Abschnitts. Ohne die Regel führen zwei Ausstiegshalte die linke Liste an:
    # Dort steht das Fahrzeug planmäßig länger, die „Verspätung" erlebt kein
    # Fahrgast. Die Regel steht in quality.py und gilt im Projekt für jede
    # Auswertung je Haltestelle.
    stops = stops[~stops["stop_name"].apply(ist_betriebliche_haltestelle)]
    seg = seg[~seg["stop_from"].apply(ist_betriebliche_haltestelle)
              & ~seg["stop_to"].apply(ist_betriebliche_haltestelle)]
    print(f"ohne betriebliche Halte: {len(stops)} Haltestellen, "
          f"{len(seg)} Abschnitte")

    # Gleiche Grundgesamtheit: links nur Halte, über die die rechte Spalte
    # überhaupt etwas sagen könnte — also Zielhalte auswertbarer Abschnitte.
    erreichbar = set(seg["stop_to"])
    stops = stops[stops["stop_name"].isin(erreichbar)]
    print(f"Haltestellen in beiden Auswertungen: {len(stops)}")

    # Beide Spalten rechnen NUR Verspätung. Verfrühte Abfahrten links und
    # abgebaute Verspätung rechts zählen null, statt gegenzurechnen — der
    # verrechnete Mittelwert ist genau die Kennzahl, die Szene 4 des Films als
    # irreführend vorführt. Beide Größen liegen längst vor und kosten nichts:
    # `verspaetung_s` kommt aus anteile_je_haltestelle(), `summe_positiv` steht
    # im Parquet.
    seg = seg.assign(nur_zunahme=seg["summe_positiv"] / seg["n"])

    links = stops.nlargest(WIE_VIELE, "verspaetung_s")
    rechts = seg.nlargest(WIE_VIELE, "nur_zunahme")

    # Überschneidung: Steht ein Halt der linken Liste an einem der zehn
    # Abschnitte rechts? Geprüft werden BEIDE Enden — ob die Verspätung dort
    # ankommt oder losgeht, ist für die Frage gleich.
    enden = set(rechts["stop_from"]) | set(rechts["stop_to"])
    beide = [n for n in links["stop_name"] if n in enden]

    # Auf ganze Sekunden: Die Erhebung laeuft weiter, eine Nachkommastelle
    # behauptet eine Stabilitaet, die die Zahl nicht hat.
    daten = {
        "n_haltestellen": len(stops),
        "n_abschnitte": len(seg),
        "links": [{"name": kurz(z["stop_name"]),
                   "wert": round(float(z["verspaetung_s"])),
                   "beide": z["stop_name"] in beide}
                  for _, z in links.iterrows()],
        "rechts": [{"von": kurz(z["stop_from"]), "nach": kurz(z["stop_to"]),
                    "wert": round(float(z["nur_zunahme"])),
                    "n": int(z["n"]),
                    "beide": (z["stop_from"] in beide
                              or z["stop_to"] in beide)}
                   for _, z in rechts.iterrows()],
        "n_beide": len(beide),
    }

    print("\nlinks — wo die Tram am spätesten ist "
          "(Ø Verspätung, Verfrühung zählt 0)")
    for z in daten["links"]:
        print(f"  {z['wert']:>5} s  {z['name']}{'  ●' if z['beide'] else ''}")
    print("\nrechts — wo die Verspätung entsteht (Ø Zunahme je Fahrt, "
          "Abbau zählt 0)")
    for z in daten["rechts"]:
        print(f"  {z['wert']:>5} s  n={z['n']:>6}  {z['von']} nach {z['nach']}"
              + ("  ●" if z["beide"] else ""))
    print(f"\nin beiden Listen: {len(beide)}"
          + (f" — {', '.join(kurz(n) for n in beide)}" if beide else ""))

    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    ZIEL.write_text(json.dumps(daten, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"\ngeschrieben: {ZIEL.relative_to(WURZEL)}")

    fassung_anteil(stops, erreichbar)
    return 0


def fassung_anteil(stops, erreichbar: set) -> None:
    """Dieselbe Gegenüberstellung, beide Spalten als Anteil.

    Links der Anteil der Abfahrten, die mehr als 3½ Minuten zu spät sind —
    die Vertragsschwelle. Rechts der Anteil der Fahrten, auf denen die Tram
    auf diesem Abschnitt später wird.

    ── Warum das die ehrlichere Fassung ist ─────────────────────────────────

    Der Mittelwert der Sekundenfassung wird von wenigen groszen Werten nach
    oben gezogen: An der Guntherstr. sind es 103 s im Mittel, aber 78 % aller
    Abfahrten liegen im Puenktlichkeitsfenster und der Median liegt bei 60 s.
    Ein Anteil kann das nicht — er sagt, wie oft, nicht wie schlimm.

    Verfruehungen ziehen hier nichts mehr herunter: Sie sind schlicht nicht
    verspaetet und zaehlen im Zaehler mit null. Dasselbe rechts fuer Abschnitte,
    auf denen Verspaetung abgebaut wird.

    Die rechte Spalte braucht `segmente_tram_zunahmeanteil.parquet` — aus einer
    Summe laesst sich kein Anteil zurueckrechnen, deshalb ein eigener Lauf
    (scripts/segmente_zunahmeanteil.py, rund sieben Minuten).
    """
    import pandas as pd

    if not ANTEIL_PARQUET.exists():
        print(f"\n{ANTEIL_PARQUET.name} fehlt — Anteilsfassung übersprungen. "
              "Erst scripts/segmente_zunahmeanteil.py laufen lassen.")
        return

    seg = pd.read_parquet(ANTEIL_PARQUET)
    seg = seg[seg["n"] >= MIN_BEOBACHTUNGEN_JE_SEGMENT]
    seg = seg[~seg["stop_from"].apply(ist_betriebliche_haltestelle)
              & ~seg["stop_to"].apply(ist_betriebliche_haltestelle)]
    # Dieselbe Grundgesamtheit wie die Sekundenfassung.
    stops = stops[stops["stop_name"].isin(erreichbar)]

    links = stops.nlargest(WIE_VIELE, "anteil_spaet")
    rechts = seg.nlargest(WIE_VIELE, "anteil_zunahme")

    enden = set(rechts["stop_from"]) | set(rechts["stop_to"])
    beide = [n for n in links["stop_name"] if n in enden]

    daten = {
        "n_haltestellen": len(stops),
        "n_abschnitte": len(seg),
        "links": [{"name": kurz(z["stop_name"]),
                   "wert": round(float(z["anteil_spaet"]), 1),
                   "beide": z["stop_name"] in beide}
                  for _, z in links.iterrows()],
        "rechts": [{"von": kurz(z["stop_from"]), "nach": kurz(z["stop_to"]),
                    "wert": round(float(z["anteil_zunahme"]), 1),
                    "n": int(z["n"]),
                    "beide": (z["stop_from"] in beide
                              or z["stop_to"] in beide)}
                   for _, z in rechts.iterrows()],
        "n_beide": len(beide),
    }

    print(f"\n── Anteilsfassung ({len(seg)} Abschnitte) ──")
    print("links — wo die Tram am häufigsten zu spät ist "
          "(Anteil über 3½ Minuten)")
    for z in daten["links"]:
        print(f"  {z['wert']:>5} %  {z['name']}{'  ●' if z['beide'] else ''}")
    print("\nrechts — wo die Verspätung entsteht (Anteil der Fahrten mit Zunahme)")
    for z in daten["rechts"]:
        print(f"  {z['wert']:>5} %  n={z['n']:>6}  {z['von']} nach {z['nach']}"
              + ("  ●" if z["beide"] else ""))
    print(f"\nin beiden Listen: {len(beide)}"
          + (f" — {', '.join(kurz(n) for n in beide)}" if beide else ""))

    ZIEL_ANTEIL.write_text(json.dumps(daten, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    print(f"geschrieben: {ZIEL_ANTEIL.relative_to(WURZEL)}")


def kurz(name: str) -> str:
    """„(Berlin)" weg — steht an fast jedem Namen und trägt im Bild nichts."""
    return name.replace(" (Berlin)", "").strip()


if __name__ == "__main__":
    raise SystemExit(main())
