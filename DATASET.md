# Dataset Card: Berlin Tram & U-Bahn Realtime Departures

## Overview

Continuously collected realtime departure and disruption data for Berlin's tram and U-Bahn networks, stored in Elasticsearch.

All index mappings are defined explicitly before data ingestion. Elasticsearch's dynamic mapping would otherwise infer imprecise types: timestamps as `text`, coordinates as plain `float` pairs rather than `geo_point`, and short integers as `long`. The field names and types below reflect deliberate mapping decisions, not auto-detected ones.

---

## Dataset Snapshot

| | Tram | U-Bahn |
|---|---|---|
| Lines covered | M1, M2, M4–M6, M8, M10, M13, M17, 12, 16, 21, 22, 27, 37, 50, 60–63, 67, 68 | U1–U9 |
| Stops | ~200 | ~170 |
| Collection interval | 60 seconds | 60 seconds |
| Estimated size after 2 months | ~3 GB total across all indices | |
| Collection start | March 2026 | March 2026 |

---

## Indices & Data Schema

### Departures (`tram-departures-v2`, `ubahn-departures`)

| Field | Type | Description |
|---|---|---|
| `collected_at` | date | Timestamp when the record was collected |
| `planned_when` | date | Scheduled departure time |
| `when` | date | Realtime departure time (null if unavailable) |
| `delay_s` | integer | Delay in seconds (negative = early) |
| `cancelled` | boolean | Whether the trip is cancelled |
| `line_name` | keyword | Line identifier, e.g. `M1`, `U5` |
| `line_id` | keyword | Internal BVG line ID |
| `direction` | keyword | Destination (end stop name) |
| `stop_id` | keyword | BVG stop ID |
| `stop_name` | keyword | Human-readable stop name |
| `stop_location` | geo_point | `{ lat, lon }` — explicit mapping required for geo queries |
| `trip_id` | keyword | BVG trip ID |
| `hour_of_day` | byte | Derived from `planned_when` (0–23) |
| `day_of_week` | byte | Derived from `planned_when` (0=Mon … 6=Sun) |
| `is_weekend` | boolean | Derived: true if day_of_week ≥ 5 |

### Disruptions (`tram-disruptions`, `ubahn-disruptions`)

| Field | Type | Description |
|---|---|---|
| `collected_at` | date | Timestamp when the record was collected |
| `trip_id` | keyword | Affected trip |
| `line_name` | keyword | Affected line |
| `direction` | keyword | Affected direction |
| `stop_id` | keyword | Stop where disruption was reported |
| `stop_name` | keyword | Stop name |
| `remark_type` | keyword | `warning` or `status` |
| `remark_code` | keyword | BVG remark code |
| `summary` | text | Short disruption summary |
| `text` | text | Full disruption description |
| `valid_from` | date | Start of disruption validity |
| `valid_until` | date | End of disruption validity |

Disruptions are deduplicated via a deterministic MD5 hash (`trip_id | stop_id | remark_code | valid_from`).

### Stops (`tram-stops`, `ubahn-stops`)

| Field | Type | Description |
|---|---|---|
| `stop_id` | keyword | BVG stop ID |
| `name` | text/keyword | Stop name |
| `location` | geo_point | `{ lat, lon }` |
| `lines` | keyword | Lines serving this stop |
| `loaded_at` | date | When the stop was seeded |

### Routes (`tram-routes`, `ubahn-routes`)

| Field | Type | Description |
|---|---|---|
| `line_name` | keyword | Line identifier |
| `stops` | nested | Ordered list of stops: `stop_id`, `name`, `stop_sequence`, `location` |

### Traffic signals (`lsa-standorte`)

| Field | Type | Description |
|---|---|---|
| `lsa_id` | keyword | Derived unique ID from coordinates |
| `standort` | text | Location description from WFS |
| `location` | geo_point | `{ lat, lon }` |
| `oepnv_status` | keyword | `aktiv`, `inaktiv`, `nicht_vorhanden`, `kein_tram` |
| `tram_linien` | keyword | Tram lines within 150m radius (derived) |

---

## Typical Data Point (Departure)

```json
{
  "collected_at": "2026-04-10T08:32:00Z",
  "planned_when": "2026-04-10T08:35:00+02:00",
  "when":         "2026-04-10T08:36:30+02:00",
  "delay_s":      90,
  "cancelled":    false,
  "line_name":    "M10",
  "direction":    "S+U Warschauer Str.",
  "stop_id":      "900110006",
  "stop_name":    "Prenzlauer Allee/Danziger Str.",
  "stop_location": { "lat": 52.5378, "lon": 13.4224 },
  "trip_id":      "1|12345|0|86|10042026",
  "hour_of_day":  8,
  "day_of_week":  3,
  "is_weekend":   false
}
```

---

## Collection Method

1. Stop IDs are seeded once from the VBB GTFS dataset and supplemented via the BVG API's nearby-stops endpoint across a 12-point geographic grid covering Berlin.
2. Every 60 seconds, departures for each stop are fetched (20-minute look-ahead, max 10 results per stop).
3. Remarks of type `warning` or `status` are extracted from departure responses and stored as disruption documents.
4. All documents are bulk-indexed into Elasticsearch.

