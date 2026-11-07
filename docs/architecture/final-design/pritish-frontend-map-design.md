# Frontend map and historical prediction delay integration

## Purpose and user requirements
Provide an interactive Adelaide Metro map with route selection, stop information, historical vehicle playback and a network-wide view of predicted arrival delays for a selected historical observation window.

## Architecture and data provenance
- Frontend: Leaflet, OpenStreetMap basemap, `frontend/js/map.js` and `frontend/js/network-delays.js`.
- Backend: Flask API configured via `ADELAIDE_METRO_DATABASE_PATH` (October 2026 research database) and `ADELAIDE_METRO_STATIC_MAP_DATA_PATH` (published official GTFS v1710).
- `/api/stops` and `/api/routes` return the published static catalogue when configured. The catalogue contains 7,600 stop/station records, including 120 parent stations, and 398 routes for the configured agency and mode selection.
- `/api/routes/{route_id}/map-data?source=static` supplies static timetable route shape variants and route stop geometry. These shapes are **not** evidence of observed vehicle travel.
- `/api/analysis/stop-delays` provides historical GTFS-Realtime *predictions*, not actual arrivals or live performance. The frontend sends one bounded request with ISO 8601 UTC timestamps, `scope=static` and `min_samples=10` by default.

## UI and design decisions
- Historical prediction categories: early (<0 min), 0–5 min, >5–10 min, >10 min, insufficient data, and no data. These are visual bins, not validated service reliability thresholds.
- The map joins returned records to eligible static platform stops using exact string stop IDs. Parent stations (`location_type=1`) are excluded from delay markers and no-data totals. Only timetable-referenced stops from the published static catalogue are included.
- A selected-route filter sends `route_id` to the backend and restricts displayed markers to platform stops belonging to that route.
- When changing filters, the frontend requests a reload instead of displaying stale route-filtered predictions.
- Adelaide local datetime inputs are converted to offset-aware UTC with explicit daylight-saving ambiguity detection.
- Requests are cancellable; backend errors are shown rather than presented as zero delay. Route map uses explicit `source=static` to avoid recorded demo selection.

## Testing and limitations
- JavaScript syntax checked using `node --check` for both modified scripts.
- API integration verified by user on October 17 2026, 09:00–09:15 Adelaide time: HTTP 200, 4,610 returned stop records, 2,870 eligible stops without observations, 7,480 eligible platform stops, and 32,267 retained rows before route filtering.
- The number of stops with **available** averages is lower than the number with records because `min_samples=10` marks many as insufficient.
- Browser rendering and route geometry requests require end-to-end verification on the user's Mac with their local 1.9 GB database and published static catalogue; these files are not included in the code package.
- Static GTFS routes reflect scheduled geometry; historical vehicle playback is a separate dataset and should not be described as live tracking.
- The original September playback default time range may need updating separately if the user wants October playback by default.

## Dependencies
Leaflet, OpenStreetMap tiles, Flask backend, official Adelaide Metro GTFS v1710 and historical GTFS-Realtime research database.

## Implemented frontend workflow and module responsibilities

1. **Initial network view:** `frontend/js/map.js` initialises the Leaflet map, loads `/api/stops` and `/api/routes`, and draws selectable stop markers. OpenStreetMap provides the basemap, while the Flask endpoints supply network data. The official static catalogue is used when the backend is configured with `ADELAIDE_METRO_STATIC_MAP_DATA_PATH`.
2. **Route selection:** The route selector requests `/api/routes/{route_id}/map-data?source=static` and renders scheduled GTFS shape variants and stops. Separate `/api/routes/{route_id}/performance` results populate route performance details. Route geometry is a published timetable representation, not a historical vehicle trajectory.
3. **Stop selection:** Selecting a stop requests `/api/stops/{stop_id}/routes` and `/api/stops/{stop_id}/performance`, then displays its associated routes and available details.
4. **Nearest stop:** A user can click a map location or use browser geolocation (subject to permission). The frontend computes Haversine straight-line distance to loaded stops, highlights the nearest candidate, and displays the distance. It does **not** calculate walking routes or travel time.
5. **Nearest-stop metrics (PR04):** `/api/stops/{stop_id}/service-metrics` receives an Adelaide-local selected interval converted into offset-aware timestamps. The UI distinguishes *scheduled GTFS departures per hour* from *historical prediction-observation reliability*, shows sample and unique-trip counts, and explicitly labels insufficient evidence. Predictions are not actual completed-trip punctuality.
6. **Historical playback (PR03):** The selected route and interval are sent to `/api/routes/{route_id}/vehicle-positions`, with pagination (`limit=1000`, `offset`) and `/coverage` for suggested recorded dates. The frontend advances a playback clock and updates vehicle markers from recorded GPS observations; this is neither a live feed nor proof of continuous movement between observations.
7. **Hotspots (PR03):** `/api/analysis/hotspots` is queried for the selected route and minimum service count. The ranked results are displayed both as markers and as a list. Changing routes invalidates previous hotspot requests.
8. **Network-wide prediction-delay view (PR02):** `frontend/js/network-delays.js` requests `/api/analysis/stop-delays` for a bounded historical window. It manages prediction-category markers and temporarily hides overlapping layers; the selected route can restrict the view. The displayed categories are based on historical *predicted* arrival offsets.

