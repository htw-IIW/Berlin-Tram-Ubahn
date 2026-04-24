# src/elasticsearch/indices.py
# Index definitions for all ES indices.
# The departure/disruption/stop schema is identical across transit networks;
# only the index names differ — those come from TransitConfig.
#
# First-time setup:
#   python -m src.elasticsearch.indices --mode tram
#   python -m src.elasticsearch.indices --mode ubahn

from elasticsearch import Elasticsearch

from config.settings import ES_HOST, ES_USER, ES_PASSWORD, TransitConfig, CONFIGS


def get_client() -> Elasticsearch:
    return Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD))


# ── Shared mappings (same schema for every transit network) ───────────────────

def _departures_mapping() -> dict:
    return {
        "mappings": {
            "properties": {
                "collected_at":  {"type": "date"},
                "planned_when":  {"type": "date"},
                "when":          {"type": "date"},
                "delay_s":       {"type": "integer"},
                "cancelled":     {"type": "boolean"},
                "line_name":     {"type": "keyword"},
                "line_id":       {"type": "keyword"},
                "direction":     {"type": "keyword"},
                "stop_id":       {"type": "keyword"},
                "stop_name":     {"type": "keyword"},
                "stop_location": {"type": "geo_point"},
                "trip_id":       {"type": "keyword"},
                "hour_of_day":   {"type": "byte"},
                "day_of_week":   {"type": "byte"},
                "is_weekend":    {"type": "boolean"},
            }
        }
    }


def _disruptions_mapping() -> dict:
    return {
        "mappings": {
            "properties": {
                "collected_at": {"type": "date"},
                "trip_id":      {"type": "keyword"},
                "line_name":    {"type": "keyword"},
                "direction":    {"type": "keyword"},
                "stop_id":      {"type": "keyword"},
                "stop_name":    {"type": "keyword"},
                "remark_type":  {"type": "keyword"},
                "remark_code":  {"type": "keyword"},
                "summary":      {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "text":         {"type": "text"},
                "valid_from":   {"type": "date"},
                "valid_until":  {"type": "date"},
            }
        }
    }


def _stops_mapping() -> dict:
    return {
        "mappings": {
            "properties": {
                "stop_id":   {"type": "keyword"},
                "name":      {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "location":  {"type": "geo_point"},
                "lines":     {"type": "keyword"},
                "loaded_at": {"type": "date"},
            }
        }
    }


# ── Index management ──────────────────────────────────────────────────────────

def create_indices(es: Elasticsearch, config: TransitConfig, recreate: bool = False) -> None:
    """Create the three indices for one transit network."""
    index_configs = [
        (config.index_departures,  _departures_mapping()),
        (config.index_disruptions, _disruptions_mapping()),
        (config.index_stops,       _stops_mapping()),
    ]
    for index_name, mapping in index_configs:
        if es.indices.exists(index=index_name):
            if recreate:
                es.indices.delete(index=index_name)
                print(f"  Gelöscht:  {index_name}")
            else:
                print(f"  Existiert bereits (übersprungen): {index_name}")
                continue
        es.indices.create(index=index_name, mappings=mapping["mappings"])
        print(f"  Erstellt:  {index_name}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create Elasticsearch indices")
    parser.add_argument("--mode", choices=list(CONFIGS), required=True,
                        help="Transit network to create indices for (tram | ubahn)")
    parser.add_argument("--recreate", action="store_true",
                        help="Delete existing indices and recreate from scratch")
    args = parser.parse_args()

    client = get_client()
    cfg = CONFIGS[args.mode]
    print(f"Erstelle Elasticsearch-Indizes für {cfg.display_name}...")
    create_indices(client, cfg, recreate=args.recreate)
    print("Fertig.")
