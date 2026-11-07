# CASR v2 Vehicle History Playback Handover

Reviewed against main `44680c0` during 6–7 November 2026, including PRs 72–76.

## Cause and change

`backend/services/vehicle_history.py::query_vehicle_history` previously returned
`None` before querying observations whenever the physical `routes` table had no
matching row. The API mapped this to 404. Both a disposable synthetic database
and the verified original Box backup reproduced this false missing-route result.
The Box backup has empty routes, stops, trips and stop_times tables.

The new `_known_route` checks, in order:

1. The selected database's physical routes table.
2. A route ID present in that database's Vehicle Positions, using an indexed
   `SELECT 1 ... WHERE route_id = ? LIMIT 1` existence lookup, outside the window.
3. Route membership in the configured, hash-verified Static map catalog.

These sources establish identity only. The observation query still reads only
Vehicle Positions from the selected database; it does not join dimensions,
geometry or schedules. No further dimension dependency exists in this request
path. Historical-only routes outside the published 384 routes remain valid.

Recorded map metadata was considered but is not an additional identity source:
recorded playback already has database routes/history, and a separately installed
map artifact alone should not establish historical coverage in another database.
No recorded/static map source-selection logic changed. Feed 1710 metadata never
replaces September feed 1692 geometry or schedules. Catalog membership does not
assert historical coverage or schedule compatibility for any date.

## API contract

`GET /api/routes/<route_id>/vehicle-positions`

Required `start_time` and `end_time` are timezone-aware ISO timestamps, compared
as actual instants using SQLite julianday. The window remains **[start, end)**.
Optional `limit` defaults to 500 (1–1000), `offset` defaults to 0. Pagination and
JSON are unchanged: route_id, start_time, end_exclusive, limit, offset,
next_offset, positions. Each position retains its existing latitude, longitude,
vehicle_id, trip_id, route_id, timestamp and database id fields.

- Known route with records: 200, ordered by timestamp then id.
- Known route with no records in the window: 200, positions `[]`, next_offset null.
- Unknown route: 404, `{"error":"Route not found"}`.
- Invalid bounds, pagination or unsupported parameters: 400, error message.
- Configured catalog missing/corrupt when needed for identity: existing 503
  MapDataUnavailableError response. Established database identity still works.
- Unconfigured catalog: database identity remains sufficient; otherwise 404.

Example using curl (which URL-encodes the positive offset safely):

```sh
curl -G http://127.0.0.1:5000/api/routes/100/vehicle-positions \
  --data-urlencode 'start_time=2026-10-17T09:00:00+10:30' \
  --data-urlencode 'end_time=2026-10-17T09:15:00+10:30' \
  --data-urlencode 'limit=1000'
```

Equivalent UTC bounds are 2026-10-16T22:30:00Z and 22:45:00Z. Performance and
Hotspot endpoints continue to use inclusive bounds; this change does not alter them.

## Configuration and safety

Set `ADELAIDE_METRO_DATABASE_PATH` before starting the application to a disposable
verified working copy of the intended historical database. This environment
variable alone does **not** enable read-only SQLite: the existing default factory
opens writable connections. Never point the ordinary app at the original Box file.
For original-file checks, use an explicit connection factory with
`sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)`, sqlite3.Row,
and `PRAGMA query_only=ON`, injected into `backend.services.vehicle_history`.
Immutable mode is suitable only for the closed, fixed backup, not a live collector.
The verification script also bounds SQLite execution with a progress handler.

Set `ADELAIDE_METRO_STATIC_MAP_DATA_PATH` to the published network directory
containing manifest.json and catalog.json, following
[the publisher instructions](citywide-static-map-data.md). This is optional for
routes already present in history, but required for citywide map/catalog access.
`ADELAIDE_METRO_DEMO_MAP_DATA_PATH` remains the September recorded artifact path.
Keep the original September database and artifacts separate. For October geometry
request `source=static`; use recorded source for the September demo. Vehicle
History itself accepts no source parameter: its database determines observations.

## Verification

Final full regression: **411 passed in 51.63 seconds**, zero failures or skips,
including 14 new compatibility tests. Command: `python -m pytest backend/tests tests
-q -p no:cacheprovider` with a dedicated writable TEMP/TMP directory and pytest
basetemp. The first full run had 376 passes and 35 temporary-directory permission
failures; rerunning with the corrected test environment passed all 411 tests.
Focused history/integration run: 28 passed. `git diff --check` passed.

New synthetic tests exercise empty dimensions, static identity, missing/corrupt
configuration, empty/future windows, unknown routes, route isolation, pagination,
September and October offsets, UTC equivalence, end exclusion, output fields,
invalid requests and read-only file hashes. Existing integration tests cover
populated dimensions and the HTTP-to-persistence-to-history path.

Read-only real-data checks on 6 November 2026:

| Database / interval (Adelaide) | Route | Records | API time |
| --- | --- | ---: | ---: |
| Original Box, Oct 17 09:00–09:15 +10:30 | 100 | 21 | 91 ms |
| Original Box, Oct 17 09:00–09:15 +10:30 | J1 | 53 | 86 ms |
| Original demo, Sep 26 09:00–09:15 +09:30 | G10 | 91 | 21 ms |
| Original demo, Sep 26 09:00–09:15 +09:30 | M44 | 98 | 2 ms |
| Original demo, Sep 26 09:00–09:15 +09:30 | 506 | 25 | 1 ms |

Single local measurements, not production performance guarantees. October rows
passed route, instant-range and ordering assertions; future windows returned
empty success. The real identity query uses the existing covering
idx_vehicle_positions_route index. No schema or persistent index changes were made.
The existing page query still filters/sorts timestamps within a route; very long
windows or large offsets are not newly optimized or claimed to have fixed latency.

Before/after SHA-256 values were identical:

- Original Box: `cc3f10973026fa4357f8ac50923187c0b554f6ba69caee3798b83bc376282bcd`.
- September demo: `735de9404b6fe46d52fe0b102004e6993815157b8f5905341afbf9cada465aa2`.

Private evidence is outside Git in `vehicle-playback-evidence-20261106` alongside
this isolated checkout: smoke.py, real-data.json, september.py,
september-and-reproduction.json and regression XML reports. No static or recorded
artifacts were written. The earlier malformed OneDrive backup was not accessed.

## Frontend handover and remaining limits

Chenchen and Pritish can test the unchanged endpoint and pagination contract.
The current frontend reads positions/next_offset, then latitude/longitude,
vehicle_id and timestamp; these fields are unchanged. Zero positions is valid
and must not be presented as a missing route. Non-2xx responses currently become
a generic history-loading status in the UI.

**Separate blocker:** `frontend/js/map.js::getPlaybackDate` still appends fixed
`+09:30`. October Adelaide dates require `+10:30`; the current frontend therefore
sends an instant one hour later than intended. The frontend owner must use
Australia/Adelaide date-aware conversion and test both seasonal offsets. No
frontend files were changed here. The backend 404 fix cannot correct a wrong
instant already encoded in a UTC request.

No browser Play/Pause test was performed for this branch. Backend and September
API success does not establish browser E2E success, production uptime or complete
network history coverage. Realtime stop_sequence compatibility remains unresolved;
no matching rules changed. CASR v2.1 remains **ON HOLD**. No deployment or merge.
