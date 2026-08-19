# Berlin Tram & U-Bahn — Delay Analysis

A semester project exploring punctuality, delay propagation, and the infrastructure economics of Berlin's tram and subway networks, combining a live Elasticsearch data pipeline with statistical analysis in Jupyter.

The project is structured as a joint submission for two courses at HTW Berlin:
- **NoSQL Databases**: Elasticsearch pipeline, index design, Kibana
- **Data Science**: Hypothesis testing, delay propagation, cost modelling

---

## What this project analyses

1. **Is the tram really worse than the U-Bahn?** paired comparison of both networks, collected simultaneously under identical conditions
2. **Where does unreliability come from?** delay generated per track segment, rather than delay observed per stop
3. **Do missing traffic signal priorities explain it?** linking Berlin's LSA dataset to measured delay — including where that link fails to hold
4. **What would fixing it cost?** cost of delay, three concrete measures, and a tram vs. U-Bahn infrastructure comparison
5. **What should be done?** ranked measures by euro per passenger-hour saved, plus a reliability prediction model

### Headline findings

| Finding | Value |
|---|---|
| Departures outside the punctuality window (−1 to +3 min) | Tram **30.0 %** vs. U-Bahn **9.9 %** |
| Departures ≥ 1 min **early** | Tram **19.2 %** vs. U-Bahn **5.9 %** |
| Effect size, mean delay (stop level) | r = 0.24 — *small* |
| Effect size, share ≥ 3 min late | r = 0.61 — *large* |
| Effect size, share ≥ 1 min early | r = 0.80 — *very large* |
| Cancellation rate (clean window) | Tram 0.52 % vs. U-Bahn **1.16 %** |
| Service interruptions per million departures | Tram **25.1** vs. U-Bahn 4.9 |
| Weather-related disruptions | Tram **19** vs. U-Bahn **0** |
| Delay concentration (Gini, 763 segments) | 0.54 — worst 20 % of segments produce 57 % |

> **The tram is not slower than the U-Bahn — it is less predictable.** And the more
> frequent deviation is the one nobody talks about: running *early*, which costs
> passengers a full headway rather than a few seconds.

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
| [`01_eda.ipynb`](notebooks/01_eda.ipynb) | EDA — Tram | Distributions, data quality (§ 2b, six findings), **early departures** (§ 3b), effective headway per line |
| [`02_eda.ipynb`](notebooks/02_eda.ipynb) | EDA — U-Bahn + network comparison | Same analysis for the subway, plus the **paired tram/U-Bahn comparison at stop level** (§ 6) |
| [`03_lsa_analyse.ipynb`](notebooks/03_lsa_analyse.ipynb) | Traffic signal priority | H6/H6b, **why H6b is circular** (§ 4c), non-circular counter-test on generated delay (§ 4d), measure derivation from the documented reasons (§ 4e) |
| [`04_hypothesen.ipynb`](notebooks/04_hypothesen.ipynb) | Hypothesis tests | H1–H4, why H1 fails and what it reveals (§ 3b), **n-inflation demonstrated empirically** (§ 7b) |
| [`04_delay_propagation.ipynb`](notebooks/04_delay_propagation.ipynb) | Delay propagation | Delay *generated* per segment; onset stops; **concentration curve and Gini** (§ 7) |
| [`05_kosten.ipynb`](notebooks/05_kosten.ipynb) | Cost analysis | Cost of measured delay; three concrete measures; tram vs. U-Bahn per km; historical context; **resilience** (§ 5) |
| [`06_entscheidungshilfe.ipynb`](notebooks/06_entscheidungshilfe.ipynb) | Decision aid | **Measure ranking** by euro per passenger-hour saved; **reliability model** P(delay ≥ 3 min) |

### Shared analysis modules

Notebooks share one definition of the analysis window, the exclusion rules and the
derived quantities, so that figures stay consistent across them:

| Module | Purpose |
|---|---|
| [`src/analysis/quality.py`](src/analysis/quality.py) | Analysis window, collector outage, operational-stop filter, thresholds |
| [`src/analysis/takt.py`](src/analysis/takt.py) | Effective headway per line (handles branch services), cost of early departures |
| [`src/analysis/segmente.py`](src/analysis/segmente.py) | Delay *generated* per segment (Δdelay), day-wise over the full collection period |

`segmente_gesamtzeitraum()` processes the whole period day by day, accumulating only
per-segment aggregates. This covers ~7.1 M segment observations across 60 weekdays
without holding them in memory; the result is cached to `data/processed/`.

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

### 2. Credentials

Credentials are **not** stored in the repository. Copy the template and fill it in:

```bash
cp .env.example .env
chmod 600 .env
# → set ES_PASSWORD and KIBANA_SYSTEM_PASSWORD
```

`.env` is git-ignored. Both `docker-compose.yml` and `config/settings.py` read from it,
so this is the single place where the password lives. Every script and notebook imports
`ES_USER` / `ES_PASSWORD` from `config.settings` and fails with a clear message if the
file is missing.

### 3. Start Elasticsearch & Kibana

```bash
docker-compose up -d
```

First run downloads images (~1 GB, one-time). After that:
- **Elasticsearch:** http://localhost:9200
- **Kibana:** http://localhost:5601 — login: `elastic`, password from `.env`

```bash
# Verify connection
source .env && curl -u "$ES_USER:$ES_PASSWORD" http://localhost:9200
```

### 4. Create indices

```bash
python -m src.elasticsearch.indices --mode tram
python -m src.elasticsearch.indices --mode ubahn
```

### 5. Configure Kibana

```bash
python -m src.elasticsearch.kibana_setup
```

Creates data views for all indices and a base dashboard at http://localhost:5601.

### 6. Seed static data (run once)

```bash
python -m src.collector.seed_stops --mode tram
python -m src.collector.seed_stops --mode ubahn
python -m src.collector.seed_routes --mode tram
python -m src.collector.seed_routes --mode ubahn
```

Loads ~200 tram stops, ~170 U-Bahn stops, and their line routes into Elasticsearch.

### 7. Seed LSA data (run once)

```bash
python -m src.collector.seed_lsa
```

Fetches all 2,305 traffic signal locations from the Berlin WFS service and enriches them with tram line proximity and ÖPNV priority status.

### 8. Start collecting

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

### 9. Run notebooks

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
