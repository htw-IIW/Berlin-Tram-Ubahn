# src/collector/reseed_stops_from_departures.py
# Updates the lines field of existing stops from already-collected departure data.
# Run after seed_stops_gtfs.py to fill in which lines serve each stop.
#
# Uses a Terms aggregation on stop_id so only one ES query is needed
# regardless of how many departure documents exist.
#
# Run:
#   python -m src.collector.reseed_stops_from_departures --mode tram
#   python -m src.collector.reseed_stops_from_departures --mode ubahn

import sys
import logging
import argparse
from elasticsearch import Elasticsearch, helpers

sys.path.insert(0, ".")
from config.settings import TransitConfig, CONFIGS
from src.elasticsearch.indices import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Upper bound for unique stops per network; well above real-world counts
# (tram ~300, U-Bahn ~170) so the Terms bucket list is never truncated.
_MAX_STOPS = 2000
_MAX_LINES_PER_STOP = 50


def aggregate_stops(es: Elasticsearch, config: TransitConfig) -> list[dict]:
    """
    Run a single aggregation query against the departures index to extract:
      - one representative stop_name + stop_location per unique stop_id
      - all line_name values that ever served that stop

    Returns a list of {stop_id, lines} dicts — only the fields being updated.
    """
    resp = es.search(
        index=config.index_departures,
        size=0,   # no raw hits needed — aggregation results only
        aggs={
            "stops": {
                "terms": {
                    "field": "stop_id",
                    "size":  _MAX_STOPS,
                },
                "aggs": {
                    "lines": {
                        "terms": {
                            "field": "line_name",
                            "size":  _MAX_LINES_PER_STOP,
                        }
                    },
                },
            }
        },
    )

    return [
        {
            "stop_id": bucket["key"],
            "lines":   [b["key"] for b in bucket["lines"]["buckets"]],
        }
        for bucket in resp["aggregations"]["stops"]["buckets"]
    ]


def reseed_stops(es: Elasticsearch, config: TransitConfig) -> None:
    log.info(f"[{config.display_name}] Extrahiere Haltestellen aus '{config.index_departures}'...")

    docs = aggregate_stops(es, config)

    if not docs:
        log.warning("  Keine Haltestellen gefunden — sind bereits Abfahrtsdaten vorhanden?")
        return

    log.info(f"  {len(docs)} eindeutige Haltestellen gefunden — aktualisiere 'lines' in '{config.index_stops}'...")

    actions = [
        {
            "_op_type":      "update",
            "_index":        config.index_stops,
            "_id":           doc["stop_id"],
            "doc":           {"lines": doc["lines"]},
            "doc_as_upsert": False,   # skip stops not yet in the index
        }
        for doc in docs
    ]
    success, failed = helpers.bulk(es, actions, stats_only=True, raise_on_error=False)

    log.info(f"  Aktualisiert: {success} Haltestellen ({failed} nicht gefunden oder Fehler).")
    log.info(f"[{config.display_name}] Fertig.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reseed stops index from departure data")
    parser.add_argument("--mode", choices=list(CONFIGS), required=True,
                        help="Transit network (tram | ubahn)")
    args = parser.parse_args()

    client = get_client()
    reseed_stops(client, CONFIGS[args.mode])
