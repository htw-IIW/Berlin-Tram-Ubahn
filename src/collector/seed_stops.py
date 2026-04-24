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


def fetch_stops_for_line(line_name: str, config: TransitConfig) -> list[dict]:
    resp = requests.get(
        f"{BVG_API_BASE}/locations",
        params={"query": line_name, "results": 50, "stops": "true", "poi": "false", "addresses": "false"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    stops = data if isinstance(data, list) else data.get("stops", [])
    return [s for s in stops if is_relevant_stop(s, config)]


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
    docs: list[dict] = []

    log.info(f"[{config.display_name}] Lade Haltestellen von der BVG-API...")

    # stop_id → doc; built incrementally so duplicate stops across lines are merged
    stops_by_id: dict[str, dict] = {}

    for line in config.lines:
        try:
            relevant = fetch_stops_for_line(line, config)
            new = 0
            for stop in relevant:
                sid = stop.get("id")
                if not sid:
                    continue
                if sid not in stops_by_id:
                    stops_by_id[sid] = stop_to_doc(stop)
                    new += 1
                else:
                    # merge any additional line names returned for this stop
                    existing_lines = stops_by_id[sid]["lines"]
                    for entry in stop.get("lines") or []:
                        name = entry.get("name")
                        if name and name not in existing_lines:
                            existing_lines.append(name)
            log.info(f"  Linie {line}: {len(relevant)} Haltestellen, {new} neu")
        except requests.exceptions.RequestException as e:
            log.warning(f"  API-Fehler bei Linie {line}: {e}")
        time.sleep(0.3)

    docs = list(stops_by_id.values())

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
