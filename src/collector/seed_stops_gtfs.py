# src/collector/seed_stops_gtfs.py
# Seeds the stops index from the VBB GTFS static feed instead of the live API.
# Downloads ~80 MB ZIP, extracts 4 files, processes stop_times.txt in chunks.
#
# Run:
#   python -m src.collector.seed_stops_gtfs --mode tram
#   python -m src.collector.seed_stops_gtfs --mode ubahn

import sys
import logging
import argparse
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime, timezone

import requests
import pandas as pd
from elasticsearch import helpers

sys.path.insert(0, ".")
from config.settings import TransitConfig, CONFIGS
from src.elasticsearch.indices import get_client

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

GTFS_URL   = "https://www.vbb.de/fileadmin/user_upload/VBB/Dokumente/API-Datensaetze/gtfs-mastscharf/GTFS.zip"
GTFS_FILES = {"stops.txt", "routes.txt", "trips.txt", "stop_times.txt"}

# Standard German GTFS route_type codes
_GTFS_ROUTE_TYPE: dict[str, int] = {
    "tram":  900,
    "ubahn": 400,
}


def to_hafas_id(gtfs_stop_id: str) -> str:
    """
    Konvertiert GTFS stop_id zu HAFAS-ID.
    'de:11000:900007104::2' → '900007104'
    '900007104'             → '900007104'  (bereits HAFAS)

    HAFAS-IDs sind die längsten rein-numerischen Segmente (9 Stellen typisch).
    """
    digit_parts = [p for p in gtfs_stop_id.split(":") if p.isdigit()]
    if digit_parts:
        return max(digit_parts, key=len)
    return gtfs_stop_id


# ── Download ──────────────────────────────────────────────────────────────────

