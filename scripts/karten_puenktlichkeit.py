#!/usr/bin/env python3
"""Schreibt die Pünktlichkeitskarten als HTML — ohne Notebook-Lauf.

Ein voller Lauf von `03_lsa_analyse.ipynb` dauert rund zehn Minuten, weil er
1,2 Mio. Abfahrten für die Segmentanalyse lädt. Die Karten hier brauchen davon
nichts: Sie stehen auf einer einzigen Elasticsearch-Aggregation und sind in
Sekunden fertig.

    python3 scripts/karten_puenktlichkeit.py              # alle Varianten
    python3 scripts/karten_puenktlichkeit.py --frueh 120  # nur eine Schwelle
    python3 scripts/karten_puenktlichkeit.py --netz ubahn

Erzeugt in `video/karten/`:

    puenktlichkeitsfenster_tram_frueh60.html   Farbe = Richtung
    puenktlichkeitsfenster_tram_frueh120.html
    lsa_status_tram_frueh60.html           Farbe = ÖPNV-Beeinflussung
    lsa_status_tram_frueh120.html
    puenktlichkeitsfenster_ubahn_frueh60.html  zum Vergleich
    puenktlichkeitsfenster_ubahn_frueh120.html
    netzvergleich_frueh120.html            beide Netze, alle Halte
    netzvergleich_gepaart_frueh120.html    nur die gemeinsamen Standorte

Die gepaarte Fassung entsteht nur, wenn beide Netze im selben Lauf gerechnet
werden (`--netz beide`, die Vorgabe) — sie braucht beide Seiten.

Für die U-Bahn gibt es bewusst **keine** LSA-Fassung: Eine U-Bahn steht an
keiner Ampel. Die Karte dient dem Größenvergleich der Kreise, nicht der
Ursachenanalyse.

Gezeichnet wird hier nichts — alles kommt aus `src/analysis/karten.py`, dieselbe
Quelle, die auch das Notebook benutzt. Die Karten können deshalb nicht von der
Analyse abweichen. Farben und Kreisstufen dort ändern.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from elasticsearch import Elasticsearch                        # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER      # noqa: E402
from scipy import stats                                        # noqa: E402

from src.analysis.karten import (                              # noqa: E402
    anteile_je_haltestelle, gemeinsame_standorte, lsa_statuskarte,
    netzvergleichskarte, netzvergleichskarte_gepaart, zuverlaessigkeitskarte,
)
from src.analysis.quality import VERSPAETET_SCHWELLE_S         # noqa: E402

ZIEL = WURZEL / "video" / "karten"

INDIZES = {"tram": "tram-departures-v2", "ubahn": "ubahn-departures-v2"}
BESCHRIFTUNG = {"tram": "Tram", "ubahn": "U-Bahn"}


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frueh", type=int, action="append",
                   help="Verfrühung ab … Sekunden. Mehrfach angebbar. "
                        "Vorgabe: 60 und 120")
    p.add_argument("--spaet", type=int, default=VERSPAETET_SCHWELLE_S,
                   help="Verspätung ab … Sekunden (Vorgabe: 180)")
    p.add_argument("--netz", choices=["tram", "ubahn", "beide"], default="beide")
    p.add_argument("--ziel", type=Path, default=ZIEL)
    args = p.parse_args()

    schwellen = args.frueh or [60, 120]
    netze = ["tram", "ubahn"] if args.netz == "beide" else [args.netz]

    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=600)
    args.ziel.mkdir(parents=True, exist_ok=True)
    gesammelt = {}

    # Die LSA-Zuordnung nur einmal laden, sie hängt nicht an der Schwelle.
    df_lsa = None
    if "tram" in netze:
        from src.analysis.lsa import lade_lsa, lsa_je_haltestelle
        df_lsa = lade_lsa(es)

    for netz in netze:
        for frueh in schwellen:
            schwelle_frueh = -abs(frueh)
            stops = anteile_je_haltestelle(es, INDIZES[netz],
                                           schwelle_frueh, args.spaet)
            gezeigt = stops[stops["count"] >= 1_000]
            print(f"\n{BESCHRIFTUNG[netz]}, Fenster "
                  f"]{schwelle_frueh} s, +{args.spaet} s[")
            print(f"  Haltestellen: {len(stops)} "
                  f"(auf der Karte: {len(gezeigt)})")
            print(f"  Anteil außerhalb — Median {gezeigt['anteil_ausserhalb'].median():.1f} %, "
                  f"Spanne {gezeigt['anteil_ausserhalb'].min():.1f}–"
                  f"{gezeigt['anteil_ausserhalb'].max():.1f} %")
            print(f"  überwiegend zu früh: "
                  f"{(gezeigt['uebergewicht'] < 0).sum()} von {len(gezeigt)}")

            karte, _ = zuverlaessigkeitskarte(
                stops, schwelle_frueh, args.spaet,
                titel=f"Außerhalb des Pünktlichkeitsfensters — {BESCHRIFTUNG[netz]}")
            pfad = args.ziel / f"puenktlichkeitsfenster_{netz}_frueh{abs(frueh)}.html"
            karte.save(str(pfad))
            print(f"  geschrieben: {pfad.relative_to(WURZEL)}")

            gesammelt[(netz, frueh)] = stops

            if netz == "tram":
                mit_lsa = lsa_je_haltestelle(stops, df_lsa)
                karte2, _ = lsa_statuskarte(mit_lsa, schwelle_frueh, args.spaet)
                pfad2 = args.ziel / f"lsa_status_tram_frueh{abs(frueh)}.html"
                karte2.save(str(pfad2))
                print(f"  geschrieben: {pfad2.relative_to(WURZEL)}")

    # ── Beide Netze auf einer Karte ─────────────────────────────────────────
    for frueh in schwellen:
        if ("tram", frueh) not in gesammelt or ("ubahn", frueh) not in gesammelt:
            continue
        tram, ubahn = gesammelt[("tram", frueh)], gesammelt[("ubahn", frueh)]
        karte = netzvergleichskarte({"Tram": tram, "U-Bahn": ubahn},
                                    -abs(frueh), args.spaet)
        pfad = args.ziel / f"netzvergleich_frueh{abs(frueh)}.html"
        karte.save(str(pfad))
        print(f"\nBeide Netze, Fenster ]-{abs(frueh)} s, +{args.spaet} s[")
        print(f"  geschrieben: {pfad.relative_to(WURZEL)}")

        # Der gepaarte Vergleich ist die Absicherung der gemeinsamen Karte
        # gegen den Einwand "das ist Ost gegen West". Seit dem 21.08.2026 über
        # den Namen statt über 300 m Umkreis — Begründung im Docstring von
        # gemeinsame_standorte().
        paare = gemeinsame_standorte(tram, ubahn)
        if paare.empty:
            continue
        d = paare["differenz_pp"]
        w, p = stats.wilcoxon(paare["tram_pct"], paare["ubahn_pct"])
        print(f"  gemeinsame Standorte (gleicher Bahnhofsname): {len(paare)}")
        print(f"    Median U-Bahn {paare['ubahn_pct'].median():.1f} %, "
              f"Tram {paare['tram_pct'].median():.1f} %")
        print(f"    Median der Paardifferenz: {d.median():+.1f} pp  "
              f"(netzweit {tram['anteil_ausserhalb'].median() - ubahn['anteil_ausserhalb'].median():+.1f} pp)")
        print(f"    Tram schlechter in {(d > 0).sum()} von {len(d)} Paaren, "
              f"Wilcoxon p = {p:.2e}")

        # Dieselbe Karte, aber nur auf den gepaarten Standorten. Eigene Datei
        # statt einer abschaltbaren Ebene, damit im Schnitt zwischen "alle
        # Halte" und "nur die gemeinsamen" hart geschnitten werden kann.
        karte = netzvergleichskarte_gepaart(paare, -abs(frueh), args.spaet)
        pfad = args.ziel / f"netzvergleich_gepaart_frueh{abs(frueh)}.html"
        karte.save(str(pfad))
        print(f"  geschrieben: {pfad.relative_to(WURZEL)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
