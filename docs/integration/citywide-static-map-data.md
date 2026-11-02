# SCRUM-282 backend: selected static bus network map data

Prepared 2 November 2026 on `feature/SCRUM-282-citywide-static-map-backend`,
from main `a98a74e` (Performance API PR #72 is already merged).
Backend implementation and local data validation are ready for review.
This does not mark the full Frontend Jira task Done. CASR v2.1 remains **ON HOLD**.

## Integration gap and scope

The recorded publisher deliberately validates the September three-route demo
manifest, database fingerprint and feed 1692. Its map reader only serves routes
in that publication. Route/stop list APIs previously read only the configured
historical database dimensions. A complete feed on disk did not publish geometry
or populate those lists automatically.

`backend.services.static_map_data` now publishes a separate, explicitly selected
static network. It reuses the existing route/stop/trip parsers, streaming
`extract_shapes`, coordinate checks, GeoJSON helper and fingerprints. It never
opens a database. Existing recorded publisher and artifacts remain unchanged.
There is no schema migration, history import or change to matching/delay logic.

## Verified source and selection policy

Pinned local archive: `official-static-1710.zip`, SHA-256:
`ef06c7e3a8e5d8613505db3c7b66d87328c02bb3bb599ab5d2054eb23b654c55`.
Feed metadata identifies Adelaide Metro, publisher URL
<https://www.adelaidemetro.com.au/>, version **1710**, valid **2026-10-16 through
2027-04-09**. This archived version is not claimed to be the latest available feed.
The manifest records the ZIP identity, hashes of every consumed source file,
feed metadata, generation time, selected agency records, policy and output hashes.
It is a reproducible identity check, not a cryptographic signature of the publisher.

| Included agency_id | Feed agency name | route_type=3 routes |
| --- | --- | ---: |
| 4 | Adelaide Metro (SouthLink) | 33 |
| 5 | Adelaide Metro (Torrens Transit) | 300 |
| 8 | Adelaide Metro (Busways) | 51 |
| Total | Explicit selected bus network | 384 |

Only `route_type=3` is selected. The same agencies also have 163 routes coded
`712`, excluded by this policy. Rail (11 routes), tram (3), regional agencies
and ferry are excluded. All 716 feed routes or all 561 Adelaide Metro agency
routes must not be described as this selected bus network. No geographic polygon
filter is applied. Included routes can extend beyond a strict metropolitan boundary.
All scheduled variants in the feed are retained, without a service-date filter;
publication does not mean every route/trip runs every day or at the selected hour.

## Publication results

| Metric | Verified selected network |
| --- | ---: |
| Routes | 384 |
| Stops referenced by selected stop-times | 7,240 |
| Additional parent stations | 1 |
| Total catalog locations | 7,241 |
| Trips | 17,017 |
| Stop-times | 722,018 |
| Unique usable shapes / route-shape variants | 1,148 / 1,148 |
| Unique shape points | 503,557 |

IDs remain exact strings. Stop-times retain ordered sequence, repeated visits and
original fields. Selected trip service IDs are checked against the calendars.
Parent locations remain `location_type=1`; platforms/stops remain `0` with their
`parent_station`. Parent catalog route associations are inherited from selected
child stops, not fabricated direct vehicle calls at a station centroid.

Publication fails atomically on missing references, duplicate IDs or selected
trip/sequence keys, missing trip relationships, missing/degenerate shapes, bad
coordinates or duplicated shape sequences. Existing folders are never overwritten.
No selected route in this feed lacked usable geometry. A future feed with missing
geometry must be corrected or deliberately reselected; the publisher does not
fabricate lines or silently omit affected trips.

## Rebuild and configure

Use the repository Python environment and requirements. Choose a **new external
output folder**, preferably with a short Windows path. Do not put the roughly
283 MB generated network in Git. Use a complete publication folder, including
manifest, catalog and route files. Keep the recorded demo folder separate.

```powershell
python -m backend.services.static_map_data --archive "PATH\official-static-1710.zip" --sha256 ef06c7e3a8e5d8613505db3c7b66d87328c02bb3bb599ab5d2054eb23b654c55 --version 1710 --agency-id 4 --agency-id 5 --agency-id 8 --route-type 3 --output "PATH\static-map-1710"
```

The verified archive on the development machine is at
`D:\Adelaide study\2026\ICT Capstone Project\CASR historical data\analysis\release_compatibility_20261021_131419\official-static-1710.zip`.
The prepared network is in the sibling evidence folder listed below. A teammate
can obtain that entire `network/` folder from the Backend owner, or obtain the
pinned ZIP and rebuild it using the command above. Neither is distributed through
this Git branch. Verify the archive SHA-256 before using a separately supplied ZIP;
do not substitute a newer feed under the version 1710 label.

For the verified first vertical slice, add `--route-id 100 --route-id J1` and use
another new output folder. The agency/type policy is still enforced.

```powershell
$env:ADELAIDE_METRO_STATIC_MAP_DATA_PATH = 'PATH\static-map-1710'
# Optional mixed mode: point these to the existing matching September demo files.
# Required only for historical queries / recorded-demo requests respectively.
$env:ADELAIDE_METRO_DATABASE_PATH = 'PATH\adelaide_metro_demo.db'
$env:ADELAIDE_METRO_DEMO_MAP_DATA_PATH = 'PATH\demo_map_data'
# For static-only mode, leave the recorded-demo variable unset.
# The static publisher does not generate or change either historical input.
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5000
```

Files: `catalog.json` (route and stop dimensions), `routes/<hashed-id>.json`
(one route's metadata, shapes, trips and ordered stop-times), `calendars.json`
(original source calendar rows), `manifest.json`. Trips retain `service_id` and
`shape_id`. All relationships needed for this selected network are published;
this task does not load them into the historical SQLite tables. The calendar
artifact retains source rows, including services outside the selected routes.
Generation stages files beside the output and renames only after validation.
Output payload hashes are deterministic; `generated_at` intentionally varies.

## Frontend API handover

When the static environment variable is unset, metadata endpoints retain their
existing database-backed behaviour. When set, these endpoints read the selected
static catalog (same array/row contracts, additional GTFS fields allowed):

- `GET /api/routes`: selected routes for the existing dropdown.
- `GET /api/stops`: selected stop/platform and parent station locations.
- `GET /api/stops/<stop_id>`: one selected location, or 404.
- `GET /api/stops/<stop_id>/routes`: its selected routes; unknown stop gives `[]`.
- `GET /api/routes/<route_id>/map-data`: bounded route geometry and relationships.

The existing frontend already requests map-data for one selected route and uses
`L.geoJSON(data.geometry)` and `data.stops`. These fields and GeoJSON coordinate
order **[longitude, latitude]** are preserved. No Frontend file was changed.
Encode IDs with `encodeURIComponent`; do not reverse GeoJSON coordinates.

Source selection is explicit when versions overlap:

| Configuration/request | Behaviour |
| --- | --- |
| Recorded demo configured, default request for G10/M44/506 | Original recorded response, unchanged |
| Recorded demo configured, route absent from its manifest | Use static publication if configured |
| Only static configured | Use selected static publication |
| `?source=static` | Require static publication, including for G10/M44/506 |
| `?source=recorded` | Require original recorded publication; no static fallback |

An inconsistent configured demo fails closed with 503 rather than silently
presenting a different version as recorded evidence. Unknown selected route is
404. Missing/unconfigured/corrupt static geometry is 503 with a static-artifact
error, distinct from a performance 404. Invalid `source` is 400.
In mixed mode catalog metadata uses 1710 while default recorded demo geometry
uses 1692; use `?source=static` for consistent static browsing, and use an explicit
recorded-demo context for September playback. Do not join trips across versions.

```text
GET /api/routes/100/map-data
GET /api/routes/J1/map-data
GET /api/routes/G10/map-data?source=static
GET /api/routes/G10/map-data?source=recorded
```

Static response fields include `label`, `data_source: "static_gtfs"`,
`static_feed_version: "1710"`, `historical_data_status: "not_included"`,
`observation_window: null`, `route_id`, `route`, `geometry`, `stops`, `trips`.
`shared/schemas/static-route-map.schema.json` reuses the recorded schema's shape
and stop definitions; distribute both schemas. The recorded schema is unchanged.
`not_included` describes the artifact, not a claim that the separately configured
historical database contains no observations. Query the existing performance and
vehicle-history endpoints independently. A valid static route returned geometry
200 with an empty synthetic historical database while performance returned
404 `{"error":"Route performance not found"}`. Never convert missing observations
into zero delay, recorded coverage or a live vehicle. Static map access itself
does not require a database; historical endpoints still require their existing
separate database configuration.

## Validation evidence and practical limits

First, real non-demo routes **100** and **J1** passed metadata, API, schema,
shape variants, stop relationships and no-history checks. The slice contains
201 trips, 16 shapes, 283 referenced stops plus one parent. Then **all 384**
published routes passed Flask requests, static schema validation and trip/shape/
stop checks; every route performance request against empty history returned 404.
Independent ZIP comparison checked all 384 route identities, 17,017 trip shape
mappings, 722,018 stop-times and published stop names/coordinates. Two full-network
generations produced identical hashes for every route, catalog and calendar file.
The source archive hash was unchanged.

| Route | Shape variants | Trips | Published locations |
| --- | ---: | ---: | ---: |
| 100 | 7 | 78 | 137 |
| J1 | 9 | 123 | 147 |

Generation took about 20.3 seconds (repeat 20.9). Output size is 282,827,314 bytes.
All-route Flask/schema validation took 54.2 seconds. Local in-process Flask request
median was 10.4 ms, maximum 107.1 ms; median response 352,952 bytes, maximum
6,248,114 bytes. These are observations on this machine, not production latency
or browser rendering benchmarks. Each map request verifies and reads only the
manifest and requested route artifact, never the complete GTFS shape file or
other routes. Catalog requests read their separately bounded catalog; there is no
persistent cache to become stale. Large route responses retain full trip/stop-time
relationships for compatibility; the Frontend should avoid repeated requests and
handle loading state. HTTP compression/caching and a smaller optional geometry-only
contract can be evaluated later if browser measurements justify them.

Final delivery regression: **348 passed in 48.33 seconds**, zero failures or skips,
including **24 new cases**. `git diff --check` and whitespace checks covering
all new files passed. The broader run covers backend/API/repository tests and
analysis/database integration tests; counts are not added across repeated runs.

Automated tests reuse the recorded fixture and include selection, leading-zero
IDs, multiple/shared shapes, station hierarchy, repeated visits, malformed input,
provenance, deterministic output, no overwrite, 404/503, route-bounded reads and
mixed-mode demo precedence. Existing G10/M44/506 fixture responses remain exactly
equal to the original recorded reader; original recorded schema tests pass.
No real demo artifact was regenerated or modified. Initial local test setup hit
temporary-folder permissions and Windows long paths; use an explicitly writable,
short `--basetemp` for this environment.

Local evidence is outside Git in sibling `scrum282-evidence-20261102/`:
`vertical-slice/`, `network/`, `network-repeat/`, `vertical-slice-validation.json`,
`network-validation.json`, `rebuild-and-source-audit.json`, and JUnit regression
results. The validation scripts there use disposable empty databases only.

## Remaining Frontend and CASR work

Frontend ownership includes clear static-versus-recorded labels, source selection
for mixed versions, parent/platform display decisions, route variant selection,
large-network rendering performance, no-history handling, screenshots and real
browser/E2E verification. No new visual verification is claimed by this task.
Static geometry is independent of unresolved static/realtime `stop_sequence`
compatibility. It does not validate production collection continuity, CASR Task
Scheduler, power-loss recovery or replacement backup integrity. The malformed
CASR backup was not accessed. Git delivery is subject to final review; deployment
and release remain outside this handover.
