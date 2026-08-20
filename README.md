# Berlin Tram & U-Bahn Delay Analysis

A semester project at HTW Berlin on the punctuality of Berlin's tram and subway
networks, submitted jointly for two courses: **NoSQL Databases** (Elasticsearch
pipeline, index design, Kibana) and **Data Science** (statistical analysis).

The repository contains the **data pipeline**, not the data and not the analysis
notebooks. Two collectors poll the BVG realtime API every 60 seconds and write
departures and disruptions into Elasticsearch. Everything downstream reads from there.

You can point it at an existing cluster, or follow the setup below and run your own
collection from scratch; the pipeline is self-contained and seeds its own reference
data.

> The analysis notebooks are kept out of the repository while the work is in progress
> and will be published once it is finished.

---

## Data sources

| Source | Contents | Licence |
|---|---|---|
| [`v6.bvg.transport.rest`](https://v6.bvg.transport.rest) | Realtime departures and disruptions. Community wrapper around BVG's HAFAS backend by Jannis R. ([@derhuerst](https://github.com/derhuerst)) — not an official BVG service. Data owner: Berliner Verkehrsbetriebe (BVG) | research/educational use only |
| [`gdi.berlin.de`](https://gdi.berlin.de) WFS | Coordinates and ÖPNV-priority status of all 2,305 Berlin traffic signals (LSA). Owner: SenStadt Berlin | [DL-DE Zero 2.0](https://www.govdata.de/dl-de/zero-2-0) — free reuse |
| [Mobilithek](https://mobilithek.info) VBB GTFS | Static timetable data for seeding stops and routes. Owner: Verkehrsverbund Berlin-Brandenburg (VBB) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — **attribution required** |

Inactive-LSA annotations come from Drucksache 19/19804 (Berliner Abgeordnetenhaus,
August 2024), a public parliamentary document.

---

## Documentation

- **[`DATASET.md`](DATASET.md)** — field-level schema of every index, example documents,
  collection method, and the known quirks of the raw data. Read this before writing
  queries.
- **[`PI_setup.md`](PI_setup.md)** — unattended 24/7 collection on a Raspberry Pi 5:
  systemd services, auto-restart, Tailscale remote access, credential rotation.

---

## Setup

**Prerequisites:** [Anaconda](https://www.anaconda.com/download) (Python 3.11+) and
[Docker Desktop](https://www.docker.com/products/docker-desktop/). Elasticsearch and
Kibana run as containers — nothing to install by hand.

### 1. Clone and create the environment

```bash
git clone https://github.com/muggiron/Berlin-Tram-Ubahn.git
cd Berlin-Tram-Ubahn

conda create -n tram-analysis python=3.11
conda activate tram-analysis
pip install -r requirements.txt
```

### 2. Credentials

Credentials are **not** stored in the repository:

```bash
cp .env.example .env
chmod 600 .env
# → set ES_PASSWORD and KIBANA_SYSTEM_PASSWORD
```

`.env` is git-ignored and is the single place where the password lives — both
`docker-compose.yml` and `config/settings.py` read from it. Anything that talks to
Elasticsearch imports `ES_USER` / `ES_PASSWORD` from `config.settings` and fails with an
explicit message if the file is missing.

### 3. Start Elasticsearch & Kibana

```bash
docker-compose up -d
```

First run downloads images (~1 GB, one-time). Elasticsearch then listens on
http://localhost:9200, Kibana on http://localhost:5601 (login `elastic`, password from
`.env`).

```bash
source .env && curl -u "$ES_USER:$ES_PASSWORD" http://localhost:9200
```

### 4. Create indices and configure Kibana

```bash
python -m src.elasticsearch.indices --mode tram
python -m src.elasticsearch.indices --mode ubahn
python -m src.elasticsearch.kibana_setup
```

### 5. Seed reference data (once)

```bash
python -m src.collector.seed_stops  --mode tram
python -m src.collector.seed_stops  --mode ubahn
python -m src.collector.seed_routes --mode tram
python -m src.collector.seed_routes --mode ubahn
python -m src.collector.seed_lsa
```

Loads ~200 tram stops, ~170 U-Bahn stops, their line routes, and the 2,305 traffic
signal locations.

### 6. Start collecting

```bash
bash scripts/collector_start.sh --mode tram
bash scripts/collector_start.sh --mode ubahn
```

Both collectors run independently in the background; the terminal can be closed. Each
polls all stops every 60 seconds.

```bash
bash scripts/collector_status.sh        # PIDs, document counts, last log lines
tail -f logs/collector-tram.log         # live log
bash scripts/collector_stop.sh --mode tram
```

Expect roughly 150–200 MB per day across both networks. Nothing is written to the
repository — everything lives in the Docker volume `esdata`.

### Managing containers

```bash
docker-compose stop     # stop, keep data
docker-compose start    # resume
docker-compose down -v  # remove everything including collected data (irreversible)
```
