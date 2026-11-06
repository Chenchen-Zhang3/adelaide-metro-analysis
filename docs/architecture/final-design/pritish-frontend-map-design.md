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
