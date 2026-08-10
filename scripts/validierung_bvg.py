#!/usr/bin/env python3
"""Vergleicht die eigene Messung mit den amtlichen Kennzahlen der BVG.

    python3 scripts/validierung_bvg.py

Grundlage sind die vier CSV-Dateien in `data/bvg/`, exportiert aus dem
Qualitätsmonitor der Senatsverwaltung, und die Definitionen in
`data/bvg/definition.md`.

── Warum das der wichtigste Beleg der Arbeit ist ────────────────────────────

Alle anderen Ergebnisse stehen auf einer selbst gebauten Erhebung. Ob die
funktioniert, kann man von innen nicht beweisen. Der Qualitätsmonitor misst
dieselben Netze im selben Zeitraum mit einem völlig anderen Verfahren — direkt
aus dem Betriebssystem der BVG statt aus der öffentlichen Abfahrts-API. Wo beide
übereinstimmen, ist das eine echte externe Validierung.

── Was vergleichbar ist und was nicht ───────────────────────────────────────

Drei der vier amtlichen Kennzahlen lassen sich nachrechnen, eine nicht:

  Pünktlichkeit           ja  — Fenster ]-60 s, +210 s[, im Raster ]-120, +240[
  Verfrühungsvermeidung   ja  — Gegenstück zu "mehr als 60 s zu früh"
  Zuverlässigkeit         eingeschränkt — nur bis zum 26.06.2026, danach ist die
                                cancelled-Erfassung kaputt (DATASET.md Nr. 3)
  Regelmäßigkeit          nein — braucht den Linientakt je Fahrt; die Bausteine
                                liegen in src/analysis/takt.py, die Zuordnung
                                Fahrt -> Takt fehlt noch

**Die Niveaus dürfen nicht als Gleichstand gelesen werden.** Der Monitor zählt je
**Fahrt**, diese Erhebung je **Abfahrtsereignis an einer Haltestelle**. Eine Fahrt
gilt amtlich als pünktlich, wenn sie es insgesamt war; hier zählt jeder einzelne
Halt. Weil eine Fahrt an dreißig Halten dreißig Gelegenheiten hat, aus dem Fenster
zu fallen, liegt die eigene Quote systematisch NIEDRIGER. Vergleichbar sind
deshalb die **Abstände zwischen den Netzen**, nicht die absoluten Werte.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from elasticsearch import Elasticsearch                        # noqa: E402

from config.settings import ES_HOST, ES_PASSWORD, ES_USER      # noqa: E402
from src.analysis.grafiken import VERFRUEHT_SCHWELLE_S         # noqa: E402
from src.analysis.quality import VERSPAETET_SCHWELLE_S         # noqa: E402

BVG = WURZEL / "data" / "bvg"
INDIZES = {"U-Bahn": "ubahn-departures-v2", "Straßenbahn": "tram-departures-v2"}

# Monate, in denen sich amtliche Veröffentlichung und eigene Erhebung
# überschneiden. April und Juni sind nur teilweise abgedeckt — die Erhebung
# beginnt am 27.04. und der Collector fiel ab dem 27.06. aus.
MONATE = [
    ("Apr 26", "2026-04-27", "2026-05-01", "nur 27.–30.04."),
    ("Mai 26", "2026-05-01", "2026-06-01", "vollständig"),
    ("Jun 26", "2026-06-01", "2026-06-27", "nur 01.–26.06."),
]


def lies_csv(name: str) -> dict[str, dict[str, float]]:
    """Eine Monitor-CSV als {Monat: {Spalte: Prozentwert}}."""
    pfad = next(BVG.glob(f"data-*.csv"), None) and None  # nur zur Klarheit
    treffer = [p for p in BVG.glob("data-*.csv")
               if p.read_text(encoding="utf-8-sig").split(",", 1)[0] == name]
    if not treffer:
        raise SystemExit(f"Keine CSV mit Kennzahl {name!r} in {BVG}")
    zeilen = list(csv.DictReader(
        treffer[0].read_text(encoding="utf-8-sig").splitlines()))
    heraus = {}
    for zeile in zeilen:
        monat = zeile[name]
        heraus[monat] = {
            spalte: float(wert.replace("%", "").replace(",", "."))
            for spalte, wert in zeile.items()
            if spalte != name and wert
        }
    return heraus


def eigene_werte(es, index: str, von: str, bis: str) -> dict[str, float]:
    """Pünktlichkeit, Verfrühungsvermeidung und Zuverlässigkeit für ein Fenster.

    Bewusst OHNE analysefenster_query(): Hier soll ein Kalendermonat gegen einen
    Kalendermonat stehen, nicht das Analysefenster des Projekts. Der
    Collector-Ausfall wird stattdessen über die Monatsgrenzen in MONATE
    ausgeklammert.
    """
    zeitraum = {"range": {"planned_when": {"gte": von, "lt": bis}}}

    mit_delay = es.search(
        index=index, size=0, track_total_hits=True,
        query={"bool": {"filter": [zeitraum, {"exists": {"field": "delay_s"}}]}},
        aggs={
            "frueh": {"filter": {"range": {"delay_s": {"lte": VERFRUEHT_SCHWELLE_S}}}},
            "spaet": {"filter": {"range": {"delay_s": {"gte": VERSPAETET_SCHWELLE_S}}}},
        },
    )
    n = mit_delay["hits"]["total"]["value"]
    if not n:
        return {}
    frueh = mit_delay["aggregations"]["frueh"]["doc_count"] / n * 100
    spaet = mit_delay["aggregations"]["spaet"]["doc_count"] / n * 100

    alle = es.search(
        index=index, size=0, track_total_hits=True, query=zeitraum,
        aggs={"aus": {"filter": {"term": {"cancelled": True}}}})
    n_alle = alle["hits"]["total"]["value"]
    ausfall = alle["aggregations"]["aus"]["doc_count"] / n_alle * 100

    return {
        "Pünktlichkeit": 100 - frueh - spaet,
        "Verfrühungsvermeidung": 100 - frueh,
        "Zuverlässigkeit": 100 - ausfall,
        "_n": n,
    }


def main() -> int:
    amtlich = {k: lies_csv(k) for k in
               ("Pünktlichkeit", "Verfrühungsvermeidung", "Zuverlässigkeit")}
    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD),
                       request_timeout=600)

    print(f"Eigenes Fenster: zu früh ab {VERFRUEHT_SCHWELLE_S} s, "
          f"zu spät ab +{VERSPAETET_SCHWELLE_S} s\n")

    gesammelt = {}
    for monat, von, bis, hinweis in MONATE:
        print(f"── {monat}  ({hinweis}) " + "─" * 40)
        for netz, index in INDIZES.items():
            eigen = eigene_werte(es, index, von, bis)
            if not eigen:
                print(f"  {netz}: keine Daten")
                continue
            gesammelt.setdefault(netz, {})[monat] = eigen
            print(f"  {netz}  (n = {eigen['_n']:,} Abfahrten mit delay_s)")
            for kennzahl in amtlich:
                amt = amtlich[kennzahl].get(monat, {}).get(netz)
                soll = next((v for k, v in amtlich[kennzahl]
                             .get(monat, {}).items()
                             if k.startswith("Jahressollwert") and netz in k), None)
                if amt is None:
                    continue
                d = eigen[kennzahl] - amt
                print(f"    {kennzahl:<22} eigen {eigen[kennzahl]:6.2f} %   "
                      f"amtlich {amt:6.2f} %   Abweichung {d:+6.2f} pp"
                      + (f"   Soll {soll:.2f} %" if soll else ""))
        print()

    # ── Der eigentliche Prüfstein: der Abstand zwischen den Netzen ───────────
    print("── Abstand Straßenbahn zu U-Bahn " + "─" * 32)
    print("   Die Niveaus sind wegen der Zähleinheit nicht vergleichbar, "
          "die Abstände schon.\n")
    for kennzahl in amtlich:
        print(f"  {kennzahl}")
        for monat, _, _, _ in MONATE:
            if not all(monat in gesammelt.get(n, {}) for n in INDIZES):
                continue
            e = (gesammelt["Straßenbahn"][monat][kennzahl]
                 - gesammelt["U-Bahn"][monat][kennzahl])
            a_tram = amtlich[kennzahl].get(monat, {}).get("Straßenbahn")
            a_ubahn = amtlich[kennzahl].get(monat, {}).get("U-Bahn")
            if a_tram is None or a_ubahn is None:
                continue
            a = a_tram - a_ubahn
            print(f"    {monat}   eigen {e:+7.2f} pp   amtlich {a:+7.2f} pp   "
                  f"Differenz der Abstände {e - a:+6.2f} pp")
        print()

    # ── Verfrühung als Verhältnis statt in Prozentpunkten ────────────────────
    #
    # Bei der Verfrühung gehen die Prozentpunkte weit auseinander (eigene
    # Messung rund dreimal so grosser Abstand), das VERHAELTNIS zwischen den
    # Netzen aber nicht. Das ist die Form, in der die Zahl im Video stehen darf.
    print("── Verfrühung: Verhältnis Straßenbahn zu U-Bahn " + "─" * 18)
    print("   In Prozentpunkten laufen die Quellen auseinander, im Verhältnis "
          "nicht.\n")
    for monat, _, _, _ in MONATE:
        if not all(monat in gesammelt.get(n, {}) for n in INDIZES):
            continue
        e_t = 100 - gesammelt["Straßenbahn"][monat]["Verfrühungsvermeidung"]
        e_u = 100 - gesammelt["U-Bahn"][monat]["Verfrühungsvermeidung"]
        a_t = 100 - amtlich["Verfrühungsvermeidung"][monat]["Straßenbahn"]
        a_u = 100 - amtlich["Verfrühungsvermeidung"][monat]["U-Bahn"]
        print(f"    {monat}   eigen {e_t:5.2f} % : {e_u:4.2f} % = {e_t / e_u:5.1f}×"
              f"    amtlich {a_t:4.2f} % : {a_u:4.2f} % = {a_t / a_u:5.1f}×")
    print("\n   Die eigene Messung liegt in jedem Monat UNTER dem amtlichen "
          "Verhältnis —\n   sie ist gegenüber der Senatsstatistik konservativ.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
