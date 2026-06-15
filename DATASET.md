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

## Sensitivity

No personal or sensitive data. All collected information is public transit schedule and operational data. No user identifiers are present.
