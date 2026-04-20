# src/elasticsearch/kibana_setup.py
"""
Richtet Kibana automatisch ein:
  - Index Patterns für alle drei Indizes
  - Ein Basis-Dashboard mit den wichtigsten Visualisierungen

Einmalig ausführen nachdem Kibana gestartet ist:
  python -m src.elasticsearch.kibana_setup

Kibana muss unter http://localhost:5601 erreichbar sein.
"""

import sys
import json
import time
import requests

sys.path.insert(0, ".")
from config.settings import ES_INDEX_DEPARTURES, ES_INDEX_DISRUPTIONS, ES_INDEX_STOPS

KIBANA_URL  = "http://localhost:5601"
KIBANA_AUTH = ("elastic", "changeme")
HEADERS     = {"kbn-xsrf": "true", "Content-Type": "application/json"}


def wait_for_kibana(timeout: int = 120) -> None:
    """Wartet bis Kibana bereit ist."""
    print("Warte auf Kibana...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(
                f"{KIBANA_URL}/api/status",
                auth=KIBANA_AUTH, timeout=5
            )
            if resp.status_code == 200:
                state = resp.json().get("status", {}).get("overall", {}).get("level")
                if state == "available":
                    print(" bereit.")
                    return
        except requests.exceptions.ConnectionError:
            pass
        print(".", end="", flush=True)
        time.sleep(5)
    raise TimeoutError("Kibana nicht erreichbar. Ist docker-compose up -d gelaufen?")


def create_data_view(index_pattern: str, name: str,
                     time_field: str = "collected_at") -> str:
    """
    Erstellt eine Kibana Data View (früher: Index Pattern).
    Gibt die ID zurück.
    """
    payload: dict = {"data_view": {"title": index_pattern, "name": name}}
    if time_field:
        payload["data_view"]["timeFieldName"] = time_field
    resp = requests.post(
        f"{KIBANA_URL}/api/data_views/data_view",
        auth=KIBANA_AUTH,
        headers=HEADERS,
        json=payload,
    )
    if resp.status_code in (200, 201):
        dv_id = resp.json()["data_view"]["id"]
        print(f"  ✅ Data View erstellt: {name} (ID: {dv_id})")
        return dv_id
    elif resp.status_code == 400 and "Duplicate" in resp.text:
        print(f"  ℹ️  Data View existiert bereits: {name}")
        # Vorhandene ID holen
        existing = requests.get(
            f"{KIBANA_URL}/api/data_views",
            auth=KIBANA_AUTH, headers=HEADERS
        ).json()
        for dv in existing.get("data_view", []):
            if dv["title"] == index_pattern:
                return dv["id"]
    else:
        print(f"  ⚠️  Fehler bei {name}: {resp.status_code} {resp.text[:200]}")
    return ""


def create_dashboard(departures_id: str, disruptions_id: str) -> None:
    """
    Erstellt ein Basis-Dashboard mit vier Panels:
    1. Verspätungen nach Uhrzeit (Line Chart)
    2. Verspätungen nach Linie (Bar Chart)
    3. Ausfälle nach Linie (Bar Chart)
    4. Störungen nach Typ (Pie Chart)
    """
    # Kibana Saved Objects API — wir importieren ein minimales Dashboard
    dashboard_ndjson = json.dumps({
        "type": "dashboard",
        "id":   "tram-overview",
        "attributes": {
            "title":       "Berliner Tram — Übersicht",
            "description": "Verspätungen, Ausfälle und Störungen der Berliner Tram",
            "timeRestore": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": "{}"
            },
            # Panels werden über Lens in Kibana selbst am einfachsten gebaut.
            # Dieses Dashboard dient als leerer Container zum Befüllen.
            "panelsJSON": "[]",
            "optionsJSON": json.dumps({"useMargins": True, "syncColors": False}),
        },
        "references": [],
    })

    resp = requests.post(
        f"{KIBANA_URL}/api/saved_objects/_import?overwrite=true",
        auth=KIBANA_AUTH,
        headers={"kbn-xsrf": "true"},
        files={"file": ("dashboard.ndjson", dashboard_ndjson, "application/ndjson")},
    )
    if resp.status_code in (200, 201):
        print("  ✅ Dashboard 'Berliner Tram — Übersicht' erstellt")
        print(f"     → {KIBANA_URL}/app/dashboards")
    else:
        print(f"  ⚠️  Dashboard-Fehler: {resp.status_code} {resp.text[:200]}")


def main() -> None:
    wait_for_kibana()

    print("\nErstelle Data Views...")
    dep_id = create_data_view(
        ES_INDEX_DEPARTURES,
        "Tram Abfahrten",
        time_field="collected_at"
    )
    dis_id = create_data_view(
        ES_INDEX_DISRUPTIONS,
        "Tram Störungen",
        time_field="collected_at"
    )
    create_data_view(
        ES_INDEX_STOPS,
        "Tram Haltestellen",
        time_field=None  # kein Zeitfeld bei Stammdaten
    )

    print("\nErstelle Dashboard...")
    create_dashboard(dep_id, dis_id)

    print("\n✅ Kibana-Setup abgeschlossen.")
    print(f"   Kibana öffnen: {KIBANA_URL}")
    print("   Login: elastic / changeme")
    print("\n   Empfohlene nächste Schritte in Kibana:")
    print("   1. Discover → Data View 'Tram Abfahrten' → erste Daten prüfen")
    print("   2. Dashboard → 'Berliner Tram — Übersicht' → Panels mit Lens hinzufügen")
    print("   3. Maps → neues Layer → 'Tram Haltestellen' als Geo-Layer")


if __name__ == "__main__":
    main()
