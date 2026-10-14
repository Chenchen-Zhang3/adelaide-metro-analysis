# Recorded demo route geometry and shared map data

SCRUM-232 / S4-C02. Prepared 2026-10-14 from main `effa203`, after verifying
SCRUM-233 is merged. **Recorded Historical Data — September 2026**.

## Source and boundary

Use the same archived Adelaide Metro static feed **1692** and recorded demo
database/manifest from SCRUM-233. The archive SHA-256 and extracted static
files are checked using the existing demo preparation helpers. `shapes.txt`
is additionally checked byte-for-byte against its archived entry. Its SHA-256:
`aac70302ec86924134dffb67e88a78112b7aaf8b93619d1cd72e244631b134d7`.

Only the 55 selected recorded trips are associated with shapes, not all trips
on these routes. Demo DB is opened `mode=ro&immutable=1; query_only=ON` and its
SHA-256 is checked before and after extraction. Its expected hash remains
`735de9404b6fe46d52fe0b102004e6993815157b8f5905341afbf9cada465aa2`.
Neither the demo DB nor the original 6 GB CASR snapshot is modified. The full
C01/C03 historical audits were not repeated.

## Official shapes and coverage

| Route | shape_id → point count | Total points | Selected trips | Route stops |
| --- | --- | ---: | ---: | ---: |
| G10 | 16638 → 319; 16782 → 448; 16783 → 465 | 1,232 | 22 | 145 |
| M44 | 15144 → 517; 15145 → 296; 15150 → 568 | 1,381 | 21 | 114 |
| 506 | 3240 → 463; 3246 → 453 | 916 | 12 | 98 |

Total: **8 separate shape variants, 3,529 points, 55 trips and 354 unique stops**.
Per-route stop counts overlap, so they must not be summed as unique stops.
Stops and route/trip associations follow selected trip `stop_times`, not a
Cartesian product of three routes and every stop. Repeated visits to the same
stop retain their individual `stop_sequence` entries in the trip mapping.

Shape points are sorted numerically by `shape_pt_sequence`; a route can have
multiple shapes and a shape can be shared by multiple trips/routes. Features
remain separate per `(route_id, shape_id)` and include their exact trip IDs and
available direction IDs. Choose the shape using the recorded `trip_id`, not by
assuming one direction/shape per route.

No shape is missing. All coordinates are finite, legal and inside the broad
Adelaide sanity bounds. G10 shapes 16782 and 16783 have respectively 19 and 18
repeated coordinates, none adjacent. These official coordinates are preserved;
they can occur on overlapping segments and are not automatically declared a
software error. Duplicate sequence numbers or degenerate/missing selected
shapes fail validation instead of generating substitute lines.

## Output files

Directory relative to the capstone project folder:
`CASR historical data/analysis/demo_map_data/`.

| File | Contract | Bytes |
| --- | --- | ---: |
| route-shapes.geojson | FeatureCollection of 8 LineStrings, one per route/shape variant | 100,143 |
| stops.geojson | FeatureCollection of 354 Points, with stop fields and associated route_ids/trip_ids | 124,931 |
| trip-map.json | 55 trip→route→shape mappings with ordered stop visits/direction_id | 127,861 |
| manifest.json | Source fingerprints, coverage, point counts, diagnostics and payload hashes | 4,671 |

The three payloads total approximately 345 KiB. Generated payloads stay outside
Git; share the **whole folder**, including manifest, alongside the separate C03
demo database. A small manifest copy is committed under
`docs/integration/evidence/recorded-demo-map.manifest.json`.
Two independent real-data generations produced matching hashes for every file.

Reproduce from this branch or merged main, using existing `requirements.txt`:

```powershell
python -m backend.services.recorded_map_data --demo-db "PATH\demo_dataset\adelaide_metro_demo.db" --demo-manifest "PATH\demo_dataset\adelaide_metro_demo.manifest.json" --static-dir "PATH\GTFS\google_transit" --static-archive "PATH\GTFS\google_transit.zip" --output "PATH\analysis\demo_map_data"
```

Use a new output folder; existing artifacts are never overwritten. Generation
streams the shapes CSV, retaining only requested shapes; no live API request or
collector is required. All required inputs come from the pinned C03 handover.

## Backend and shared contract

There was no existing geometry endpoint. One focused read-only addition is:

`GET /api/routes/<route_id>/map-data`

