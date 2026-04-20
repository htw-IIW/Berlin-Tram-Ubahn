# src/elasticsearch/indices.py
"""
Index-Definitionen für alle drei ES-Indizes.
Beim ersten Start einmalig ausführen: python -m src.elasticsearch.indices
"""

from elasticsearch import Elasticsearch
from config.settings import ES_HOST, ES_USER, ES_PASSWORD
from config.settings import ES_INDEX_DEPARTURES, ES_INDEX_DISRUPTIONS, ES_INDEX_STOPS


def get_client() -> Elasticsearch:
    return Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD))


# ── Mapping: tram-departures ─────────────────────────────────────────────────
# Eine Zeile = eine Abfahrt eines Tram-Trips an einer Haltestelle.
# "delay" ist negativ bei Verfrühung, positiv bei Verspätung (Sekunden).
DEPARTURES_MAPPING = {
    "mappings": {
        "properties": {
            "collected_at":   {"type": "date"},          # Zeitpunkt der API-Abfrage
            "planned_when":   {"type": "date"},          # Fahrplanmäßige Abfahrt
            "when":           {"type": "date"},          # Prognostizierte Abfahrt (null = Ausfall)
            "delay_s":        {"type": "integer"},       # Verspätung in Sekunden
            "cancelled":      {"type": "boolean"},
            "line_name":      {"type": "keyword"},       # z.B. "M10"
            "line_id":        {"type": "keyword"},       # interne HAFAS-ID
            "direction":      {"type": "keyword"},       # Endstation
            "stop_id":        {"type": "keyword"},       # HAFAS-Haltestellennummer
            "stop_name":      {"type": "keyword"},
            "stop_location":  {"type": "geo_point"},     # {lat, lon} für Kibana Maps
            "trip_id":        {"type": "keyword"},
            # Abgeleitete Felder für einfachere Aggregationen in Kibana
            "hour_of_day":    {"type": "byte"},          # 0–23
            "day_of_week":    {"type": "byte"},          # 0=Mo … 6=So
            "is_weekend":     {"type": "boolean"},
        }
    }
}

# ── Mapping: tram-disruptions ────────────────────────────────────────────────
# Störungsmeldungen aus den HAFAS-Remarks der BVG-API.
# "remarks" in der API enthalten type=warning Einträge mit summary und text.
DISRUPTIONS_MAPPING = {
    "mappings": {
        "properties": {
            "collected_at":  {"type": "date"},
            "trip_id":       {"type": "keyword"},
            "line_name":     {"type": "keyword"},
            "direction":     {"type": "keyword"},
            "stop_id":       {"type": "keyword"},
            "stop_name":     {"type": "keyword"},
            "remark_type":   {"type": "keyword"},   # "warning", "hint", "status"
            "remark_code":   {"type": "keyword"},   # BVG-interner Code
            "summary":       {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "text":          {"type": "text"},
            "valid_from":    {"type": "date"},
            "valid_until":   {"type": "date"},
        }
    }
}

# ── Mapping: tram-stops ──────────────────────────────────────────────────────
# Stammdaten aller Tram-Haltestellen (einmalig geladen).
STOPS_MAPPING = {
    "mappings": {
        "properties": {
            "stop_id":    {"type": "keyword"},
            "name":       {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "location":   {"type": "geo_point"},
            "lines":      {"type": "keyword"},   # Liste aller Linien an dieser Haltestelle
        }
    }
}


def create_indices(es: Elasticsearch, recreate: bool = False) -> None:
    """Erstellt alle drei Indizes. Mit recreate=True werden bestehende gelöscht."""
    configs = [
        (ES_INDEX_DEPARTURES,  DEPARTURES_MAPPING),
        (ES_INDEX_DISRUPTIONS, DISRUPTIONS_MAPPING),
        (ES_INDEX_STOPS,       STOPS_MAPPING),
    ]
    for index_name, mapping in configs:
        if es.indices.exists(index=index_name):
            if recreate:
                es.indices.delete(index=index_name)
                print(f"  Gelöscht: {index_name}")
            else:
                print(f"  Existiert bereits (übersprungen): {index_name}")
                continue
        es.indices.create(index=index_name, body=mapping)
        print(f"  Erstellt: {index_name}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--recreate", action="store_true",
                        help="Bestehende Indizes löschen und neu anlegen")
    args = parser.parse_args()

    client = get_client()
    print("Erstelle Elasticsearch-Indizes...")
    create_indices(client, recreate=args.recreate)
    print("Fertig.")
