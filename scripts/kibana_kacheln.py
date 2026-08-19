#!/usr/bin/env python3
"""Legt die beiden Mittelwert-Kacheln für Szene 4 in Kibana an.

    python3 scripts/kibana_kacheln.py
    python3 scripts/kibana_kacheln.py --loeschen     # wieder entfernen

Erzeugt zwei Lens-Visualisierungen — „Ø Abweichung Straßenbahn" (rot) und
„Ø Abweichung U-Bahn" (blau) — und ein Dashboard, das beide nebeneinander zeigt.
Alle drei Objekte tragen feste IDs mit dem Präfix `szene4-`, damit ein zweiter
Aufruf sie überschreibt statt Dubletten anzulegen.

── Warum zwei getrennte Kacheln und kein Breakdown ──────────────────────────

`KIBANA.md` beschreibt den Weg über **Breakdown by `_index`**. Der ist zum
Klicken schneller, vergibt die Farben aber aus einer Palette — Tram und U-Bahn
bekommen dann irgendwelche zwei Farben, nicht Rot und Blau. Zwei getrennte
Kacheln mit je einer festen Farbe sind der einzige Weg, die Netzfarben des
Projekts exakt zu treffen (FARBE_NETZ in src/analysis/grafiken.py).

── Was die Kachel zeigt ─────────────────────────────────────────────────────

Den Mittelwert von `delay_s` über das Analysefenster. Erwartet werden rund 33 s
für die Straßenbahn und rund 22 s für die U-Bahn. Die beiden Zahlen liegen
absichtlich nah beieinander — das ist die Aussage von Szene 4, nicht ein Fehler.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from config.settings import ES_PASSWORD, ES_USER                # noqa: E402
from src.analysis.grafiken import FARBE_NETZ                    # noqa: E402

KIBANA = "http://tram-pi:5601"

# Die kombinierte Data View über beide Netze (`*-departures-v2`), angelegt nach
# KIBANA.md Abschnitt 0.1. Wird beim Lauf gegen die API geprüft.
DATA_VIEW = "eaae290c-7850-4ae3-9a93-6164856d6bf1"

# Basisfilter aus KIBANA.md Abschnitt 0.3. Ohne ihn zeigt Kibana andere Zahlen
# als die Notebooks — Betriebshöfe und Ausstiegshalte sind dann mitgezählt.
BASISFILTER = ('delay_s: * and not stop_name: ("Betriebshof*" '
               'or "*[Ausstieg]" or "*[Endstelle]")')

VON, BIS = "2026-04-27T00:00:00.000Z", "2026-07-29T23:59:59.999Z"

# ── Das Laufzeitfeld für die zweite Kennzahl ─────────────────────────────────
#
# „Anteil außerhalb des Pünktlichkeitsfensters" ist ein Quotient und in Lens nur
# über eine Formel darstellbar. Formelspalten muss man als Saved Object von Hand
# ausschreiben (versteckte Rechenspalten plus ein tinymath-Baum) — fehleranfällig
# und schlecht zu prüfen.
#
# Stattdessen bekommt die Data View ein Laufzeitfeld, das je Abfahrt 1 oder 0
# liefert. Der Mittelwert davon IST der gesuchte Anteil, und damit ist die Kachel
# genau so gebaut wie die Mittelwertkachel — eine `average`-Spalte.
#
# Nebeneffekt, der das Feld auch außerhalb dieser Grafik nützlich macht: Die
# Definition des Vertragsfensters steht damit sichtbar in Kibana und lässt sich
# in Discover und in jeder anderen Visualisierung wiederverwenden.
LAUFZEITFELD = "ausserhalb_fenster"
LAUFZEITSKRIPT = (
    "def d = doc['delay_s']; "
    "if (d.size() == 0) return; "
    "emit(d.value <= -120 || d.value >= 240 ? 1 : 0);"
)

# Format der beiden Kennzahlen. `id` und `params` gehen unverändert in die
# Lens-Spalte.
FORMAT_SEKUNDEN = {"id": "number", "params": {"decimals": 0, "suffix": " s"}}
FORMAT_PROZENT = {"id": "percent", "params": {"decimals": 1}}

# Vier Kacheln, zwei Kennzahlen mal zwei Netze. Die Reihenfolge bestimmt die
# Anordnung im Dashboard: obere Zeile Mittelwerte, untere Zeile Anteile.
KACHELN = [
    ("szene4-mittelwert-tram", "Ø Abweichung — Straßenbahn", "Straßenbahn",
     "tram-departures-v2", FARBE_NETZ["Tram"], "delay_s", FORMAT_SEKUNDEN),
    ("szene4-mittelwert-ubahn", "Ø Abweichung — U-Bahn", "U-Bahn",
     "ubahn-departures-v2", FARBE_NETZ["U-Bahn"], "delay_s", FORMAT_SEKUNDEN),
    ("szene4-ausserhalb-tram", "Außerhalb des Fensters — Straßenbahn",
     "Straßenbahn", "tram-departures-v2", FARBE_NETZ["Tram"],
     LAUFZEITFELD, FORMAT_PROZENT),
    ("szene4-ausserhalb-ubahn", "Außerhalb des Fensters — U-Bahn",
     "U-Bahn", "ubahn-departures-v2", FARBE_NETZ["U-Bahn"],
     LAUFZEITFELD, FORMAT_PROZENT),
]
DASHBOARD = "szene4-mittelwerte"


def ruf(pfad: str, methode: str = "GET", koerper=None):
    daten = json.dumps(koerper).encode() if koerper is not None else None
    anfrage = urllib.request.Request(f"{KIBANA}{pfad}", data=daten,
                                     method=methode)
    anfrage.add_header("kbn-xsrf", "true")
    anfrage.add_header("Content-Type", "application/json")
    import base64
    schluessel = base64.b64encode(f"{ES_USER}:{ES_PASSWORD}".encode()).decode()
    anfrage.add_header("Authorization", f"Basic {schluessel}")
    try:
        with urllib.request.urlopen(anfrage, timeout=60) as antwort:
            roh = antwort.read()
            return json.loads(roh) if roh else {}
    except urllib.error.HTTPError as fehler:
        raise SystemExit(f"{methode} {pfad} -> HTTP {fehler.code}\n"
                         f"{fehler.read().decode()[:1200]}")


def lens_objekt(titel: str, beschriftung: str, index: str, farbe: str,
                feld: str, format_: dict) -> dict:
    """Attribute einer Lens-Metric-Kachel mit fester Farbe."""
    ebene, spalte = "ebene1", "wert"
    return {
        "attributes": {
            "title": titel,
            "description": ("Mittelwert von delay_s über das Analysefenster. "
                            "Erzeugt von scripts/kibana_kacheln.py."),
            "visualizationType": "lnsMetric",
            "state": {
                "datasourceStates": {
                    "formBased": {
                        "layers": {
                            ebene: {
                                "columns": {
                                    spalte: {
                                        "label": beschriftung,
                                        "dataType": "number",
                                        "operationType": "average",
                                        "sourceField": feld,
                                        "isBucketed": False,
                                        "scale": "ratio",
                                        "params": {
                                            "emptyAsNull": True,
                                            "format": format_,
                                        },
                                    }
                                },
                                "columnOrder": [spalte],
                                "incompleteColumns": {},
                                "sampling": 1,
                            }
                        }
                    }
                },
                "internalReferences": [],
                "filters": [],
                "query": {"language": "kuery",
                          "query": f'{BASISFILTER} and _index: "{index}"'},
                "visualization": {
                    "layerId": ebene,
                    "layerType": "data",
                    "metricAccessor": spalte,
                    "color": farbe,
                    "showBar": False,
                },
                "adHocDataViews": {},
            },
        },
        "references": [{
            "type": "index-pattern", "id": DATA_VIEW,
            "name": f"indexpattern-datasource-layer-{ebene}",
        }],
    }


def dashboard_objekt() -> dict:
    tafeln = []
    for nr, (kennung, titel, *_rest) in enumerate(KACHELN):
        # 48 Spalten Raster, zwei Kacheln je Zeile. Bewusst nur 10 Einheiten
        # hoch: In einem hohen Panel skaliert Lens die Zahl auf Bildschirmhöhe,
        # und im Dashboard sieht das aus wie ein Plakat.
        tafeln.append({
            "version": "8.17.2", "type": "lens",
            "gridData": {"x": (nr % 2) * 24, "y": (nr // 2) * 10,
                         "w": 24, "h": 10, "i": str(nr + 1)},
            "panelIndex": str(nr + 1),
            "embeddableConfig": {"enhancements": {}},
            "panelRefName": f"panel_{nr}",
            "title": titel,
        })
    return {
        "attributes": {
            "title": "Szene 4 — Mittelwerte Tram gegen U-Bahn",
            "description": ("Für das Video. Die beiden Zahlen liegen nah "
                            "beieinander — das ist die Aussage der Szene. "
                            "Erzeugt von scripts/kibana_kacheln.py."),
            "panelsJSON": json.dumps(tafeln),
            "optionsJSON": json.dumps({"hidePanelTitles": False,
                                       "useMargins": True,
                                       "syncColors": False,
                                       "syncCursor": True,
                                       "syncTooltips": False}),
            "timeRestore": True,
            "timeFrom": VON,
            "timeTo": BIS,
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(
                {"query": {"language": "kuery", "query": ""}, "filter": []})},
        },
        "references": [
            {"name": f"panel_{nr}", "type": "lens", "id": kennung}
            for nr, (kennung, *_r) in enumerate(KACHELN)
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--loeschen", action="store_true",
                   help="Kacheln und Dashboard wieder entfernen")
    args = p.parse_args()

    if args.loeschen:
        for typ, kennung in ([("dashboard", DASHBOARD)]
                             + [("lens", k[0]) for k in KACHELN]):
            try:
                ruf(f"/api/saved_objects/{typ}/{kennung}", "DELETE")
                print(f"gelöscht: {typ}/{kennung}")
            except SystemExit as fehler:
                print(f"übersprungen: {typ}/{kennung} ({fehler})")
        return 0

    dv = ruf(f"/api/data_views/data_view/{DATA_VIEW}")
    print(f"Data View: {dv['data_view']['title']} "
          f"({dv['data_view'].get('name')})")

    # Laufzeitfeld anlegen oder aktualisieren. Die API kennt beides getrennt:
    # POST legt an und scheitert, wenn es schon da ist; POST auf .../{name}
    # aktualisiert. Deshalb erst aktualisieren, dann anlegen.
    feld = {"name": LAUFZEITFELD,
            "runtimeField": {"type": "long",
                             "script": {"source": LAUFZEITSKRIPT}}}
    try:
        ruf(f"/api/data_views/data_view/{DATA_VIEW}/runtime_field/"
            f"{LAUFZEITFELD}", "POST", {"runtimeField": feld["runtimeField"]})
        print(f"Laufzeitfeld aktualisiert: {LAUFZEITFELD}\n")
    except SystemExit:
        ruf(f"/api/data_views/data_view/{DATA_VIEW}/runtime_field",
            "POST", feld)
        print(f"Laufzeitfeld angelegt: {LAUFZEITFELD}\n")

    for kennung, titel, beschriftung, index, farbe, feld, fmt in KACHELN:
        ruf(f"/api/saved_objects/lens/{kennung}?overwrite=true", "POST",
            lens_objekt(titel, beschriftung, index, farbe, feld, fmt))
        print(f"angelegt: {titel:<38} {farbe}  {feld}")

    ruf(f"/api/saved_objects/dashboard/{DASHBOARD}?overwrite=true", "POST",
        dashboard_objekt())
    print(f"\nDashboard: {KIBANA}/app/dashboards#/view/{DASHBOARD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
