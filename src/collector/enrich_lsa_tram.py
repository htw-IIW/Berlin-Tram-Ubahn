"""
Anreicherung der LSA-Daten mit Tram-Bezug.

Prüft für jede LSA ob sie in der Nähe einer Tram-Haltestelle liegt
und aktualisiert den oepnv_status von "unbekannt" auf "aktiv" (liegt
an Tramstrecke, hat Vorrang) oder "kein_tram" (keine Tramstrecke).

Voraussetzung: seed_lsa.py und der Tram-Collector müssen gelaufen sein.

Nutzung:
    python -m src.collector.enrich_lsa_tram
"""

import logging
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, scan

from config.settings import ES_HOST, ES_USER, ES_PASSWORD
from src.elasticsearch.indices import INDEX_LSA

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

INDEX_DEPARTURES = "tram-departures-v2"
RADIUS_METERS = 150  # LSA muss innerhalb von 150m einer Haltestelle liegen


def get_tram_stop_locations(es: Elasticsearch) -> list[dict]:
    """Holt alle einzigartigen Tram-Haltestellen mit Koordinaten aus tram-departures."""
    stop_locations: dict[str, dict] = {}
    stop_linien: dict[str, set] = {}

    for hit in scan(
        es,
        index=INDEX_DEPARTURES,
        query={"query": {"match_all": {}}},
        _source=["stop_name", "stop_location", "line_name"],
        size=5000,
    ):
        src = hit["_source"]
        name = src.get("stop_name")
        loc = src.get("stop_location")
        if not name or not loc:
            continue
        lat = loc.get("lat")
        lon = loc.get("lon")
        if lat is None or lon is None:
            continue

        if name not in stop_locations:
            stop_locations[name] = {"lat": lat, "lon": lon}
            stop_linien[name] = set()

        line = src.get("line_name")
        if line:
            stop_linien[name].add(line)

    stops = [
        {
            "name": name,
            "lat": loc["lat"],
            "lon": loc["lon"],
            "linien": sorted(stop_linien[name]),
        }
        for name, loc in stop_locations.items()
    ]

    log.info(f"{len(stops)} Tram-Haltestellen gefunden")
    return stops


def enrich() -> None:
    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD))

    # Alle Tram-Haltestellen laden
    stops = get_tram_stop_locations(es)

    # Für jede Haltestelle: Finde LSA im Radius
    update_actions = []
    matched_lsa_ids = set()

    for stop in stops:
        # Geo-Distance-Query auf LSA-Index
        result = es.search(
            index=INDEX_LSA,
            size=50,
            query={
                "bool": {
                    "must": {"match_all": {}},
                    "filter": {
                        "geo_distance": {
                            "distance": f"{RADIUS_METERS}m",
                            "location": {"lat": stop["lat"], "lon": stop["lon"]},
                        }
                    },
                }
            },
        )

        for hit in result["hits"]["hits"]:
            lsa_id = hit["_id"]
            current_status = hit["_source"].get("oepnv_status", "unbekannt")

            # Nur "unbekannt" aktualisieren — bereits manuell gesetzte
            # Status (inaktiv, nicht_vorhanden) nicht überschreiben
            if current_status == "unbekannt" and lsa_id not in matched_lsa_ids:
                matched_lsa_ids.add(lsa_id)
                update_actions.append({
                    "_op_type": "update",
                    "_index": INDEX_LSA,
                    "_id": lsa_id,
                    "doc": {
                        "oepnv_status": "aktiv",
                        "tram_linien": stop["linien"],
                    }
                })

    log.info(f"{len(matched_lsa_ids)} LSA als tram-relevant erkannt")

    # Alle verbleibenden "unbekannt" → "kein_tram"
    remaining = scan(
        es,
        index=INDEX_LSA,
        query={"query": {"term": {"oepnv_status": "unbekannt"}}}
    )
    kein_tram_count = 0
    for hit in remaining:
        update_actions.append({
            "_op_type": "update",
            "_index": INDEX_LSA,
            "_id": hit["_id"],
            "doc": {"oepnv_status": "kein_tram"}
        })
        kein_tram_count += 1

    log.info(f"{kein_tram_count} LSA als kein_tram klassifiziert")

    # Bulk-Update
    if update_actions:
        success, errors = bulk(es, update_actions, stats_only=True)
        log.info(f"Updates: {success}, Fehler: {errors}")

    # Finale Statistik
    es.indices.refresh(index=INDEX_LSA)
    agg = es.search(
        index=INDEX_LSA,
        size=0,
        aggs={"status": {"terms": {"field": "oepnv_status"}}},
    )
    log.info("Finale Verteilung:")
    for bucket in agg["aggregations"]["status"]["buckets"]:
        log.info(f"  {bucket['key']}: {bucket['doc_count']}")


if __name__ == "__main__":
    enrich()