def download_gtfs(tmp_dir: Path) -> Path:
    zip_path = tmp_dir / "GTFS.zip"
    log.info("Lade VBB GTFS ZIP herunter (%s)...", GTFS_URL)
    with requests.get(GTFS_URL, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        total_mb = int(resp.headers.get("content-length", 0)) // (1024 * 1024)
        downloaded = 0
        with open(zip_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                fh.write(chunk)
                downloaded += len(chunk)
                print(
                    f"\r  {downloaded // (1024 * 1024)} / {total_mb} MB",
                    end="", flush=True,
                )
    print()
    log.info("  Download abgeschlossen: %s", zip_path)
    return zip_path


# ── Extraction ────────────────────────────────────────────────────────────────

def extract_gtfs_files(zip_path: Path, tmp_dir: Path) -> None:
    """Extract only the four needed files; ignore the rest of the ZIP."""
    log.info("  Extrahiere %s...", ", ".join(sorted(GTFS_FILES)))
    with zipfile.ZipFile(zip_path) as zf:
        for entry in zf.namelist():
            if Path(entry).name in GTFS_FILES:
                zf.extract(entry, tmp_dir)
    log.info("  Extraktion abgeschlossen.")


def _find(tmp_dir: Path, filename: str) -> Path:
    """Locate an extracted file regardless of subdirectory nesting in the ZIP."""
    matches = list(tmp_dir.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"{filename} nicht im GTFS ZIP gefunden.")
    return matches[0]


# ── GTFS processing ───────────────────────────────────────────────────────────

def collect_relevant_stop_ids(tmp_dir: Path, config: TransitConfig) -> set[str]:
    """
    Three-step filter through GTFS files:
      routes.txt  → keep routes matching route_type and config.lines
      trips.txt   → keep trip_ids belonging to those routes
      stop_times  → keep stop_ids appearing in those trips  (chunked)
    """
    route_type = _GTFS_ROUTE_TYPE[config.name]

    # ── routes ───────────────────────────────────────────────────────────────
    routes = pd.read_csv(_find(tmp_dir, "routes.txt"), dtype=str)
    routes["route_type"] = routes["route_type"].astype(int)
    relevant_routes = set(
        routes.loc[
            (routes["route_type"] == route_type)
            & routes["route_short_name"].isin(set(config.lines)),
            "route_id",
        ]
    )
    log.info("  %d passende Routen (route_type=%d)", len(relevant_routes), route_type)

    # ── trips ─────────────────────────────────────────────────────────────────
    trips = pd.read_csv(_find(tmp_dir, "trips.txt"), dtype=str, usecols=["route_id", "trip_id"])
    relevant_trips = set(trips.loc[trips["route_id"].isin(relevant_routes), "trip_id"])
    log.info("  %d Trips gefunden", len(relevant_trips))

    # ── stop_times (chunked — ~500 MB uncompressed) ───────────────────────────
    stop_ids: set[str] = set()
    chunk_num = 0
    for chunk in pd.read_csv(
        _find(tmp_dir, "stop_times.txt"),
        dtype=str,
        usecols=["trip_id", "stop_id"],   # load only the two needed columns
        chunksize=100_000,
    ):
        hits = chunk.loc[chunk["trip_id"].isin(relevant_trips), "stop_id"]
        stop_ids.update(hits)
        chunk_num += 1
        if chunk_num % 10 == 0:
            print(f"\r  stop_times: {chunk_num * 100_000:,} Zeilen gelesen, {len(stop_ids)} Stops bisher",
                  end="", flush=True)
    print()
    log.info("  %d eindeutige Haltestellen in stop_times gefunden", len(stop_ids))

    return stop_ids


def build_stop_docs(tmp_dir: Path, stop_ids: set[str]) -> list[dict]:
    stops = pd.read_csv(
        _find(tmp_dir, "stops.txt"),
        dtype=str,
        usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"],
    )
    filtered = stops[stops["stop_id"].isin(stop_ids)]
    loaded_at = datetime.now(timezone.utc).isoformat()
    docs: list[dict] = []

    for _, row in filtered.iterrows():
        geo = None
        try:
            geo = {"lat": float(row["stop_lat"]), "lon": float(row["stop_lon"])}
        except (TypeError, ValueError):
            pass

        docs.append({
            "stop_id":   to_hafas_id(row["stop_id"]),
            "name":      row["stop_name"],
            "location":  geo,
            "lines":     [],   # filled later by reseed_stops_from_departures
            "loaded_at": loaded_at,
        })

    return docs


# ── Orchestration ─────────────────────────────────────────────────────────────

def seed_stops_gtfs(es, config: TransitConfig) -> None:
    log.info("[%s] Starte GTFS-Import...", config.display_name)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        zip_path = download_gtfs(tmp_dir)
        extract_gtfs_files(zip_path, tmp_dir)

        # remove ZIP immediately after extraction to free disk space
        zip_path.unlink()
        log.info("  ZIP gelöscht.")

        stop_ids = collect_relevant_stop_ids(tmp_dir, config)
        docs     = build_stop_docs(tmp_dir, stop_ids)

    # tmp_dir is cleaned up automatically when the context exits

    log.info("  %d Stop-Dokumente aufgebaut — indexiere nach '%s'...", len(docs), config.index_stops)

    if not docs:
        log.warning("  Keine Haltestellen gefunden. Prüfe route_type und config.lines.")
        return

    actions = [
        {"_index": config.index_stops, "_id": doc["stop_id"], "_source": doc}
        for doc in docs
        # stop_id is already the HAFAS ID (converted in build_stop_docs)
    ]
    success, failed = helpers.bulk(es, actions, stats_only=True)
    log.info("  Indexiert: %d Haltestellen (%d Fehler).", success, failed)
    log.info("[%s] Fertig.", config.display_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed stops from VBB GTFS feed")
    parser.add_argument("--mode", choices=list(CONFIGS), required=True,
                        help="Transit network (tram | ubahn)")
    args = parser.parse_args()

    client = get_client()
    seed_stops_gtfs(client, CONFIGS[args.mode])
