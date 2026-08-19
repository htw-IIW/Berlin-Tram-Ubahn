# config/settings.py
# Central configuration. Adding a new transit network = add a TransitConfig entry
# in CONFIGS. No other file needs to change.

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Zugangsdaten kommen aus .env im Repo-Root (nicht in Git, siehe .env.example).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# All product keys recognised by the BVG REST API
_BVG_PRODUCTS = ("tram", "bus", "subway", "suburban", "regional", "ferry", "express")


@dataclass(frozen=True)
class TransitConfig:
    """Everything that differs between transit networks (tram, U-Bahn, …)."""
    name: str                                      # used as --mode CLI arg
    api_product: str                               # BVG API product key
    lines: tuple[str, ...]                         # line names (documentation / filtering)
    index_departures: str
    index_disruptions: str
    index_stops: str
    index_routes: str
    grid_points: tuple[tuple[float, float], ...]   # (lat, lon) for stop discovery

    @property
    def api_filter_params(self) -> dict[str, str]:
        """BVG API params that enable only this network's product."""
        return {p: "true" if p == self.api_product else "false" for p in _BVG_PRODUCTS}

    @property
    def display_name(self) -> str:
        return {"tram": "Straßenbahn", "ubahn": "U-Bahn"}.get(self.name, self.name)


# ── Shared API + ES connection ────────────────────────────────────────────────

BVG_API_BASE = "https://v6.bvg.transport.rest"

COLLECT_INTERVAL_SEC    = 60   # seconds between collection rounds
DEPARTURE_WINDOW_MIN    = 20   # look-ahead per stop (minutes)
MAX_DEPARTURES_PER_STOP = 10   # cap per API call

ES_HOST     = os.getenv("ES_HOST", "http://tram-pi:9200")
ES_USER     = os.getenv("ES_USER", "elastic")
ES_PASSWORD = os.getenv("ES_PASSWORD", "")

if not ES_PASSWORD:
    raise RuntimeError(
        "ES_PASSWORD ist nicht gesetzt.\n"
        "Zugangsdaten stehen bewusst nicht mehr im Repository.\n"
        "Abhilfe: .env.example nach .env kopieren und das Passwort eintragen,\n"
        "oder ES_PASSWORD als Umgebungsvariable setzen."
    )


# ── Transit network configs ───────────────────────────────────────────────────

TRAM_CONFIG = TransitConfig(
    name="tram",
    api_product="tram",
    lines=(
        "M1", "M2", "M4", "M5", "M6", "M8", "M10", "M13", "M17",
        "12", "16", "21", "22", "27", "37", "50", "60", "61", "62", "63", "67", "68",
    ),
    index_departures="tram-departures",
    index_disruptions="tram-disruptions",
    index_stops="tram-stops",
    index_routes="tram-routes",
    # 12-point grid covering Berlin's eastern tram network (6 km radius each)
    grid_points=(
        (52.5200, 13.4050),   # Mitte / Hackescher Markt
        (52.5380, 13.4200),   # Prenzlauer Berg
        (52.5160, 13.4530),   # Friedrichshain
        (52.4950, 13.4050),   # Kreuzberg / Bergmannstr.
        (52.5140, 13.4900),   # Lichtenberg
        (52.5530, 13.4580),   # Weißensee
        (52.5560, 13.5060),   # Hohenschönhausen
        (52.5440, 13.5600),   # Marzahn
        (52.5280, 13.3750),   # Tiergarten / Hauptbahnhof
        (52.5050, 13.3320),   # Schöneberg
        (52.4860, 13.4320),   # Tempelhof (Straßenbahn-Rand)
        (52.5700, 13.3980),   # Pankow
    ),
)

UBAHN_CONFIG = TransitConfig(
    name="ubahn",
    api_product="subway",
    lines=("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9"),
    index_departures="ubahn-departures-v2",
    index_disruptions="ubahn-disruptions",
    index_stops="ubahn-stops",
    index_routes="ubahn-routes",
    # 12-point grid covering Berlin's city-wide U-Bahn network (6 km radius each)
    grid_points=(
        (52.5200, 13.4050),   # Mitte / Alexanderplatz (U2, U5, U8)
        (52.5200, 13.3000),   # Charlottenburg / Zoo (U2, U9)
        (52.5160, 13.4530),   # Friedrichshain / Warschauer Str (U1)
        (52.5600, 13.3800),   # Wedding / Gesundbrunnen (U6, U8)
        (52.4700, 13.3800),   # Schöneberg / Tempelhof (U4, U7)
        (52.5600, 13.2900),   # Tegel (U6 northern end)
        (52.4600, 13.3200),   # Steglitz (U9 southern end)
        (52.4700, 13.4500),   # Neukölln / Rudow (U7, U8)
        (52.5100, 13.5000),   # Lichtenberg (U5 eastern section)
        (52.5700, 13.4600),   # Pankow (U2 northern end)
        (52.5000, 13.3500),   # Wittenbergplatz (U1, U2, U3)
        (52.5300, 13.3300),   # Tiergarten / Hansaplatz (U9)
    ),
)

# Single registry — add new networks here, nothing else changes
CONFIGS: dict[str, TransitConfig] = {
    "tram":  TRAM_CONFIG,
    "ubahn": UBAHN_CONFIG,
}
