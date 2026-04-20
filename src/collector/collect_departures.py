# src/collector/collect_departures.py
"""
Sammelt kontinuierlich Abfahrtsdaten (inkl. Echtzeit-Verspätungen)
für alle Berliner Tram-Haltestellen und indexiert sie in Elasticsearch.

Läuft als Dauerprozess: python -m src.collector.collect_departures
Für einmaligen Test:    python -m src.collector.collect_departures --once
"""

import sys
import time
import logging
import argparse
import requests
from datetime import datetime, timezone
from elasticsearch import Elasticsearch, helpers

sys.path.insert(0, ".")
from config.settings import (
    BVG_API_BASE, TRAM_LINES_CORE, COLLECT_INTERVAL_SEC,
    DEPARTURE_WINDOW_MIN, MAX_DEPARTURES_PER_STOP,
    ES_INDEX_DEPARTURES, ES_INDEX_DISRUPTIONS, ES_INDEX_STOPS,
)
from src.elasticsearch.indices import get_client
from src.utils.helpers import enrich_departure, enrich_remark

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def fetch_tram_stop_ids(es: Elasticsearch) -> list[str]:
    """
    Holt alle Tram-Haltestellen-IDs aus dem ES-Stops-Index.
    Fallback: leere Liste wenn Index noch nicht befüllt.
    """
    try:
        resp = es.search(
            index=ES_INDEX_STOPS,
            body={"query": {"match_all": {}}, "_source": ["stop_id"]},
            size=2000,
        )
        return [hit["_source"]["stop_id"] for hit in resp["hits"]["hits"]]
    except Exception as e:
        log.warning(f"Stops-Index nicht erreichbar: {e}")
        return []


def fetch_departures(stop_id: str) -> list[dict]:
    """
    Ruft Abfahrten einer Haltestelle von der BVG-API ab.
    Gibt nur Tram-Abfahrten zurück (product=tram).
    """
    resp = requests.get(
        f"{BVG_API_BASE}/stops/{stop_id}/departures",
        params={
            "duration":  DEPARTURE_WINDOW_MIN,
            "results":   MAX_DEPARTURES_PER_STOP,
            "tram":      "true",
            # Alle anderen Verkehrsmittel ausblenden
            "bus":       "false",
            "subway":    "false",
            "suburban":  "false",
            "regional":  "false",
            "ferry":     "false",
            "express":   "false",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("departures", [])


def process_departures(departures: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Trennt Abfahrtsdokumente von Störungsdokumenten.
    Gibt (departure_docs, disruption_docs) zurück.
    """
    dep_docs = []
    dis_docs = []

    for dep in departures:
        # Abfahrt anreichern und speichern
        dep_docs.append(enrich_departure(dep))

        # Remarks (Störungen, Hinweise) separat indexieren
        for remark in dep.get("remarks", []):
            if remark.get("type") in ("warning", "status"):
                dis_docs.append(enrich_remark(remark, dep))

    return dep_docs, dis_docs


def bulk_index(es: Elasticsearch, index: str, docs: list[dict]) -> int:
    """Indexiert eine Liste von Dokumenten via Bulk-API. Gibt Anzahl Erfolge zurück."""
    if not docs:
        return 0
    actions = [{"_index": index, "_source": doc} for doc in docs]
    success, _ = helpers.bulk(es, actions, stats_only=True)
    return success


def collect_once(es: Elasticsearch, stop_ids: list[str]) -> dict:
    """
    Eine Sammelrunde über alle Haltestellen.
    Gibt Statistiken zurück.
    """
    all_deps = []
    all_dis  = []
    errors   = 0

    for stop_id in stop_ids:
        try:
            raw = fetch_departures(stop_id)
            deps, dis = process_departures(raw)
            all_deps.extend(deps)
            all_dis.extend(dis)
        except requests.exceptions.RequestException as e:
            log.debug(f"API-Fehler bei Stop {stop_id}: {e}")
            errors += 1
        except Exception as e:
            log.warning(f"Unerwarteter Fehler bei Stop {stop_id}: {e}")
            errors += 1
        time.sleep(0.05)  # 50ms zwischen Anfragen

    n_deps = bulk_index(es, ES_INDEX_DEPARTURES,  all_deps)
    n_dis  = bulk_index(es, ES_INDEX_DISRUPTIONS, all_dis)

    return {
        "departures_indexed": n_deps,
        "disruptions_indexed": n_dis,
        "api_errors": errors,
        "stops_queried": len(stop_ids),
    }


def main(once: bool = False) -> None:
    es = get_client()

    log.info("Lade Tram-Haltestellen aus Elasticsearch...")
    stop_ids = fetch_tram_stop_ids(es)

    if not stop_ids:
        log.error(
            "Keine Haltestellen gefunden. Zuerst seed_stops.py ausführen:\n"
            "  python -m src.collector.seed_stops"
        )
        sys.exit(1)

    log.info(f"{len(stop_ids)} Tram-Haltestellen geladen.")

    round_num = 0
    while True:
        round_num += 1
        start = time.time()
        stats = collect_once(es, stop_ids)
        elapsed = time.time() - start

        log.info(
            f"Runde {round_num}: "
            f"{stats['departures_indexed']} Abfahrten, "
            f"{stats['disruptions_indexed']} Störungen indexiert "
            f"({stats['api_errors']} Fehler, {elapsed:.1f}s)"
        )

        if once:
            break

        sleep_time = max(0, COLLECT_INTERVAL_SEC - elapsed)
        log.info(f"Nächste Runde in {sleep_time:.0f}s...")
        time.sleep(sleep_time)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BVG Tram Departure Collector")
    parser.add_argument(
        "--once", action="store_true",
        help="Nur eine Runde sammeln, dann beenden"
    )
    args = parser.parse_args()
    main(once=args.once)
