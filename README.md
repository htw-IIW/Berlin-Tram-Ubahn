# Berlin Tram & U-Bahn — Delay Analysis

A semester project exploring punctuality, delay propagation, and the infrastructure economics of Berlin's tram and subway networks, combining a live Elasticsearch data pipeline with statistical analysis in Jupyter.

The project is structured as a joint submission for two courses at HTW Berlin:
- **NoSQL Databases**: Elasticsearch pipeline, index design, Kibana
- **Data Science**: Hypothesis testing, delay propagation, cost modelling

---

## What this project analyses

1. **How punctual is the tram?** delay distributions by line, time of day, and stop type
2. **Do missing traffic signal priorities cause delays?** linking Berlin's LSA dataset to measured tram delays (H6b)
3. **Where do delays originate and propagate?** trip-level delay diffing across stop sequences
4. **What does it cost?** operational cost of delay, LSA upgrade ROI, and a tram vs. U-Bahn infrastructure comparison

---

## Data

All data is collected continuously into Elasticsearch and is **not stored in this repository**. See [`DATASET.md`](DATASET.md) for full field-level schema documentation.

### Tram departures & disruptions — BVG REST API

Realtime departure data (delay in seconds, cancellations, trip IDs) is fetched every 60 seconds via a community-maintained REST API wrapper around BVG's HAFAS backend.

