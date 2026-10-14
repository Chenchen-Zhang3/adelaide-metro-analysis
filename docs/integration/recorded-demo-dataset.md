# Recorded real-data demo dataset

SCRUM-233 / S4-C03. Prepared on 2026-10-14 from main `a920c6c`, after C01
was merged. This is a standalone recorded-data artifact, not a live collector.

**Recorded Historical Data — September 2026**

## Source and selection

Historical source is the unchanged legacy CASR snapshot
`CASR historical data/original/adelaide_metro_history_20260928_165052.db`.
It is opened using `mode=ro&immutable=1` and `query_only=ON`. No migration,
source write, original index change or full database copy is performed.

Static files come from the existing archived `GTFS/google_transit.zip` and its
verified extracted directory. Feed version **1692** covers 2026-08-20 through
2026-10-11. Its SHA-256 is pinned in `recorded-demo-config.json`; every required
static file is checked against the archive before generation. No newer feed
is downloaded or mixed in. See C01's ID audit for full source provenance.

Recorded observation window is **[2026-09-26 09:00:00, 11:00:00)** Adelaide
time, UTC+09:30. End is exclusive. Scheduled arrivals may precede or follow
that window: it is the observation timestamp that selects a historical record.

| Route | Name | Vehicle rows | Source updates | Stored v2 updates | Trips present in both feeds |
| --- | --- | ---: | ---: | ---: | ---: |
| G10 | Marion Centre Interchange to Blair Athol | 741 | 21,361 | 10,743 | 19 |
| M44 | Marion Centre Interchange to Golden Grove Interchange | 793 | 16,246 | 7,319 | 19 |
| 506 | Tea Tree Plaza Interchange to City | 258 | 10,676 | 4,194 | 10 |

All five C01 candidate routes were profiled in this actual window. H30 was
usable but offered fewer overlapping trips; 506 adds different coverage and
late-running examples. Route 300 included a -9,660-second outlier and was not
selected for this compact demonstration. No selected observations were edited
to improve their appearance. There are 48 shared trips across the selected
routes and 55 distinct trips overall; the extra seven have predictions but no
vehicle observation in this window. Full selected trip/stop IDs are in the
manifest rather than implied to be simultaneous observations.

## Final artifact

Directory relative to the capstone project folder:
`CASR historical data/analysis/demo_dataset/`.

- `adelaide_metro_demo.db`: **3,858,432 bytes (3.68 MiB)**.
- `adelaide_metro_demo.manifest.json`: source hashes, config, table counts,
  all selected trip/stop IDs, route overlap, shape IDs and API samples.
- Database SHA-256:
  `735de9404b6fe46d52fe0b102004e6993815157b8f5905341afbf9cada465aa2`.

| Table | Rows |
| --- | ---: |
| routes | 3 |
| trips | 55 |
| stops | 354 |
| stop_times | 3,249 |
| vehicle_positions | 1,792 |
| trip_updates | 22,256 |
| trip_update_current_state | 2,313 |
| collection_cycles | 1,242 |

This is the existing physical **v2** schema, with full supporting state tables.
`create_tables`, static parsers/converters and repository insertion helpers are
reused. Selected source observations are merged chronologically and passed
through `persist_realtime_collection(..., checkpoint_seconds=900)`.
Of 48,283 original updates, 26,027 unchanged observations are suppressed by
the existing v2 policy; timestamps, IDs, coordinates and delay values are not
rewritten. Initial state is relative to the selected window, not the whole
three-day history. Static stop times cover the full selected trips.

The legacy source has no cycle ledger. The 1,242 generated ledger rows are
actual successful **demo import transactions**, grouped by original observation
timestamp; they are not invented CASR poll-success telemetry. Both manifest
and `schema_metadata.ledger_provenance` explicitly say so. Do not use this
subset ledger to measure original collector uptime. `schema_metadata` also
contains the recorded-data label; no new physical table design was introduced.

## Regenerate safely

Run from the repository root using Python 3.12 and existing backend dependencies:

```powershell
python -m pip install -r requirements.txt
python -m backend.services.recorded_demo --source "PATH\original\adelaide_metro_history_20260928_165052.db" --static-dir "PATH\GTFS\google_transit" --static-archive "PATH\GTFS\google_transit.zip" --config docs/integration/recorded-demo-config.json --output "PATH\analysis\demo_dataset\adelaide_metro_demo.db"
```

Use a new output filename/directory when one already exists. The builder refuses
to overwrite a source, output database or existing manifest. It builds in a
temporary directory, validates using existing services, then publishes the DB
and manifest. It restores the original database-path setting on exit or failure.
Run it in a separate offline process, not inside a running Flask server.

The same real inputs were generated twice into separate destinations; both
database hashes match exactly. Binary reproducibility is demonstrated on this
SQLite/Python environment; another SQLite version may lay out equivalent rows
differently. Generation is repeatable without live API or CASR host access.
After generation, teammates only need the small demo DB, manifest and repository,
not the original 6 GB source. Share DB + manifest through the team's file share;
no binary database or source feed is committed to Git or automatically uploaded.

## Run the existing backend against the demo

In a fresh PowerShell terminal from the repository root, set the absolute local
path before importing backend modules:

```powershell
$demoPath = 'C:\team-demo\adelaide_metro_demo.db'
if (-not (Test-Path -LiteralPath $demoPath)) { throw 'Copy the demo DB here first' }
$env:ADELAIDE_METRO_DATABASE_PATH = $demoPath
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5000
```

