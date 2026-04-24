# src/elasticsearch/kibana_setup.py
# Automatically sets up Kibana data views and a base dashboard for every
# registered transit network. Idempotent — safe to re-run.
#
# Run once after Kibana is up:
#   python -m src.elasticsearch.kibana_setup

import sys
import json
import time
import requests

sys.path.insert(0, ".")
from config.settings import ES_USER, ES_PASSWORD, CONFIGS

KIBANA_URL  = "http://localhost:5601"
KIBANA_AUTH = (ES_USER, ES_PASSWORD)
HEADERS     = {"kbn-xsrf": "true", "Content-Type": "application/json"}


def wait_for_kibana(timeout: int = 120) -> None:
    print("Warte auf Kibana...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{KIBANA_URL}/api/status", auth=KIBANA_AUTH, timeout=5)
            if resp.status_code == 200:
                level = resp.json().get("status", {}).get("overall", {}).get("level")
                if level == "available":
                    print(" bereit.")
                    return
        except requests.exceptions.ConnectionError:
            pass
        print(".", end="", flush=True)
        time.sleep(5)
    raise TimeoutError("Kibana nicht erreichbar. Ist docker-compose up -d gelaufen?")


def create_data_view(index_pattern: str, name: str, time_field: str | None = "collected_at") -> str:
    """Create a Kibana data view; returns its ID. No-ops if it already exists."""
    payload: dict = {"data_view": {"title": index_pattern, "name": name}}
    if time_field:
        payload["data_view"]["timeFieldName"] = time_field

    resp = requests.post(
        f"{KIBANA_URL}/api/data_views/data_view",
        auth=KIBANA_AUTH, headers=HEADERS, json=payload,
    )

    if resp.status_code in (200, 201):
        dv_id = resp.json()["data_view"]["id"]
        print(f"  ✅  Data View erstellt: {name} (ID: {dv_id})")
        return dv_id

    if resp.status_code == 400 and "Duplicate" in resp.text:
        print(f"  ℹ️   Data View existiert bereits: {name}")
        existing = requests.get(
            f"{KIBANA_URL}/api/data_views", auth=KIBANA_AUTH, headers=HEADERS
        ).json()
        for dv in existing.get("data_view", []):
            if dv["title"] == index_pattern:
                return dv["id"]

    print(f"  ⚠️   Fehler bei {name}: {resp.status_code} {resp.text[:200]}")
    return ""


def create_dashboard(dashboard_id: str, title: str, description: str) -> None:
    """Create a blank dashboard container. Panels are added via Kibana Lens."""
    ndjson = json.dumps({
        "type": "dashboard",
        "id":   dashboard_id,
        "attributes": {
            "title":       title,
            "description": description,
            "timeRestore": False,
            "panelsJSON":  "[]",
            "optionsJSON": json.dumps({"useMargins": True, "syncColors": False}),
            "kibanaSavedObjectMeta": {"searchSourceJSON": "{}"},
        },
        "references": [],
    })
    resp = requests.post(
        f"{KIBANA_URL}/api/saved_objects/_import?overwrite=true",
        auth=KIBANA_AUTH,
        headers={"kbn-xsrf": "true"},
        files={"file": ("dashboard.ndjson", ndjson, "application/ndjson")},
    )
    if resp.status_code in (200, 201):
        print(f"  ✅  Dashboard '{title}' erstellt")
    else:
        print(f"  ⚠️   Dashboard-Fehler: {resp.status_code} {resp.text[:200]}")


def main() -> None:
    wait_for_kibana()

    # Create data views + dashboard for every registered transit network
    for mode, config in CONFIGS.items():
        print(f"\n── {config.display_name} ──────────────────────────────────────")

        create_data_view(config.index_departures,  f"{config.display_name} Abfahrten")
        create_data_view(config.index_disruptions, f"{config.display_name} Störungen")
        create_data_view(config.index_stops,       f"{config.display_name} Haltestellen", time_field=None)

        create_dashboard(
            dashboard_id=f"{mode}-overview",
            title=f"Berliner {config.display_name} — Übersicht",
            description=f"Verspätungen, Ausfälle und Störungen der Berliner {config.display_name}",
        )

    print(f"\n✅  Kibana-Setup abgeschlossen. Öffnen: {KIBANA_URL}  (Login: {ES_USER} / {ES_PASSWORD})")
    print("\n   Empfohlene nächste Schritte:")
    print("   1. Discover → Data Views prüfen")
    print("   2. Dashboards → Panels mit Lens hinzufügen")
    print("   3. Maps → Geo-Layer aus den Haltestellen-Indizes")


if __name__ == "__main__":
    main()
