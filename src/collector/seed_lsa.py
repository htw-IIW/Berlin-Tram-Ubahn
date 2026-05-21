"""
Einmaliges Seeding der Berliner Lichtsignalanlagen (LSA) in Elasticsearch.

Datenquelle: WFS-Dienst der Berliner Geodateninfrastruktur
Lizenz: Datenlizenz Deutschland Zero 2.0 (frei nutzbar)

Anreicherung: ÖPNV-Vorrangstatus aus Drucksache 19/19804
(Schriftliche Anfrage Oda Hassepaß, GRÜNE, Aug. 2024)

Nutzung:
    python -m src.collector.seed_lsa          # Normal
    python -m src.collector.seed_lsa --force  # Index neu anlegen
"""

import argparse
import logging
import requests
from datetime import datetime, timezone
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from pyproj import Transformer

# Importiere ES-Verbindung und Index-Konstanten aus bestehendem Code.
# Passe den Import an die tatsächliche Struktur in config/settings.py an.
from config.settings import ES_HOST, ES_USER, ES_PASSWORD
from src.elasticsearch.indices import INDEX_LSA, MAPPING_LSA

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── WFS-Konfiguration ──────────────────────────────────────────────────────
# Schritt 1: GetCapabilities aufrufen um den exakten TypeName zu ermitteln.
# Der Layer heißt vermutlich "lsa:lichtsignalanlagen" oder ähnlich.
# Falls der Name anders ist, muss WFS_TYPENAME angepasst werden.

WFS_BASE = "https://gdi.berlin.de/services/wfs/lsa"
WFS_TYPENAME = "lsa:lsa"  # ← ggf. anpassen nach GetCapabilities

def get_wfs_capabilities() -> str:
    """Ruft GetCapabilities ab und gibt den XML-Text zurück.
    Nutze das um den korrekten TypeName zu finden falls der Default nicht stimmt."""
    url = f"{WFS_BASE}?SERVICE=WFS&REQUEST=GetCapabilities"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text

def fetch_lsa_geojson() -> dict:
    """Lädt alle LSA als GeoJSON vom WFS."""
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": WFS_TYPENAME,
        "OUTPUTFORMAT": "json",
        "COUNT": "10000",
    }
    log.info(f"Lade LSA-Daten von {WFS_BASE} ...")
    resp = requests.get(WFS_BASE, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    log.info(f"{len(data.get('features', []))} LSA-Features geladen")
    return data

# ── ÖPNV-Vorrangstatus (manuell aus Drs. 19/19804) ────────────────────────
# Kreuzungen an denen die ÖPNV-Beeinflussung NICHT aktiv ist.
# Quelle: Parlamentarische Anfrage Oda Hassepaß (GRÜNE), Aug. 2024
# https://pardok.parlament-berlin.de/starweb/adis/citat/VT/19/SchrAnfr/S19-19804.pdf

LSA_OHNE_VORRANG = {
    # Format: Teilstring der LSA-Bezeichnung → (status, bemerkung, linien)
    # Das Matching erfolgt case-insensitive über str.contains()

    # ── Linie M4 ──
    "Alexanderstraße": (
        "nicht_vorhanden",
        "Hohe Tramfrequenz, Einfachhaltestelle, Baustellensituation, "
        "Nähe Knoten Otto-Braun-Str - aus Verkehrssicherheitsgründen nicht möglich",
        ["M4", "M5", "M2"]
    ),
    "Greifswalder Straße / Michelangelostraße": (
        "inaktiv",
        "Kein stabiler Betrieb wegen veralteter Hardware, Modernisierung in Planung",
        ["M4"]
    ),
    "Antonplatz": (
        "inaktiv",
        "Neue Software nach Knotenumbau in Projektierung",
        ["M4", "12"]
    ),
    "Berliner Allee / Buschallee": (
        "inaktiv",
        "Bauzustand Berliner Wasserbetriebe",
        ["M4"]
    ),
    "Falkenberger Chaussee / Welsestraße": (
        "inaktiv",
        "Langsamfahrstelle wegen Gleisschäden",
        ["M4"]
    ),

    # ── Linie M5 ──
    "Landsberger Allee / Karl-Lade-Straße": (
        "inaktiv",
        "Langsamfahrstelle wegen Gleisschäden",
        ["M5"]
    ),
    "Hauptstraße / Suermondtstraße": (
        "inaktiv",
        "Nach Hardware-Modernisierung Software in Anpassung",
        ["M5"]
    ),
}


def match_oepnv_status(bezeichnung: str) -> tuple:
    """Prüft ob eine LSA-Bezeichnung zu einer bekannten Kreuzung ohne Vorrang passt.

    Returns:
        (status, bemerkung, linien) oder ("unbekannt", "", [])
    """
    bez_lower = bezeichnung.lower()
    for key, (status, bemerkung, linien) in LSA_OHNE_VORRANG.items():
        if key.lower() in bez_lower:
            return status, bemerkung, linien
    # Default: Status unbekannt — wir wissen nicht ob diese LSA
    # überhaupt an einer Tramstrecke liegt. Das wird in Schritt 2
    # (Spatial Join mit Tram-Haltestellen) aufgelöst.
    return "unbekannt", "", []


_transformer = Transformer.from_crs("EPSG:25833", "EPSG:4326", always_xy=True)


def parse_features(geojson: dict) -> list[dict]:
    """Wandelt GeoJSON-Features in ES-Dokumente um."""
    now = datetime.now(timezone.utc).isoformat()
    docs = []

    for feat in geojson.get("features", []):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})

        coords = geom.get("coordinates", [None, None])
        if not coords or len(coords) < 2:
            continue

        lon_raw, lat_raw = coords[0], coords[1]
        lon, lat = _transformer.transform(lon_raw, lat_raw)

        lsa_id = str(
            props.get("lsa_nr")
            or props.get("LSA_NR")
            or props.get("gml_id")
            or props.get("id")
            or f"lsa_{lat}_{lon}"
        )
        bezeichnung = str(
            props.get("standort")
            or props.get("bezeichnung")
            or props.get("BEZEICHNUNG")
            or props.get("name")
            or props.get("NAME")
            or "unbekannt"
        )

        status, bemerkung, linien = match_oepnv_status(bezeichnung)

        docs.append({
            "_index": INDEX_LSA,
            "_id": lsa_id,
            "_source": {
                "lsa_id":          lsa_id,
                "bezeichnung":     bezeichnung,
                "location":        {"lat": lat, "lon": lon},
                "oepnv_status":    status,
                "oepnv_bemerkung": bemerkung,
                "tram_linien":     linien,
                "seeded_at":       now,
            }
        })

    return docs


