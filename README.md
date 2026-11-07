
Adelaide Metro Transport Analysis
Client: Centre for Automotive Safety Research (CASR)
Team: UG-S2-15
Final presentation: 9 November 2026
Last updated: 7 November 2026

Adelaide Metro Transport Analysis is a research-oriented web application for exploring Adelaide Metro's static network and recorded historical transport information. It combines a Leaflet map, a Python/Flask JSON API, a prepared GTFS Static catalog, and an SQLite historical database. It is not a live vehicle-tracking or actual-arrival verification service.

Features
City-wide routes and stops, with route selection and stop details.
Route and stop performance statistics based on historical predictions.
Network-wide predicted-delay visualisation, including missing/insufficient-data states.
Historical delay hotspot rankings and map markers.
Historical vehicle-position playback with Adelaide time handling.
Nearest-stop search from a map-selected location (straight-line distance).
Quick start — final historical analysis website (Windows)
These commands describe the locally verified CASR v2 workflow. The historical database and generated static catalog are not included in GitHub. Obtain them through the approved CASR/team sharing location (the team's OneDrive Final presentation folder, if you are authorised to access it).

1. Get the code and install dependencies
Download the latest main branch from this repository (using Code → Download ZIP), extract it, and open PowerShell in the extracted project folder. Alternatively, clone this repository with its actual Git URL.

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
Tested development environment: Windows, Python 3.12.2. Do not run the application using Python from an unrelated environment.

2. Obtain and place the data
The following files are supplied separately from the repository:

Final presentation/
├── static-map-1710/
│   ├── catalog.json
│   ├── calendars.json
│   └── manifest.json
├── adelaide_metro_history_v2_20261022_140923.db
└── official-static-1710.zip
Required to run the verified CASR v2 website: the complete static-map-1710 folder and the historical .db file.
For provenance/regenerating the static catalog: official-static-1710.zip (the site does not read this ZIP directly).
Preserve the original supplied historical database. Use a verified working copy for application access; do not use the original Box backup as the writable Flask database. Do not commit datasets to GitHub.
For example, copy these files into a separate local folder such as C:\AdelaideMetroData, leaving the original shared copy untouched.

3. Start the backend
In the first PowerShell terminal, from the project root, set the paths to your own computer's files:

.\.venv\Scripts\Activate.ps1
$env:ADELAIDE_METRO_DATABASE_PATH = "C:\AdelaideMetroData\adelaide_metro_history_v2_20261022_140923.db"
$env:ADELAIDE_METRO_STATIC_MAP_DATA_PATH = "C:\AdelaideMetroData\static-map-1710"
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5001
Keep this terminal running. Check that Flask reports http://127.0.0.1:5001. Do not point this command at a collector's active database or the original immutable backup.

4. Start the frontend
Open a second PowerShell terminal in the same project root:

python -m http.server 8000
Open http://127.0.0.1:8000/frontend/ in a browser.

The repository's frontend/js/map.js currently uses http://127.0.0.1:5001 as its API base URL. Therefore the commands above use port 5001; no frontend-casr-test copy or JavaScript edit is necessary for this configuration. Both terminals must stay open. Internet access is required for online map tiles.

5. Check that the site is working
Confirm the city-wide map loads; the tested GTFS Static 1710 catalog contains 384 routes and 7,241 locations.
Select a route (e.g. G10 or M44) and check that route performance appears.
Click a blue stop marker to display stop details and performance.
Open Historical Delay Hotspots or Network-Wide Prediction Delays. Choose a time interval covered by the historical data; not all stops have enough observations.
For a playback smoke test, select Route 100, 17 October 2026, 09:00–09:30 Adelaide time and load historical vehicle positions. Confirm playback loads and the time progresses. Data coverage may be sparse in some windows.
If you see Route not found, verify you pulled the latest backend and configured the intended CASR v2 database. If you see no data, first check the historical date/time range and static-vs-historical route coverage.

Automated tests
From the project root, use a new temporary SQLite database instead of a protected historical backup:

.\.venv\Scripts\Activate.ps1
$env:ADELAIDE_METRO_DATABASE_PATH = Join-Path $env:TEMP ("adelaide-metro-test-" + [guid]::NewGuid().ToString("N") + ".db")
python -m pytest -q
Recorded regression result (7 November 2026): 415 passed in 96.27 seconds. This is evidence from the tested version, not a promise of identical timing in every environment.

Data, safety and limitations
Static GTFS network coverage and historical observation coverage are different; static routes do not necessarily have historical records.
Historical delay figures are based on recorded predictions, not necessarily confirmed actual arrivals. A missing value must not be interpreted as zero delay.
Vehicle playback uses recorded historical positions, not live vehicle tracking; recorded observations may be sparse.
Map-based nearest-stop distances are straight-line estimates, not walking routes.
The local website verification does not certify the separately deployed CASR production collector, its automated restart, or long-term reliability. An earlier October production backup was flagged for integrity concerns; the separately obtained and checked CASR v2 file used for final local testing passed its own SQLite integrity check. Do not conflate those claims or change a production release HOLD based only on local tests.
Browser geolocation requires permission, and large historical queries may hit API limits.
Final browser verification covered playback loading and timeline progression; Reset and route-switching during playback and individual No Data marker popups were not independently confirmed in the cited QA run.
Documentation and technical references
Final Setup and Handover Guide — detailed installation, datasets, fallback demo, data protection and delivery checklist.
Sprint 5 Final Integration Test Report — actual API, browser and pytest results.
CASR GTFS Collection and Data Access — collector operation, schema and research-data access.
CASR v2 Vehicle Playback Integration — playback compatibility fix, API contract and verification.
City-wide Static Map Preparation — preparation and provenance of static catalog.
Sprint 5 GTFS Integration — static-data and integration decisions.
Final Design Documents — module and system design materials.
Developer reference (existing project capabilities)
The repository also contains GTFS and GTFS-Realtime collection/parsing modules, optimised trip-update persistence, shared schemas, API services, automated tests and deployment scripts. These are separate from starting the historical-analysis website and may require additional operational configuration.

Key directories:

backend/                  Flask API, analysis, database and data services
frontend/                 Leaflet/JavaScript web interface
shared/                   Shared GTFS entities and schemas
tests/                    Integration tests and fixtures
scripts/                  Collection, validation and operational scripts
docs/                     Architecture, deployment, testing and handover
For continuous collection or CASR Windows hosting, follow the dedicated collection guide and Windows deployment guide. Do not treat the local browser-demo quick start as instructions for modifying a production collector.

The earlier September G10/M44/506 demonstration files remain a separate fallback; see the Final Setup and Handover Guide and the archived Sprint 4 Demo Setup.
