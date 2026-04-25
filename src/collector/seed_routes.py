# src/collector/seed_routes.py
# Builds the ordered stop sequence for every line in a transit network
# and indexes one document per line into the routes index.
#
# Run once (after seed_stops):
#   python -m src.collector.seed_routes --mode tram
#   python -m src.collector.seed_routes --mode ubahn

import sys
import time
import logging
import argparse
import requests

sys.path.insert(0, ".")
from config.settings import BVG_API_BASE, TransitConfig, CONFIGS
from src.elasticsearch.indices import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def resolve_line_id(line_name: str) -> str | None:
    """
    Find the HAFAS line ID for a given line name by searching /locations
    and inspecting the lines arrays of returned stops.
    Returns the first matching line ID, or None if not found.
    """
    resp = requests.get(
        f"{BVG_API_BASE}/locations",
        params={"query": line_name, "results": 50, "stops": "true", "poi": "false", "addresses": "false"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    locations = data if isinstance(data, list) else data.get("stops", [])

    for stop in locations:
        for line in stop.get("lines") or []:
            if line.get("name") == line_name and line.get("id"):
                return line["id"]
    return None


def fetch_route_stops(line_id: str) -> list[dict]:
    """Fetch the ordered stop list for a line from /lines/{id}/stops."""
    resp = requests.get(
        f"{BVG_API_BASE}/lines/{line_id}/stops",
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("stops", [])


def build_stop_entry(raw: dict, sequence: int) -> dict:
    """Convert one raw stop from the route response to an ES nested object."""
    loc = (raw.get("location") or {})
    geo = None
    if loc.get("latitude") and loc.get("longitude"):
        geo = {"lat": loc["latitude"], "lon": loc["longitude"]}

    # prefer an explicit stop_sequence from the API; fall back to positional index
    stop_sequence = raw.get("stop_sequence") or raw.get("stopSequence") or sequence

    return {
        "stop_id":       raw.get("id"),
        "name":          raw.get("name"),
        "stop_sequence": stop_sequence,
        "location":      geo,
    }


def seed_routes(es, config: TransitConfig) -> None:
    log.info(f"[{config.display_name}] Lade Linienrouten von der BVG-API...")
    indexed = 0

    for line_name in config.lines:
        try:
            line_id = resolve_line_id(line_name)
            if not line_id:
                log.warning(f"  {line_name}: keine Linien-ID gefunden — übersprungen")
                time.sleep(0.3)
                continue

            raw_stops = fetch_route_stops(line_id)
            stops = [build_stop_entry(s, i) for i, s in enumerate(raw_stops)]

            doc = {"line_name": line_name, "stops": stops}
            es.index(index=config.index_routes, id=line_name, document=doc)

            log.info(f"  {line_name}: {len(stops)} Haltestellen indexiert (ID: {line_id})")
            indexed += 1

        except requests.exceptions.RequestException as e:
            log.warning(f"  {line_name}: API-Fehler — {e}")
        except Exception as e:
            log.warning(f"  {line_name}: Fehler — {e}")

        time.sleep(0.3)

    log.info(f"\n[{config.display_name}] {indexed}/{len(config.lines)} Linienrouten indexiert.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BVG Route Seeder")
    parser.add_argument("--mode", choices=list(CONFIGS), required=True,
                        help="Transit network to seed routes for (tram | ubahn)")
    args = parser.parse_args()

    client = get_client()
    seed_routes(client, CONFIGS[args.mode])