## UI/UX rationale and technical fixes

- Keep route, stop, nearest-stop, hotspot, playback and network-delay functions in discoverable controls rather than mixing their markers indiscriminately. The delay view manages layer visibility to reduce clutter.
- Show loading, empty-data and API-error states rather than silently treating missing observations as on-time performance.
- Use request counters and cancellation/selection checks to prevent slower asynchronous responses from repainting an outdated route or location.
- Interpret Adelaide local dates with daylight-saving awareness before calling timestamp-based APIs; the network-delay view rejects ambiguous or nonexistent local times. The nearest-stop metrics converter resolves matching offsets but does not explicitly reject a repeated local time as ambiguous.
- Escape inserted HTML text in the nearest-stop metrics display. Keep static GTFS scheduled geometry separate from recorded vehicle observations.
- An integration test collection failure involving pytest parameter IDs was addressed by assigning explicit IDs to the invalid-protobuf and HTTP-403 test cases.
- A full backend suite was run with local dataset override environment variables unset, preventing the published static catalogue from replacing test fixtures.

## Code review and verification record

- `frontend/js/map.js` has targeted comments at nearest-stop selection, scheduled-versus-observed metrics, playback pagination, request invalidation and hotspot rendering. `frontend/js/network-delays.js` already contains comments for timezone handling, prediction-only categories, marker eligibility and overlay management.
- The developer reported **400 passed, 3 skipped** for `python3 -m pytest -q backend/tests` after unsetting `ADELAIDE_METRO_STATIC_MAP_DATA_PATH`, `ADELAIDE_METRO_DEMO_MAP_DATA_PATH` and `ADELAIDE_METRO_DATABASE_PATH`.
- The developer reported the PR04 commit **`918cc04`** pushed to `feature/S5-network-delay-frontend`.
- Earlier PR04-specific testing reported **4 passed** for `backend/tests/test_nearest_stop_metrics.py`.
- Historical prediction API integration evidence from 17 October 2026 is recorded above; this is API evidence, **not** a screenshot or proof of final browser acceptance.
- **Final browser testing evidence still required:** capture screenshots and outcomes for citywide map loading, route and stop selection, nearest-stop with metrics, network prediction categories, hotspots, playback controls and empty/error states. Record browser/version, date, route/stop IDs, historical time windows, and any console/network errors. Do not mark this complete until performed.
- **JavaScript syntax and whitespace checks:** run `node --check frontend/js/map.js`, `node --check frontend/js/network-delays.js`, and `git diff --check` after applying the comment changes; the uploaded archive alone does not prove these final checks were executed.

## Remaining limitations and follow-up

- The historical database and static GTFS catalogue are local external inputs and were excluded from the uploaded ZIP, so full data-backed browser verification cannot be independently reproduced from this archive.
- Predictions, scheduled frequencies and observed GPS positions answer different questions; none alone establishes actual stop arrival punctuality.
- Nearest-stop distance is straight-line distance and may differ substantially from a pedestrian route.
- Playback depends on recorded position coverage, may have gaps, and must not be presented as live tracking.
- Browser performance with all Adelaide-wide markers, map tile availability, browser geolocation permission and final acceptance screenshots remain to be verified on the development machine.
