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

### 2b. Second, shorter gap: 14–15 May 2026

A separate and previously undocumented interruption sits **inside** the May analysis
window used by `notebooks/03_lsa_analyse.ipynb`. Tram departures with `delay_s`, weekdays
only:

| Date | Documents | Share of a normal day |
|---|---|---|
| 13 May | 129,185 | 100 % |
| **14 May** | **81,432** | **63 %** |
| **15 May** | **1,425** | **1 %** |
| 18 May | 128,150 | 100 % |

The 15th is effectively missing; the 14th ends early. Unlike the June outage this one is
**not** excluded by `analysefenster_query()`, because the window it belongs to is
specified by date range in the notebook itself.

**Consequence:** harmless for cross-sectional measures — stop-level means over 15 weekdays
lose one day of input and shift by less than the run-to-run variation of the ongoing
collection. It matters for anything indexed by date: daily rates, weekday profiles, and
any before/after comparison spanning mid-May. The cluster bootstrap in
`03_lsa_analyse.ipynb`, section 4d-2, resamples calendar days and therefore treats the
short day as the smaller cluster it is, without special handling.

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

As of 10 Aug 2026 — collection is ongoing, so these grow:

| | documents | distinguishable incidents | ratio |
|---|---|---|---|
| Tram | 1,835,330 | **2,123** | 864 : 1 |
| U-Bahn | 836,096 | **3,449** | 242 : 1 |

Count incidents by deduplicating on (`line_name`, `summary`, `valid_from`). Document
shares are meaningless as frequency statements.

**This inflation is not duplication.** Both collectors assign a deterministic `_id` —
departures use `trip_id-stop_id-planned_when`, remarks use an MD5 over
(`trip_id`, `stop_id`, `remark_code`, `valid_from`) — and write with `op_type: "index"`,
so a repeated collection round overwrites the same document instead of appending. Because
Elasticsearch enforces uniqueness on `_id`, duplicates are structurally impossible rather
than merely unlikely. Verified on the departures index: for sampled trips the ratio of
documents to distinct stops is exactly 1.00, in May and in August alike.

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

### 12. The tram index contains one non-BVG operator

Line **88** belongs to the Schöneiche–Rüdersdorf tramway (SRS), a separate operator. It
appears in the data because the BVG departures endpoint also serves interchange stops.

| | line 88 |
|---|---|
| Documents | 4,640 (0.04 % of the tram index) |
| Stops | 1 — *S Friedrichshagen/Dahlwitzer Landstr.* |
| Share without `delay_s` | **100.0 %** |

Because the line supplies no realtime values at all, it never entered any delay statistic —
every one of those is conditioned on `delay_s` existing. It was visible in exactly one
place: the per-line completeness chart, where it ranked first at 100 % missing and read as
a flaw in the collection pipeline rather than what it is, a foreign operator without a
realtime feed.

It is now excluded throughout, so that the population is "BVG tram" and nothing else. The
rule lives in `src/analysis/quality.py` (`FREMDLINIEN`, `ist_fremdlinie`,
`ohne_fremdlinien`) and is applied both in the Elasticsearch filter
(`analysefenster_query`) and at the three points where a tram DataFrame is loaded.

> Effect on reported figures: tram document count 11,989,793 → 11,985,153. All delay,
> punctuality, segment and cost results are unchanged.

---

### 13. `delta_delay` lets early running masquerade as recovery

The segment measure `delta_delay = delay(i+1) − delay(i)` treats an early departure as
negative delay, so an early vehicle running *further* ahead of schedule is scored the same
way as a late vehicle catching up. Both come out negative.

This is not a corner case. Over the collection period:

| | |
|---|---|
| Segment observations starting early | ~20 % |
| Mean `delta_delay` when the segment starts early | **≈ +10 s** |
| Mean `delta_delay` when it does not | ≈ −1 s |
| Negative deltas that are vehicles running further ahead | **~50 %** |

The network mean of about +1 s is therefore driven almost entirely by early vehicles
returning to schedule — not by delay being generated and absorbed.

Since 9 August 2026 `segmente_aus_fahrten()` also returns

```
delta_verspaetung = max(delay(i+1), 0) − max(delay(i), 0)
```

which clips at the timetable, so an early departure contributes 0 and can never offset a
late one. Worked examples are in the header of `src/analysis/segmente.py`.

| before | after | `delta_delay` | `delta_verspaetung` | |
|---|---|---|---|---|
| +120 s | +180 s | +60 s | +60 s | falls further behind |
| +180 s | +120 s | −60 s | −60 s | catches up |
| −60 s | −120 s | −60 s | **0 s** | runs further ahead |
| −120 s | −60 s | +60 s | **0 s** | returns toward schedule |

Early running is not discarded, only measured elsewhere — as the share of early departures
per stop (notebook 03, section 2). A *level* and a *change* are two quantities; forcing
them into one number was the defect.