- **API:** `v6.bvg.transport.rest`
- **Owner / maintainer:** Jannis R. ([@derhuerst](https://github.com/derhuerst)) — community project, not an official BVG service
- **Data owner:** Berliner Verkehrsbetriebe (BVG)
- **Usage:** research/educational only; not for commercial redistribution

### Traffic signal locations — Berlin Open Geodata (LSA)

Coordinates and ÖPNV-priority status for all 2,305 traffic signals (Lichtsignalanlagen) in Berlin, fetched from the city's WFS endpoint.

- **Source:** `gdi.berlin.de` WFS service
- **Owner:** Senatsverwaltung für Stadtentwicklung, Bauen und Wohnen (SenStadt Berlin)
- **License:** [Datenlizenz Deutschland – Zero – Version 2.0 (DL-DE Zero 2.0)](https://www.govdata.de/dl-de/zero-2-0) — free reuse including commercial
- **Inactive LSA annotations:** Drucksache 19/19804 (Berliner Abgeordnetenhaus, August 2024), Senatsverwaltung für Mobilität (SenMobil Berlin); public parliamentary document

### Stop & route reference data — VBB GTFS

Static timetable data used to seed stop IDs and line routes.

- **Source:** [Mobilithek](https://mobilithek.info) VBB General Transit Feed Specification export
- **Owner:** Verkehrsverbund Berlin-Brandenburg (VBB)
- **License:** [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) — attribution required

---

## Dataset snapshot

| | Tram | U-Bahn |
|---|---|---|
| Lines | M1, M2, M4–M6, M8, M10, M13, M17, 12, 16, 21, 22, 27, 37, 50, 60–63, 67, 68 | U1–U9 |
| Stops | ~200 | ~170 |
| Collection interval | 60 s | 60 s |
| Collection start | March 2026 | March 2026 |
| Index size (est. after 2 months) | ~3 GB total across all indices | |

---

## Elasticsearch indices

Four indices per network (prefix `tram-*` / `ubahn-*`):

| Index | Contents | Key fields |
|---|---|---|
| `*-departures` | One row per departure event | `line_name`, `stop_name`, `delay_s`, `planned_when`, `trip_id`, `hour_of_day`, `day_of_week`, `cancelled` |
| `*-disruptions` | Service disruption records | `line_name`, `summary`, `remark_type`, `valid_from`, `valid_until` |
| `*-stops` | Static stop reference | `stop_id`, `name`, `location` (geo_point), `lines` |
| `*-routes` | Ordered stop sequences per line | `line_name`, `stops` (nested: `stop_id`, `name`, `stop_sequence`, `location`) |

Additional index loaded from Berlin Open Geodata:

| Index | Contents | Source |
|---|---|---|
| `lsa-standorte` | 2,305 traffic signal locations with ÖPNV priority status | SenStadt Berlin WFS |

→ Full field-level schema, example documents, and collection method: [`DATASET.md`](DATASET.md)

---

## Notebooks

All notebooks are in [`notebooks/`](notebooks/) and run sequentially — each builds on the previous.

| Notebook | Title | Contents |
|---|---|---|
| [`01_eda.ipynb`](notebooks/01_eda.ipynb) | Exploratory Data Analysis | Delay distributions, cancellations, line comparisons, time-of-day patterns |
| [`01b_eda.ipynb`](notebooks/01b_eda.ipynb) | EDA — U-Bahn | Same analysis for the subway network |
| [`02_hypothesen.ipynb`](notebooks/02_hypothesen.ipynb) | Hypothesis Tests | H1–H4: mixed traffic, junction stops, M10 vs M4, rush-hour effects (Mann-Whitney-U, Kruskal-Wallis) |
| [`03_lsa_analyse.ipynb`](notebooks/03_lsa_analyse.ipynb) | LSA Analysis | Linking signal priority status to measured delays; H6/H6b; outlier map |
| [`04_delay_propagation.ipynb`](notebooks/04_delay_propagation.ipynb) | Delay Propagation | Per-trip delay deltas; worst segments; onset-stop analysis |
| [`05_kosten.ipynb`](notebooks/05_kosten.ipynb) | Cost Analysis | Operational cost of delays; LSA upgrade ROI; tram vs. U-Bahn infrastructure economics; historical context |

---

## Repository structure

```
berlin-tram-ubahn/
├── config/
│   └── settings.py              # ES connection, API URLs, network config
├── data/                        # gitignored — raw and processed exports if needed
├── deploy/
│   ├── install_services.sh      # systemd setup for Raspberry Pi
│   └── transit-collector@.service
├── docs/                        # additional documentation
├── logs/                        # gitignored — collector logs
├── notebooks/                   # Jupyter analysis (see table above)
├── scripts/
│   ├── collector_start.sh       # start collector as background process (--mode tram|ubahn)
│   ├── collector_stop.sh
│   └── collector_status.sh      # live status: PID, doc counts, last log lines
├── src/
│   ├── collector/
│   │   ├── collect_departures.py      # main collector loop (60 s interval)
│   │   ├── seed_stops.py              # seed stops from BVG API (run once)
│   │   ├── seed_stops_gtfs.py         # alternative: seed from VBB GTFS
│   │   ├── seed_routes.py             # seed line routes (run once)
│   │   └── reseed_stops_from_departures.py
│   ├── elasticsearch/
│   │   ├── indices.py                 # index definitions and mappings
│   │   └── kibana_setup.py            # data views and base dashboard
│   └── utils/
│       └── helpers.py
├── DATASET.md                   # full schema documentation
├── PI_setup.md                  # Raspberry Pi long-running setup
├── docker-compose.yml
└── requirements.txt
```

---

## Storage model

**No data is stored in the repository.** The collector writes directly to Elasticsearch running in Docker:

```
collect_departures.py
        │  writes to
        ▼
Elasticsearch container
        │  persists in
        ▼
Docker volume "esdata"
```

Estimated storage: ~150–200 MB/day (both networks), ~9–12 GB over two months after Elasticsearch compression.

For unattended long-running collection (24/7, auto-restart on crash or power loss), see [`PI_setup.md`](PI_setup.md) — covers Raspberry Pi 5 deployment with systemd services and Tailscale remote access.

---

## Setup

### Prerequisites

- [Anaconda](https://www.anaconda.com/download) (Python 3.11+)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — Elasticsearch and Kibana run as containers, no manual install needed

### 1. Clone and create environment

```bash
git clone https://github.com/<username>/Berlin-Tram-UBahn.git
cd Berlin-Tram-UBahn

conda create -n tram-analysis python=3.11
conda activate tram-analysis
pip install -r requirements.txt
```

> Each new terminal session: `conda activate tram-analysis`

### 2. Start Elasticsearch & Kibana

```bash
docker-compose up -d
```

First run downloads images (~1 GB, one-time). After that:
- **Elasticsearch:** http://localhost:9200
- **Kibana:** http://localhost:5601 — login: `elastic` / `changeme`

```bash
# Verify connection
curl -u elastic:changeme http://localhost:9200
```

### 3. Create indices

```bash
python -m src.elasticsearch.indices --mode tram
python -m src.elasticsearch.indices --mode ubahn
```

### 4. Configure Kibana

```bash
python -m src.elasticsearch.kibana_setup
```

Creates data views for all indices and a base dashboard at http://localhost:5601.

### 5. Seed static data (run once)

```bash
python -m src.collector.seed_stops --mode tram
python -m src.collector.seed_stops --mode ubahn
python -m src.collector.seed_routes --mode tram
python -m src.collector.seed_routes --mode ubahn
```

Loads ~200 tram stops, ~170 U-Bahn stops, and their line routes into Elasticsearch.

### 6. Seed LSA data (run once)

```bash
python -m src.collector.seed_lsa
```

Fetches all 2,305 traffic signal locations from the Berlin WFS service and enriches them with tram line proximity and ÖPNV priority status.

### 7. Start collecting

```bash
bash scripts/collector_start.sh --mode tram
bash scripts/collector_start.sh --mode ubahn
```

Both collectors run independently in the background — the terminal can be closed. Each fetches departures and disruptions for all stops every 60 seconds.

```bash
# Check status
bash scripts/collector_status.sh

# Follow live log
tail -f logs/collector-tram.log

# Stop
bash scripts/collector_stop.sh --mode tram
bash scripts/collector_stop.sh --mode ubahn
```

### 8. Run notebooks

```bash
jupyter notebook notebooks/
```

Start with `01_eda.ipynb`. The collector should have been running for at least a few hours before the analysis notebooks are meaningful.

### Managing containers

```bash
docker-compose stop    # stop containers, data in volume is preserved
docker-compose start   # restart
docker-compose down -v # remove everything including all collected data (irreversible)
```
