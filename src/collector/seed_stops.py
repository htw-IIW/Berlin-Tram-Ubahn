# src/collector/seed_stops.py
"""
Loads all Berlin tram stops once into the tram-stops Elasticsearch index.

Run once before starting the collector:
  python -m src.collector.seed_stops
"""

import sys
import time
import logging
import requests
from datetime import datetime, timezone

sys.path.insert(0, ".")
from config.settings import BVG_API_BASE, ES_INDEX_STOPS
from src.elasticsearch.indices import get_client
from elasticsearch import helpers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Grid of lat/lon points covering Berlin's tram network areas.
# Using 6 km radius per point to ensure full coverage.
BERLIN_TRAM_GRID = [
    (52.5200, 13.4050),   # Mitte / Hackescher Markt
    (52.5380, 13.4200),   # Prenzlauer Berg
    (52.5160, 13.4530),   # Friedrichshain
    (52.4950, 13.4050),   # Kreuzberg / Bergmannstr.
    (52.5140, 13.4900),   # Lichtenberg
    (52.5530, 13.4580),   # Weißensee
    (52.5560, 13.5060),   # Hohenschönhausen
    (52.5440, 13.5600),   # Marzahn
    (52.5280, 13.3750),   # Tiergarten / Hauptbahnhof
    (52.5050, 13.3320),   # Schöneberg
    (52.4860, 13.4320),   # Tempelhof (Straßenbahn-Rand)
    (52.5700, 13.3980),   # Pankow
]


def fetch_stops_nearby(lat: float, lon: float, distance: int = 6000) -> list[dict]:
    resp = requests.get(
        f"{BVG_API_BASE}/stops/nearby",
        params={"latitude": lat, "longitude": lon, "distance": distance, "results": 500},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("stops", [])


def is_tram_stop(stop: dict) -> bool:
    products = stop.get("products") or {}
    return bool(products.get("tram"))


def stop_to_doc(stop: dict) -> dict:
    loc = stop.get("location") or {}
    geo = None
    if loc.get("latitude") and loc.get("longitude"):
        geo = {"lat": loc["latitude"], "lon": loc["longitude"]}

    # Collect line names from stationDHID or lines sub-array if present
    lines = []
    for entry in stop.get("lines") or []:
        name = entry.get("name")
        if name and name not in lines:
            lines.append(name)

    return {
        "stop_id":  stop.get("id"),
        "name":     stop.get("name"),
        "location": geo,
        "lines":    lines,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    es = get_client()
    seen: set[str] = set()
    docs: list[dict] = []

    log.info("Lade Tram-Haltestellen von der BVG-API...")

    for lat, lon in BERLIN_TRAM_GRID:
        try:
            stops = fetch_stops_nearby(lat, lon)
            tram_stops = [s for s in stops if is_tram_stop(s)]
            new = 0
            for stop in tram_stops:
                sid = stop.get("id")
                if sid and sid not in seen:
                    seen.add(sid)
                    docs.append(stop_to_doc(stop))
                    new += 1
            log.info(f"  ({lat:.3f}, {lon:.3f}): {len(tram_stops)} Tram-Haltestellen gefunden, {new} neu")
        except requests.exceptions.RequestException as e:
            log.warning(f"  API-Fehler bei ({lat}, {lon}): {e}")
        time.sleep(0.3)

    log.info(f"\n{len(docs)} eindeutige Tram-Haltestellen gesammelt.")

    if not docs:
        log.error("Keine Haltestellen gefunden — Abbruch.")
        sys.exit(1)

    actions = [
        {"_index": ES_INDEX_STOPS, "_id": doc["stop_id"], "_source": doc}
        for doc in docs
    ]
    success, failed = helpers.bulk(es, actions, stats_only=True)
    log.info(f"Indexiert: {success} Haltestellen ({failed} Fehler).")
    log.info("Fertig. Collector kann jetzt gestartet werden.")


if __name__ == "__main__":
    main()
