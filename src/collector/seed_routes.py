# src/collector/seed_routes.py
# Reconstructs the ordered stop sequence for every line from already-collected
# departure data in Elasticsearch — no BVG API calls required.
#
# Run after enough departure data has been collected (stop_sequence must be present):
#   python -m src.collector.seed_routes --mode tram
#   python -m src.collector.seed_routes --mode ubahn

import sys
import logging
import argparse
from collections import defaultdict
from elasticsearch import Elasticsearch

sys.path.insert(0, ".")
from config.settings import TransitConfig, CONFIGS
from src.elasticsearch.indices import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def fetch_departures_with_sequence(es: Elasticsearch, config: TransitConfig) -> list[dict]:
    """
    Return all departure documents that carry a stop_sequence value.
    Only the fields needed for route reconstruction are fetched.
    """
    resp = es.search(
        index=config.index_departures,
        query={"exists": {"field": "stop_sequence"}},
        source=["line_name", "trip_id", "stop_id", "stop_name", "stop_sequence", "stop_location"],
        size=10000,
    )
    total = resp["hits"]["total"]["value"]
    if total > 10000:
        log.warning(
            f"  Index enthält {total} passende Dokumente, aber es werden nur die ersten "
            f"10 000 geladen. Ggf. erneut ausführen wenn mehr Daten gesammelt wurden."
        )
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def build_routes(docs: list[dict]) -> dict[str, dict]:
    """
    Group docs by line_name → trip_id → stop_sequence and reconstruct one
    canonical route per line by picking the trip with the most unique stops.

    Returns {line_name: route_doc} where route_doc is ready to index into ES.
    """
    # line_name → trip_id → stop_sequence → stop entry
    # Keying the inner dict by stop_sequence deduplicates repeated observations
    # of the same stop within one trip across multiple collection rounds.
    by_line: dict[str, dict[str, dict[int, dict]]] = defaultdict(lambda: defaultdict(dict))

    for doc in docs:
        line_name     = doc.get("line_name")
        trip_id       = doc.get("trip_id")
        stop_sequence = doc.get("stop_sequence")

        if not (line_name and trip_id and stop_sequence is not None):
            continue

        by_line[line_name][trip_id][stop_sequence] = {
            "stop_id":       doc.get("stop_id"),
            "name":          doc.get("stop_name"),
            "stop_sequence": stop_sequence,
            "location":      doc.get("stop_location"),
        }

    routes: dict[str, dict] = {}
    for line_name, trips in by_line.items():
        # The trip with the highest number of unique stops is the best proxy
        # for the full route (short-turn trips would have fewer stops).
        best_stops = max(trips.values(), key=len)
        stops = sorted(best_stops.values(), key=lambda s: s["stop_sequence"])
        routes[line_name] = {
            "line_name":  line_name,
            "stop_count": len(stops),
            "stops":      stops,
        }

    return routes


def seed_routes(es: Elasticsearch, config: TransitConfig) -> None:
    log.info(f"[{config.display_name}] Rekonstruiere Routen aus '{config.index_departures}'...")

    docs = fetch_departures_with_sequence(es, config)
    log.info(f"  {len(docs)} Abfahrtsdokumente mit stop_sequence geladen.")

    if not docs:
        log.warning(
            "  Keine Dokumente mit stop_sequence gefunden. "
            "Stelle sicher dass der Collector bereits Daten gesammelt hat."
        )
        return

    routes = build_routes(docs)
    log.info(f"  {len(routes)} Linien rekonstruiert — indexiere nach '{config.index_routes}'...")

    for line_name, route_doc in sorted(routes.items()):
        es.index(index=config.index_routes, id=line_name, document=route_doc)
        log.info(f"  {line_name}: {route_doc['stop_count']} Haltestellen")

    log.info(f"\n[{config.display_name}] Fertig. {len(routes)} Routen in '{config.index_routes}' gespeichert.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BVG Route Reconstructor")
    parser.add_argument("--mode", choices=list(CONFIGS), required=True,
                        help="Transit network to reconstruct routes for (tram | ubahn)")
    args = parser.parse_args()

    client = get_client()
    seed_routes(client, CONFIGS[args.mode])
