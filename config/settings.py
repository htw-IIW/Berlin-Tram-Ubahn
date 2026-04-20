# config/settings.py
# Central configuration — edit here to change API base, credentials, or collection params.

BVG_API_BASE = "https://v6.bvg.transport.rest"

# Tram lines to monitor (Berliner Tram-Netz, Stand 2024)
TRAM_LINES_CORE = [
    "M1", "M2", "M4", "M5", "M6", "M8", "M10", "M13", "M17",
    "12", "16", "21", "22", "27", "37", "50", "60", "61", "62", "63", "67", "68",
]

# Collector timing
COLLECT_INTERVAL_SEC  = 60   # Pause between collection rounds (seconds)
DEPARTURE_WINDOW_MIN  = 20   # Look-ahead window per stop (minutes)
MAX_DEPARTURES_PER_STOP = 10  # Max departures returned per stop per call

# Elasticsearch connection
ES_HOST     = "http://localhost:9200"
ES_USER     = "elastic"
ES_PASSWORD = "changeme"

# Elasticsearch index names
ES_INDEX_DEPARTURES  = "tram-departures"
ES_INDEX_DISRUPTIONS = "tram-disruptions"
ES_INDEX_STOPS       = "tram-stops"