> Which one is in use: `zufluss_je_haltestelle(..., spalte=…)` defaults to `delta_delay`,
> so notebooks 04, 05, 06 and the cached `segmente_tram_gesamt.parquet` are unaffected.
> Notebook 03 asks for `delta_verspaetung` explicitly. The active choice is recorded in
> `agg.attrs["quelle"]`.

---

### 14. The punctuality window, and how it maps onto the official one

Analyses in this project use **]−120 s, +240 s[** — a departure counts as outside the
window at `delay_s ≤ −120` or `delay_s ≥ +240`. Both bounds are the contract's own,
translated onto the minute grid; neither is a judgement call of this project.

Under the BVG transport contract, since **1 January 2025** a trip counts as punctual if it
departs **between 60 s before and 210 s after** the published time; the early tolerance was
tightened from 90 s to 60 s on that date, which is why figures from 2025 onward are not
comparable with older published ones. *Verfrühungsvermeidung* is a **separate, fourth metric**
with its own target (tram 99.00 %, U-Bahn 99.90 %): the share of trips **not** departing more
than 60 s early.

> Note the distinction, which earlier drafts of this file blurred: the contract does **not**
> state that an early departure is booked as a cancelled trip. "Cancelled" belongs to
> *Zuverlässigkeit* (trips operated out of trips ordered). That an early departure *behaves*
> like a cancellation for a passenger who arrives on time is an interpretation this project
> makes — well founded, but it must be presented as an argument, not as a quotation from the
> contract. Source of record: `data/bvg/definition.md`.

Because `delay_s` is minute-quantised (characteristic 1), "more than 60 s early" has exactly
one representation in this data:

```
more than 60 s early  →  delay_s < −60  →  delay_s ≤ −120
```

| Side | This project | Contract | Relationship |
|---|---|---|---|
| early | `≤ −120` | more than 60 s early | **identical** |
| late | `≥ +240` | more than 210 s late | **identical under rounding** |

**Why `≥ +240` and not `≥ +180`** (changed 10 Aug 2026). The contract boundary of 210 s falls
between two grid steps, so which step is faithful depends on the API's rounding convention:

| | step `180` represents | step `240` represents | verdict |
|---|---|---|---|
| API **rounds** | true 150–210 s → all **punctual** | true 210–270 s → all **late** | `240` is exact; `180` is plainly wrong |
| API **truncates** | true 180–240 s → mixed | true 240–299 s → under-counts | `240` under-counts, `180` over-counts |

`≥ +240` is therefore either exact or conservative — it can never overstate the gap between
the networks. `≥ +180` would repeat, mirrored, the error that `≤ −60` made on the early side:
counting departures that lie *inside* the window. Applying the same rule to both sides is what
makes the window defensible as a whole.

Effect of the late-side change:

| | `≥ +180` | `≥ +240` |
|---|---|---|
| Tram late | 10.77 % | 6.23 % |
| U-Bahn late | 4.02 % | 2.11 % |
| ratio | 2.68× | **2.95×** |
| **punctuality rate, tram** | 78.84 % | **83.38 %** (contract target 92.30 %) |
| **punctuality rate, U-Bahn** | 95.00 % | **96.90 %** (contract target 98.70 %) |

The contract targets come from `data/bvg/` (export of the Senate's quality monitor). Both
own rates sit below the official published ones because of the counting unit — see
characteristic 15.

Measured over the standard analysis window, `delay_s` present, collector outage excluded:
n = 9,784,009 (tram) and 5,458,881 (U-Bahn).

**Why not `≤ −60`** (used until 10 Aug 2026): it is *stricter* than the contract — it counts
the −60 s grid value, which the contract still treats as punctual — and it is
rounding-sensitive. −60 s is the single most frequent early value:

| Early value | Tram departures | share of all early tram departures |
|---|---|---|
| exactly −60 s | 996,782 | **45.8 %** |
| exactly −120 s | 1,000,921 | 46.0 % |
| −180 s or earlier | 165,330 | 8.2 % |

For the U-Bahn **83.3 %** of early departures sit on −60 s exactly. And the sub-minute truth
behind that bucket is unrecoverable: across all 13.2 M documents, `when` and `planned_when`
carry **exactly one distinct seconds value, `0`**, and `delay_s` equals their difference with
zero deviation in all 11.3 M cases. A recorded −60 s can therefore mean anything from a few
seconds to nearly two minutes early. `≤ −120` is the smallest threshold at which "more than a
minute early" holds under any rounding convention.

Effect of the change:

| | `≤ −60` | `≤ −120` |
|---|---|---|
| Tram early | 19.3 % | 10.4 % |
| U-Bahn early | 6.1 % | 1.0 % |
| ratio | 3.1× | **10.2×** |

The gap between the networks *widens*. Whether the U-Bahn's concentration on a single bucket
is genuine dispatch behaviour or an artefact of its feed cannot be decided from these data.

**Per-stop figures under the full contract window** (`≤ −120` and `≥ +240`, stops with at
least 1,000 departures):

| | Tram (n = 396) | U-Bahn (n = 169) |
|---|---|---|
| median share outside the window | 15.6 % | 2.5 % |
| range | 0.4 – 31.5 % | 0.0 – 8.4 % |
| stops predominantly **early** rather than late | **307 of 396** | 31 of 169 |

That last row is the sharpest single statement in the dataset: at roughly **four out of five
tram stops the dominant failure is departing too early**, not too late — the opposite of what
the public debate assumes.

> Maps are produced by `scripts/karten_puenktlichkeit.py`, which writes the tram, U-Bahn and
> combined variants. Labels are written in whole minutes, never seconds: a seconds figure
> claims a resolution the data does not have.

---

### 15. External validation against the Senate's quality monitor

`data/bvg/` holds monthly figures for all four contractual metrics (Jan 2025 – Jun 2026) plus
their definitions. They are measured from BVG's own operating system, not from the public
departure API — an entirely independent instrument on the same networks in the same months.
`scripts/validierung_bvg.py` reproduces the comparison.

**Contractual annual targets** (these supersede the 91 % / 97 % figures quoted in earlier
drafts of this file, which were wrong):

| Metric | U-Bahn | Tram | Bus |
|---|---|---|---|
| Pünktlichkeit | 98.70 % | **92.30 %** | 88.99 % (2025) / 89.40 % (2026) |
| Verfrühungsvermeidung | 99.90 % | 99.00 % | 98.00 % |
| Zuverlässigkeit | 99.70 % | 99.70 % | 99.80 % |
| Regelmäßigkeit | 98.73 % (2025) / 98.90 % (2026) | 96.70 % | 94.40 % |

**Comparison for the three overlapping months.** Own figures use the contract window
(`≤ −120` / `≥ +240`); "amtlich" is the published monthly value.

| Month | Metric | own, U-Bahn | official | own, Tram | official |
|---|---|---|---|---|---|
| Mai 26 | Pünktlichkeit | 97.35 % | 98.01 % | 84.44 % | 86.89 % |
| Mai 26 | Verfrühungsvermeidung | 99.09 % | 99.78 % | 89.93 % | 97.14 % |
| Mai 26 | Zuverlässigkeit | 98.94 % | 98.37 % | 99.60 % | 99.07 % |

**The levels do not match, and they are not supposed to.** The monitor counts **per trip**,
this dataset counts **per departure event at a stop**. A trip with thirty stops has thirty
chances to fall outside the window, so own punctuality is systematically *lower*; conversely a
cancelled trip vanishes from the feed rather than being counted, so own reliability is
systematically *higher*. Both deviations are stable across months — punctuality −0.7 to
−1.6 pp (U-Bahn) and −2.4 to −3.3 pp (tram), reliability +0.2 to +1.4 pp.

**What does match is what the analysis actually claims — the distance between the networks:**

| Metric | own gap (Tram − U-Bahn) | official gap | difference |
|---|---|---|---|
| Pünktlichkeit, Apr/Mai/Jun 26 | −12.1 / −12.9 / −14.5 pp | −11.0 / −11.1 / −12.8 pp | ≤ 1.8 pp |
| Zuverlässigkeit, Apr/Mai/Jun 26 | +1.26 / +0.66 / +0.54 pp | +0.86 / +0.70 / +0.88 pp | ≤ 0.4 pp |

The reliability row is the strongest single validation in the project, because it reproduces a
**counter-intuitive** result: in these months the tram is *more* reliable than the U-Bahn — it
cancels fewer trips. Both instruments agree on the direction and, in May, on the size to within
0.04 pp. A pipeline that merely flattered the hypothesis would not do that.

**Verfrühung is the exception and must be quoted as a ratio, never in percentage points.** In
points the two sources diverge by a factor of three (own gap ≈ −9 pp, official ≈ −2.8 pp).
As a ratio they agree, and the own measurement is the *conservative* one in every month:

| Month | own ratio Tram : U-Bahn | official ratio |
|---|---|---|
| Apr 26 | 8.8× | 11.8× |
| Mai 26 | 11.0× | 13.0× |
| Jun 26 | 10.9× | 15.7× |

**Regelmäßigkeit is not reproduced.** Its definition needs the line's headway per trip
(`60 s – max. 10 min`); `src/analysis/takt.py` computes the effective headway per line, but the
trip-to-headway assignment does not exist yet. It is the one contractual metric still open.

---

## Sensitivity

No personal or sensitive data. All collected information is public transit schedule and
operational data. No user identifiers are present.