The existing `/api/routes`, `/api/stops`, stop-to-route and performance endpoints
are preserved. New endpoint uses prepared artifacts and does not add shape
tables or modify storage. Configure both data paths before importing the app:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = 'C:\team-demo\adelaide_metro_demo.db'
$env:ADELAIDE_METRO_DEMO_MAP_DATA_PATH = 'C:\team-demo\demo_map_data'
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5000
```

Set the map-data path to the directory, not a single file. Confirm the existing
routes/stops endpoints return 3 routes and 354 stops, so the server is using
the matching recorded database rather than an unrelated application database.

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/routes/G10/map-data
Invoke-RestMethod http://127.0.0.1:5000/api/routes/M44/map-data
Invoke-RestMethod http://127.0.0.1:5000/api/routes/506/map-data
```

Response fields: `label`, `static_feed_version`, `observation_window`, `route_id`,
`geometry` (LineString FeatureCollection), `stops` (Point FeatureCollection),
and `trips` (route-specific trip/shape/ordered-stop mappings). IDs remain exact
strings. Shared schema: `shared/schemas/recorded-route-map.schema.json`.
All payload files are hash-verified on access; unknown route returns 404 and
unconfigured/missing/inconsistent artifacts return a readable 503. Existing
endpoints remain usable when map artifacts have not yet been configured.

GeoJSON coordinates are **[longitude, latitude]**. Named stop fields remain
`stop_lat` and `stop_lon`. Leaflet's `L.geoJSON` converts coordinates itself;
do not reverse them before passing GeoJSON. Direct `L.polyline` arrays instead
require `[latitude, longitude]`.

## Frontend integration example — not yet wired into the browser

The current map already uses Leaflet and route selection, but does not yet fetch
this endpoint or draw these shapes. SCRUM-234 can add a call alongside the route
selection handler in `frontend/js/map.js`, retaining current performance UI:

```javascript
const response = await fetch(
  `${API_BASE_URL}/api/routes/${encodeURIComponent(routeId)}/map-data`
);
if (!response.ok) throw new Error(`Map data unavailable: ${response.status}`);
const data = await response.json();
// Remove previous route layers on each selection; keep layer handles in UI state.
const routeLayer = L.geoJSON(data.geometry).addTo(map);
const stopLayer = L.geoJSON(data.stops, {
  pointToLayer: (_feature, latlng) => L.circleMarker(latlng, {radius: 4})
}).addTo(map);
map.fitBounds(routeLayer.getBounds());
```

This renders separate official variants, not one concatenated polyline. To
display one recorded trip, use its trip-map entry or filter LineString features
by `feature.properties.trip_ids.includes(tripId)`. No road snapping, synthetic
vehicle trajectory, animation or playback controls are implemented in C02.

## Evidence and remaining SCRUM-234 work

**96 related tests passed**, including 14 new geometry/contract/API cases.
Coverage includes numeric point ordering, missing/bad shapes, coordinate ranges
and reversed-axis schema rejection, multiple variants, shared shapes, exact IDs,
shared stops/repeated visits, artifact hashes, no overwrite, 404/503 and existing
endpoint compatibility. Parser, C01, C03, repository, pipeline, API and analysis
regressions passed. C05's long-running simulation was not repeated.

Actual local artifact smoke, with HTTP fetching blocked: G10/M44/506 each return
200; outputs pass the shared schema; all 55 trip/shape assignments and selected
stop associations match. Existing routes/stops endpoints return 3/354. Demo
database hash is unchanged. No original CASR data or frontend file was modified.

Geometry/data contracts are ready for review and the tentative 19 October demo.
Actual browser map integration has **not** been claimed complete. SCRUM-234 must:

1. Wire route selection to the new endpoint and remove old layers on changes.
2. Choose/render the correct trip shape/variant and handle 404/503 visibly.
3. Integrate historical vehicle data/time controls using the separate playback
   interface; this endpoint supplies geometry and relationships, not vehicle frames.
4. Show **Recorded Historical Data — September 2026**, preserve the September
   timestamps, and avoid claiming feed 1692 is current live October service.
5. Verify actual browser styling, stop popups, responsive behaviour and selected
   trip/stop interaction. Escape external stop/route names when building HTML.
6. Check Leaflet CDN/OpenStreetMap tile availability or separate caching; offline
   GTFS/map-data artifacts do not automatically provide an offline basemap.

No automatic merge, Jira transition or SCRUM-234 implementation was performed.
