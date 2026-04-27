# src/collector/reseed_stops_from_departures.py
# Rebuilds the stops index entirely from already-collected departure data.
# Useful when seed_stops.py is unavailable or the stops index is out of sync.
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
from datetime import datetime, timezone
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

    Returns a list of stop documents ready for indexing into config.index_stops.
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
                    # one representative doc per stop for name + location
                    "top_hit": {
                        "top_hits": {
                            "size": 1,
                            "_source": ["stop_name", "stop_location"],
                        }
                    },
                    # all distinct lines that served this stop
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

    buckets = resp["aggregations"]["stops"]["buckets"]
    loaded_at = datetime.now(timezone.utc).isoformat()
    docs: list[dict] = []

    for bucket in buckets:
        stop_id = bucket["key"]
        source  = bucket["top_hit"]["hits"]["hits"][0]["_source"]
        lines   = [b["key"] for b in bucket["lines"]["buckets"]]

        # departures use stop_name/stop_location; stops index expects name/location
        docs.append({
            "stop_id":   stop_id,
            "name":      source.get("stop_name"),
            "location":  source.get("stop_location"),
            "lines":     lines,
            "loaded_at": loaded_at,
        })

    return docs


def reseed_stops(es: Elasticsearch, config: TransitConfig) -> None:
    log.info(f"[{config.display_name}] Extrahiere Haltestellen aus '{config.index_departures}'...")

    docs = aggregate_stops(es, config)

    if not docs:
        log.warning("  Keine Haltestellen gefunden — sind bereits Abfahrtsdaten vorhanden?")
        return

    log.info(f"  {len(docs)} eindeutige Haltestellen gefunden — schreibe nach '{config.index_stops}'...")

    actions = [
        {"_index": config.index_stops, "_id": doc["stop_id"], "_source": doc}
        for doc in docs
    ]
    success, failed = helpers.bulk(es, actions, stats_only=True)

    log.info(f"  Indexiert: {success} Haltestellen ({failed} Fehler).")
    log.info(f"[{config.display_name}] Fertig.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reseed stops index from departure data")
    parser.add_argument("--mode", choices=list(CONFIGS), required=True,
                        help="Transit network (tram | ubahn)")
    args = parser.parse_args()

    client = get_client()
    reseed_stops(client, CONFIGS[args.mode])
