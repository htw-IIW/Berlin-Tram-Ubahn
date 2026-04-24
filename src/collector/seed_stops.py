# src/collector/seed_stops.py
# Discovers and loads all stops for one transit network into Elasticsearch.
# Run once before starting the collector:
#   python -m src.collector.seed_stops --mode tram
#   python -m src.collector.seed_stops --mode ubahn

import sys
import time
import logging
import argparse
import requests
from datetime import datetime, timezone

sys.path.insert(0, ".")
from config.settings import BVG_API_BASE, TransitConfig, CONFIGS
from src.elasticsearch.indices import get_client
from elasticsearch import helpers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def fetch_stops_nearby(lat: float, lon: float, distance: int = 6000) -> list[dict]:
    resp = requests.get(
        f"{BVG_API_BASE}/stops/nearby",
        params={"latitude": lat, "longitude": lon, "distance": distance, "results": 500},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("stops", [])


def is_relevant_stop(stop: dict, config: TransitConfig) -> bool:
    """True if this stop serves the transit network described by config."""
    return bool((stop.get("products") or {}).get(config.api_product))


def stop_to_doc(stop: dict) -> dict:
    loc = stop.get("location") or {}
    geo = None
    if loc.get("latitude") and loc.get("longitude"):
        geo = {"lat": loc["latitude"], "lon": loc["longitude"]}

    lines = []
    for entry in stop.get("lines") or []:
        name = entry.get("name")
        if name and name not in lines:
            lines.append(name)

    return {
        "stop_id":   stop.get("id"),
        "name":      stop.get("name"),
        "location":  geo,
        "lines":     lines,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }


def seed_stops(es, config: TransitConfig) -> None:
    seen: set[str] = set()
    docs: list[dict] = []

    log.info(f"[{config.display_name}] Lade Haltestellen von der BVG-API...")

    for lat, lon in config.grid_points:
        try:
            stops = fetch_stops_nearby(lat, lon)
            relevant = [s for s in stops if is_relevant_stop(s, config)]
            new = 0
            for stop in relevant:
                sid = stop.get("id")
                if sid and sid not in seen:
                    seen.add(sid)
                    docs.append(stop_to_doc(stop))
                    new += 1
            log.info(f"  ({lat:.3f}, {lon:.3f}): {len(relevant)} Haltestellen, {new} neu")
        except requests.exceptions.RequestException as e:
            log.warning(f"  API-Fehler bei ({lat}, {lon}): {e}")
        time.sleep(0.3)

    log.info(f"\n[{config.display_name}] {len(docs)} eindeutige Haltestellen gesammelt.")

    if not docs:
        log.error("Keine Haltestellen gefunden — Abbruch.")
        sys.exit(1)

    actions = [
        {"_index": config.index_stops, "_id": doc["stop_id"], "_source": doc}
        for doc in docs
    ]
    success, failed = helpers.bulk(es, actions, stats_only=True)
    log.info(f"Indexiert: {success} Haltestellen ({failed} Fehler).")
    log.info(f"Fertig. Collector starten mit: python -m src.collector.collect_departures --mode {config.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BVG Stop Seeder")
    parser.add_argument("--mode", choices=list(CONFIGS), required=True,
                        help="Transit network to seed (tram | ubahn)")
    args = parser.parse_args()

    client = get_client()
    seed_stops(client, CONFIGS[args.mode])