def seed(force: bool = False) -> None:
    """Hauptfunktion: Lädt LSA-Daten und indexiert sie."""
    es = Elasticsearch(ES_HOST, basic_auth=(ES_USER, ES_PASSWORD))

    # Index erstellen oder neu anlegen
    if es.indices.exists(index=INDEX_LSA):
        if force:
            log.info(f"Index {INDEX_LSA} wird gelöscht (--force)")
            es.indices.delete(index=INDEX_LSA)
        else:
            log.info(f"Index {INDEX_LSA} existiert bereits. --force zum Neuanlegen.")
            return

    es.indices.create(
        index=INDEX_LSA,
        mappings=MAPPING_LSA["mappings"],
        settings=MAPPING_LSA["settings"],
    )
    log.info(f"Index {INDEX_LSA} angelegt")

    # Daten laden
    # Falls der WFS-Request fehlschlägt, erst GetCapabilities prüfen:
    try:
        geojson = fetch_lsa_geojson()
    except Exception as e:
        log.error(f"WFS-Request fehlgeschlagen: {e}")
        log.info("Prüfe GetCapabilities für korrekten TypeName...")
        caps = get_wfs_capabilities()
        # Suche nach FeatureType-Namen im XML
        import re
        names = re.findall(r'<Name>(.*?)</Name>', caps)
        log.info(f"Verfügbare Layer: {names}")
        log.info("Passe WFS_TYPENAME in diesem Script an und starte neu.")
        return

    # Beim ersten Lauf: Properties eines Features loggen
    if geojson.get("features"):
        sample = geojson["features"][0].get("properties", {})
        log.info(f"Beispiel-Properties: {list(sample.keys())}")
        log.info(f"Beispiel-Werte: {sample}")

    docs = parse_features(geojson)
    log.info(f"{len(docs)} LSA-Dokumente vorbereitet")

    # Bulk-Indexierung
    success, errors = bulk(es, docs, stats_only=True)
    log.info(f"Indexiert: {success}, Fehler: {errors}")

    # Statistik
    es.indices.refresh(index=INDEX_LSA)
    count = es.count(index=INDEX_LSA)["count"]
    log.info(f"Gesamt im Index: {count}")

    # Status-Verteilung
    agg = es.search(
        index=INDEX_LSA,
        size=0,
        aggs={"status": {"terms": {"field": "oepnv_status"}}},
    )
    for bucket in agg["aggregations"]["status"]["buckets"]:
        log.info(f"  {bucket['key']}: {bucket['doc_count']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LSA-Daten in Elasticsearch laden")
    parser.add_argument("--force", action="store_true", help="Index neu anlegen")
    args = parser.parse_args()
    seed(force=args.force)