---

---

## Known Data Characteristics

These properties were established in `notebooks/01_eda.ipynb`, section 2b. They constrain
what the data can support and are enforced centrally in `src/analysis/quality.py`.

### 1. `delay_s` is minute-quantised

All 9.8 M delay values are exact multiples of 60. The aggregation over
`delay_s mod 60` finds **exactly one residue class** instead of the 60 expected at true
second resolution, and `delay_s` takes only **122 distinct values** across the whole index.
The BVG API reports delays in whole minutes; the seconds figure is a conversion, not a
measurement. `when` and `planned_when` are likewise minute-aligned, so the true
sub-minute delay cannot be recovered.

**Consequence:** medians of individual departures snap to the grid (they are 0 in most
groups), and rank tests run mostly on ties. Means over many observations remain precise —
the rounding contributes about 17.3/√n seconds to the standard error. Use **proportions
at grid thresholds** (60, 120, 180, 300, 600 s) as reliability measures.

### 2. Collector outage 27 June – 7 July 2026

Between 943 and ~12,000 documents per day were captured instead of the usual ~140,000.
The remaining records come from irregular sampling times and are unusable for rates,
daily profiles and trip reconstruction. Excluded via `analysefenster_query()`.

### 3. `cancelled` breaks after the restart — U-Bahn only

|  | U-Bahn before | U-Bahn after |
|---|---|---|
| documents/day | ~76,000 | ~76,000 |
| stops | 169 | 169 |
| realtime coverage | 83.9 % | 98.3 % |
| p90 / p95 delay | 82 / 134 s | 85 / 138 s |
| **cancelled** | **1.160 %** | **0.062 %** |

The tram does not show this break (0.521 % → 0.520 %), and several post-restart days
report exactly zero cancellations across ~76,000 departures. This is a capture artefact,
not a service improvement — most likely the API stopped returning cancelled trips instead
of flagging them. **Cancellation rates are only comparable within 27 Apr – 26 Jun.**

### 4. Realtime coverage jumps at the restart

Coverage rises in both networks (tram 81.0 % → 95.5 %, U-Bahn 83.9 % → 98.3 %).
Departures without realtime data are probably not a random subset. **Cross-sectional
comparisons over the full window are valid; time trends across 7 July are not.**

### 5. Operational stops are not passenger stops

Depots, alighting-only and turning points accumulate dwell time by design. Excluded via
`ist_betriebliche_haltestelle()`, which matches only `[Ausstieg]`, `[Endstelle]` and
`Betriebshof *`.

Square brackets alone are **not** an exclusion criterion — most bracketed names
distinguish platforms of the same stop (`U Alexanderplatz (Berlin) [Tram]`) and are
regular high-volume stops.

### 6. Timestamps are serialised inconsistently

`collected_at` appears both with and without microseconds. `pd.to_datetime` infers the
format from the first value and then fails on the other variant. Always pass
`format="ISO8601"`.

### 7. Disruption documents are not disruptions

Disruptions are not a separate feed — they are extracted from the `remarks` array
attached to each departure, deduplicated by MD5 of
(`trip_id`, `stop_id`, `remark_code`, `valid_from`). Since `remark_code` is consistently
`None`, one real disruption produces **one document per affected trip and stop, for its
entire validity**. A three-week engineering works notice generates hundreds of thousands
of documents.

Tram: 1,500,492 documents → **1,961 distinguishable incidents**.
U-Bahn: 765,008 documents → **3,067 incidents**.

Count incidents by deduplicating on (`line_name`, `summary`, `valid_from`). Document
shares are meaningless as frequency statements.

### 8. The disruption feed contains BVG test messages

Records prefixed `Test - Please ignore the following information` describe invented
events. The only weather-related U-Bahn message in the whole collection period is one of
these. Filter before analysis.

### 9. `stop_sequence` is never populated

The BVG departures endpoint does not return it, so both `*-routes` indices are empty —
`seed_routes.py` depends on the field it is meant to reconstruct. Stop order within a
trip is derived from `planned_when` instead (`src/analysis/segmente.py`).

### 10. LSA field naming

`standort` is empty for all 2,305 records; the location description is in `bezeichnung`.
`oepnv_bemerkung` holds the documented reason why a signal has no transit priority and is
essential for interpreting the status (see `notebooks/03_lsa_analyse.ipynb`, section 4e).

### 11. Collection period covers one season

27 April – ongoing, i.e. spring and summer only, about 26 % of a year. Icing of overhead
lines, leaf fall and snow clearance all fall outside the window and affect only the tram.
**No annual statements are possible.** The paired network comparison remains valid because
both networks were captured simultaneously under identical conditions — and the measured
gap is a *lower bound* on the annual gap.

---

## Sensitivity

No personal or sensitive data. All collected information is public transit schedule and
operational data. No user identifiers are present.
