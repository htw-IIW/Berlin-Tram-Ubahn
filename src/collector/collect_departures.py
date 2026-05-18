# src/collector/collect_departures.py
# Continuous 60-second collection loop for one transit network.
#
# Continuous mode:  python -m src.collector.collect_departures --mode tram
#                   python -m src.collector.collect_departures --mode ubahn
# Single round:     python -m src.collector.collect_departures --mode tram --once

import sys
import time
import logging
import argparse
import requests
from elasticsearch import Elasticsearch, helpers

sys.path.insert(0, ".")
from config.settings import (
    BVG_API_BASE, COLLECT_INTERVAL_SEC,
    DEPARTURE_WINDOW_MIN, MAX_DEPARTURES_PER_STOP,
    TransitConfig, CONFIGS,
)
from src.elasticsearch.indices import get_client
from src.utils.helpers import enrich_departure, enrich_remark

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def fetch_stop_ids(es: Elasticsearch, config: TransitConfig) -> list[str]:
    try:
        resp = es.search(
            index=config.index_stops,
            query={"match_all": {}},
            source=["stop_id"],
            size=2000,
        )
        return [hit["_source"]["stop_id"] for hit in resp["hits"]["hits"]]
    except Exception as e:
        log.warning(f"Stops-Index nicht erreichbar: {e}")
        return []


def fetch_departures(stop_id: str, config: TransitConfig) -> list[dict]:
    resp = requests.get(
        f"{BVG_API_BASE}/stops/{stop_id}/departures",
        params={
            "duration": DEPARTURE_WINDOW_MIN,
            "results":  MAX_DEPARTURES_PER_STOP,
            **config.api_filter_params,   # enables only this network's product
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("departures", [])


def process_departures(departures: list[dict]) -> tuple[list[dict], list[dict]]:
    dep_docs, dis_docs = [], []
    for dep in departures:
        dep_docs.append(enrich_departure(dep))
        for remark in dep.get("remarks", []):
            if remark.get("type") in ("warning", "status"):
                dis_docs.append(enrich_remark(remark, dep))
    return dep_docs, dis_docs


def bulk_index(es: Elasticsearch, index: str, docs: list[dict]) -> int:
    if not docs:
        return 0
    actions = [
        {
            "_index": index,
            "_id": f"{doc.get('trip_id')}-{doc.get('stop_id')}-{doc.get('planned_when')}",
            "_source": doc,
            "op_type": "index",
        }
        for doc in docs
    ]
    success, _ = helpers.bulk(es, actions, stats_only=True)
    return success


def bulk_index_disruptions(es: Elasticsearch, index: str, docs: list[dict]) -> int:
    if not docs:
        return 0
    actions = [
        {
            "_index": index,
            "_id": doc.pop("_doc_id", None),
            "_source": doc,
            "op_type": "index",
        }
        for doc in docs
    ]
    success, _ = helpers.bulk(es, actions, stats_only=True)
    return success


def collect_once(es: Elasticsearch, stop_ids: list[str], config: TransitConfig) -> dict:
    """One full collection round across all stops for this network."""
    all_deps, all_dis = [], []
    errors = 0

    for stop_id in stop_ids:
        try:
            raw = fetch_departures(stop_id, config)
            deps, dis = process_departures(raw)
            all_deps.extend(deps)
            all_dis.extend(dis)
        except requests.exceptions.RequestException as e:
            log.debug(f"API-Fehler bei Stop {stop_id}: {e}")
            errors += 1
        except Exception as e:
            log.warning(f"Unerwarteter Fehler bei Stop {stop_id}: {e}")
            errors += 1
        time.sleep(0.05)   # 50 ms between requests to avoid hammering the API

    n_deps = bulk_index(es, config.index_departures, all_deps)
    n_dis  = bulk_index_disruptions(es, config.index_disruptions, all_dis)

    return {
        "departures_indexed":  n_deps,
        "disruptions_indexed": n_dis,
        "api_errors":          errors,
        "stops_queried":       len(stop_ids),
    }


def main(mode: str, once: bool = False) -> None:
    config = CONFIGS[mode]
    es = get_client()

    log.info(f"[{config.display_name}] Lade Haltestellen aus Elasticsearch...")
    stop_ids = fetch_stop_ids(es, config)

    if not stop_ids:
        log.error(
            f"Keine Haltestellen in '{config.index_stops}' gefunden. "
            f"Zuerst ausführen:\n  python -m src.collector.seed_stops --mode {mode}"
        )
        sys.exit(1)

    log.info(f"[{config.display_name}] {len(stop_ids)} Haltestellen geladen.")

    round_num = 0
    while True:
        round_num += 1
        start = time.time()
        stats = collect_once(es, stop_ids, config)
        elapsed = time.time() - start

        log.info(
            f"[{config.display_name}] Runde {round_num}: "
            f"{stats['departures_indexed']} Abfahrten, "
            f"{stats['disruptions_indexed']} Störungen indexiert "
            f"({stats['api_errors']} Fehler, {elapsed:.1f}s)"
        )

        if once:
            break

        sleep_time = max(0, COLLECT_INTERVAL_SEC - elapsed)
        log.info(f"[{config.display_name}] Nächste Runde in {sleep_time:.0f}s...")
        time.sleep(sleep_time)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BVG Departure Collector")
    parser.add_argument("--mode", choices=list(CONFIGS), required=True,
                        help="Transit network to collect (tram | ubahn)")
    parser.add_argument("--once", action="store_true",
                        help="Run a single collection round, then exit")
    args = parser.parse_args()
    main(mode=args.mode, once=args.once)