Do not run the live collector against this demo database. In a second terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/routes
Invoke-RestMethod http://127.0.0.1:5000/api/stops
Invoke-RestMethod http://127.0.0.1:5000/api/routes/G10/performance
Invoke-RestMethod http://127.0.0.1:5000/api/stops/100618/routes
Invoke-RestMethod http://127.0.0.1:5000/api/stops/100618/performance
```

The existing frontend uses this host/port. It can be served from the repository
with `python -m http.server 8000`, then opened at
`http://127.0.0.1:8000/frontend/`. Actual browser consumption/playback was not
tested or implemented in this task. Leaflet CDN and OpenStreetMap tiles still
require internet or separate caching; offline GTFS data is not a guarantee of
an offline basemap. Allow only the intended one demo server on port 5000.

## Query/data contract

Repository functions used successfully: `get_all_routes`, `get_all_stops`,
`get_routes_by_stop`, `get_vehicle_positions_filtered`,
`get_trip_updates_filtered`, `get_trip_updates_by_stop`; analysis uses
`query_and_analyse`. Route/stop endpoints were exercised with the actual Flask
test client, not endpoint mocks. The published DB was independently retested
with HTTP fetching blocked; all requests returned 200 without GTFS traffic.

Example Python, after setting the database environment variable:

```python
from backend.database.repository import get_vehicle_positions_filtered, get_trip_updates_filtered
vehicles = get_vehicle_positions_filtered(route_id="G10", start_time="2026-09-26T09:00:00+09:30", end_time="2026-09-26T11:00:00+09:30")
updates = get_trip_updates_filtered(route_id="G10", stop_id="100618", start_time="2026-09-26T09:00:00+09:30", end_time="2026-09-26T11:00:00+09:30")
```

IDs remain strings. Vehicle coordinates are latitude/longitude numbers and
vehicle timestamps remain original ISO strings. Trip Update timestamps and
scheduled arrivals are INTEGER epoch inside SQLite, converted to Adelaide ISO
at the repository boundary; actual arrival is derived. Example returned record:

```json
{"trip_id":"1135909","route_id":"G10","stop_id":"100618","scheduled_arrival":"2026-09-26T09:03:26+09:30","actual_arrival":"2026-09-26T09:05:24+09:30","delay_seconds":118,"timestamp":"2026-09-26T09:01:05+09:30","observation_kind":"initial"}
```

Static route/trip stops can be inspected read-only:

```sql
SELECT t.route_id, t.trip_id, st.stop_sequence, s.stop_id, s.stop_name
FROM trips t JOIN stop_times st ON t.trip_id=st.trip_id
JOIN stops s ON s.stop_id=st.stop_id
WHERE t.route_id='G10' ORDER BY t.trip_id,st.stop_sequence;
```

Current HTTP APIs do not expose raw vehicle playback or time-range selection.
SCRUM-234 must decide that interface using the existing repository functions,
add the recorded-data banner and replay controls, and verify browser behaviour.
Do not invent an existing `/api/vehicles` or `/api/history` endpoint. Existing
performance `total_services` counts retained prediction observations, not
unique trips/completed services; state-change/checkpoint sampling affects these
aggregates and they should not be presented as an unbiased service census.

## Geometry handover to SCRUM-232

Official shapes are available but current schema/API has no shape interface.
No shape table, polyline API or invented vehicle trajectory is added here.
Manifest preserves shape IDs from the selected static trips:

- G10: `16638`, `16782`, `16783`.
- M44: `15144`, `15145`, `15150`.
- 506: `3240`, `3246`.

SCRUM-232 needs version-1692 `trips.txt` and `shapes.txt` for its geometry work.
The database alone does not contain route polylines. Observed vehicle coordinates
are suitable as recorded positions, not a road-aligned continuous trajectory.

## Validation and presentation readiness

All selected IDs, trip/route mappings, trip/stop pairs and static references
validate. Every coordinate is finite and in legal latitude/longitude ranges;
no selected vehicle coordinate triggered the broad Adelaide-area warning.
Source and reconstructed actual arrival equal schedule + signed delay.
Delay range is **-333 to +916 seconds** in both source and retained history.
Observation timestamps are preserved at UTC+09:30, distinct from arrival times.
All timestamps are inside the configured observation window.

Independent checks find zero trip/stop orphans, vehicle/trip orphans and route
conflicts; SQLite integrity is `ok`. API route/stop/performance and repository
time-range queries all work. Focused extraction tests cover reproducibility,
schema/state/ledger compatibility, exact IDs, excluded end boundary, invalid
data, absent inputs, version/hash mismatch, path restoration and no overwrite.

Final related regression suite: **89 passed**, including **14 new extraction
tests**; no failures or skips. Existing v2 storage, repository, API, pipeline,
parser/converter and analysis integration tests are included. The unrelated
C05 long-running suite was not repeated. Reproduce with
`python -m pytest backend/tests/test_recorded_demo.py -q` in the test environment.

The dataset is ready for SCRUM-233 review and recorded-data demonstrations on
19 October. The static feed is expired by that date, so never describe these
September observations as live October information. Browser playback, geometry,
basemap/CDN availability, and the visible recorded-data label remain integration
checks for SCRUM-232/234 and the presenting team. No Jira transition, automatic
merge, production deployment or next-task implementation was performed.
