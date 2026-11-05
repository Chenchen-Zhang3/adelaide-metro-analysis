# Network-wide stop prediction delays: Pritish handover

Local implementation on `feature/S5-network-wide-stop-delay-api`, based on main
`29319ef01489af3b0d73c274027ebf963de50c87` (PR #72/#73 integrated).
Ready for frontend integration testing; deployment and release remain pending.
CASR v2.1 remains **ON HOLD**.

From the updated backend checkout, configure an approved v2 historical demo or
research copy using `ADELAIDE_METRO_DATABASE_PATH`. For static scope, also set
`ADELAIDE_METRO_STATIC_MAP_DATA_PATH` to the complete 1710 publication directory
(manifest, catalog, calendars and route files), then start the existing API:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = 'PATH\approved-v2-research-copy.db'
$env:ADELAIDE_METRO_STATIC_MAP_DATA_PATH = 'PATH\network'
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5000
```

Replace PATH with actual local paths. The environment variable selects the DB;
it does not itself enforce read-only access. The production-backed validation
used a separate connection factory with `mode=ro&immutable=1` and query_only.
Never point the standard development server at the original Box backup.

## Call one bulk endpoint

`GET /api/analysis/stop-delays`

```text
http://127.0.0.1:5000/api/analysis/stop-delays?start_time=2026-10-17T09%3A00%3A00%2B10%3A30&end_time=2026-10-17T09%3A15%3A00%2B10%3A30&scope=static&min_samples=10
```

| Parameter | Contract |
|---|---|
| `start_time`, `end_time` | Both required, ISO 8601 with explicit UTC offset or Z. Inclusive observation-time interval `[start,end]`, maximum 3,600 elapsed seconds; equal endpoints allowed. |
| `route_id` | Optional exact string, nonempty, at most 128 characters. Applied before visit deduplication. |
| `min_samples` | Integer 1–100000; default 10, a provisional display threshold, not statistical confidence. |
| `scope` | `observed` (default) or `static`. Explained below. |

Unknown/repeated query parameters are rejected, including misspelled time filters.
Encode `+` as `%2B` or use URLSearchParams. October Adelaide is +10:30;
September is +09:30. Both are compared as UTC instants; response timestamps are UTC.
Do not reuse the frontend's fixed +09:30 conversion for October.
Performance/Hotspot use inclusive bounds; Vehicle History excludes the end.

## Scope and joining the map

Use `/api/stops` for coordinates and names; join results by exact **string**
`stop_id`. Do not make one performance request per marker.

- `scope=observed`: returns observed stop IDs from the requested historical DB
  window/route, without any static feed compatibility claim. Unknown routes
  simply produce an empty result. Suitable for the September recorded context.
- `scope=static`: requires the complete static publication configured with
  `ADELAIDE_METRO_STATIC_MAP_DATA_PATH`; validates Adelaide dates against its
  feed validity and keeps only exact location_type=0 stop/platform IDs. Parent
  stations are excluded and never receive summed child predictions. With
  route_id, eligible catalog stops must list that route and the route must exist.
- **Static scope filters stop membership, not all historical route IDs.** Without
  route_id it includes all historical routes observed at those stops, including
  services outside the publisher's selected 384 routes. This is stated in
  `historical_route_scope`; do not label it a 384-route-only delay aggregate.
- An absent eligible stop means `no_data`, zero samples and null metrics for
  this window/filter. Stops outside the eligible catalog/route are **excluded**,
  not no_data. Observed IDs excluded by static matching are listed separately.
  The eligible stop denominator counts catalog stops, not expected services;
  there is no completeness percentage.

1710 is valid 16 October 2026–9 April 2027. Static scope rejects 12–15 October;
do not substitute 1692. Date and ID compatibility do not prove service-calendar,
trip, stop_sequence or complete historical coverage. The research copy has only
100/J1 database dimensions; this endpoint reads historical rows plus the external
catalog and does not depend on those incomplete dimension tables.

## Metric definitions

Filter observations first, then retain the latest prediction for each
`(trip_id, stop_id, scheduled_arrival)` visit, matching the existing analysis
identity. Latest means greatest epoch `observed_at`, then greatest row `id` for
equal times. Revisions outside the window cannot replace a selected prediction.
Null observation times are excluded. Repeated visits with different scheduled
arrival instants remain separate. route_id is not part of the existing identity.

Average is the arithmetic mean of selected `delay_seconds / 60`, rounded to two
decimal places, including negative early values. On-time percentage calls the
existing `classify_punctuality`: Early <0; On Time 0–5 inclusive; Delayed >5–10
inclusive; Severely Delayed >10 minutes. The percentage is On Time samples / all
selected visit samples ×100, rounded to two decimals. No new colour thresholds
or actual-arrival rules are introduced.

Counts are **prediction visit samples**, not completed services or raw retained
rows. Stored changes/checkpoints provide neither every feed snapshot nor every
service. Below min_samples, both metrics are null but count/time bounds remain.

The old Python preparation path compares formatted timestamps and does not define
a stable ID tie-break. This endpoint explicitly orders actual instants and IDs,
including an autumn DST fold. Standard-window single-stop parity is tested;
ambiguous equal-time revisions/DST-fold ordering have this explicit distinction.
No existing endpoint or matching rule was changed.

## Response field reference

| Fields | Meaning |
|---|---|
| `data_source` | `historical_trip_update_predictions` |
| `start_time`, `end_time`, `interval` | Requested bounds normalised to UTC; `inclusive`. |
| `route_id`, `scope`, `historical_route_scope` | Applied filters and explicit route membership semantics. |
| `aggregation_unit`, `visit_identity`, `tie_break` | Latest-per-visit methodology and deterministic ordering. |
| `min_samples`, `on_time_delay_minutes` | Visible threshold and existing inclusive 0–5 on-time rule. |
| `missing_stop_policy`, `limitations` | Absence and prediction-only interpretation. |
| `static_catalog` | Null for observed scope; otherwise version, valid_from/to, eligible_stop_count and parent_station_rollup=false. |
| `excluded_observed_stop_ids` | Sorted exact observed IDs excluded from static eligibility; empty for observed scope. |
| `coverage.returned_stop_count` | Number of returned observed eligible stops, including insufficient_data. |
| `coverage.prediction_sample_count` | Sum of selected visit samples for returned stops. |
| `coverage.window_retained_row_count_before_route_filter` | Time-slice rows counted for the safety guard; includes other routes/stops. |
| `coverage.no_data_stop_count` | Eligible static stops minus returned stops; null when there is no defined static denominator. |
| `stops[].stop_id` | Exact string ID; no coordinates duplicated. |
| `stops[].average_predicted_delay_minutes` | Signed average, or null below threshold. |
| `stops[].predicted_on_time_percentage` | Prediction-based percentage, or null below threshold. |
| `stops[].prediction_sample_count` | Selected visit count. |
| `stops[].data_status` | `available` or `insufficient_data`; no_data is represented by absence as above. |
| `stops[].first_selected_observation_time`, `last_selected_observation_time` | UTC extrema after deduplication; not service times, raw-row coverage or collection uptime. |

Measured synthetic example entry (`min_samples=1`, two selected delays 0 and 1
minute, **not production data**):

```json
{
  "stop_id": "00000",
  "average_predicted_delay_minutes": 0.5,
  "predicted_on_time_percentage": 100.0,
  "prediction_sample_count": 2,
  "data_status": "available",
  "first_selected_observation_time": "2026-10-16T22:31:00+00:00",
  "last_selected_observation_time": "2026-10-16T22:31:00+00:00"
}
```

## Limits and errors

The v2 observed_at index bounds two SQL queries in one read transaction: an
index-only row guard, then window-function deduplication and grouped aggregates.
Only grouped rows reach Python; no N+1 queries or millions of raw rows are loaded.
At most 100,000 retained time-slice rows are allowed, even with a sparse route
filter. A SQLite progress handler imposes an approximately five-second SQL
execution budget (not an HTTP SLA); aggregation never returns a partial result.
No new indexes or migrations are required. Missing schema/index errors retain the
existing generic database-error response; configure the application's v2 DB.

| Status | Handling |
|---|---|
| 200 | Results or empty stops list. Do not convert emptiness to zero delay. |
| 400 | Invalid/missing/repeated parameter, reversed/>1-hour range, invalid static date/route. Read `error`. |
| 422 | `code=analysis_limit_exceeded`: row cap/deadline. Narrow the time window; do not automatically retry an unbounded request. |
| 503 | Static catalog/manifest unavailable or inconsistent. Fix configuration; do not label it no_data. |
| 500 | Existing generic database error, e.g. wrong DB schema. Do not display it as no_data. |

## Frontend work

Keep static stops visible. Use separate unavailable/insufficient marker styles;
colour only available metrics. Choose one legend metric, e.g. **Average predicted
delay (minutes)** or **Predicted on-time percentage**. Label any chosen colour
bins as display choices, not scientifically validated thresholds. Include source,
requested window, threshold and prediction sample count in legend/popups.

Fetch once per selected window/route; debounce filters, cancel or discard stale
responses, and show loading/error states. Never retain an old window's colours
under a new label. Keep static map access independent of statistics availability.
Frontend owns markers, popups, legend, controls, rendering and E2E testing.

## Local evidence (5 November 2026)

Final-review regression: 202 tests passed in 28.43 s, zero failures/skips, including 41 new
bulk tests. Relevant API, repository, analysis, Hotspot, static publication and
integration tests were run. No application frontend edits or production writes.

Saved implementation-stage single-run local measurements, not rerun during final
review; no concurrency/browser/network claim:

| Dataset | Retained rows | Returned stops | Samples | SQL ms | API ms | Bytes |
|---|---:|---:|---:|---:|---:|---:|
| Small synthetic | 12 | 3 | 6 | 1.24 | 18.83 | 1,848 |
| Large synthetic | 56,000 | 7,000 | 28,000 | 89.89 | 118.34 | 1,905,042 |
| Read-only October research copy, static scope | 32,267 | 4,432 | 7,117 | 46.34 | 101.22 | 1,205,497 |

Timing rows use min_samples=1. The real window was 17 October 09:00–09:15
+10:30. There were 178 excluded observed IDs. At the default min_samples=10,
only **11** stops were available, **4,421** insufficient, and **2,808** eligible
stops had no data. Do not lower the threshold merely to make the map look full.
Payloads around 1–2 MB still need frontend/laptop testing.

Research-copy SHA-256 before/after was
`a6c812418ad6db1ffcc33c2cd414117e83430597f6e95d48d9a31f3f113240dd`;
size/mtime unchanged. The original Box and malformed OneDrive backups were not
opened. Empty static dimensions, sparse predictions and unresolved upstream
stop_sequence semantics do not justify stronger coverage claims. For 9 November,
retain the separate September recorded playback fallback and labelled October
API/research evidence. No CASR release is authorised.
