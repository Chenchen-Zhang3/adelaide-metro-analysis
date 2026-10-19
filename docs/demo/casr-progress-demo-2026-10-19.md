# CASR Progress Demo — 19 October 2026

**Project:** Adelaide Metro Real-Time Transport Analysis  
**Jira:** SCRUM-235 / S4-C05  
**Client:** Centre for Automotive Safety Research (CASR)  
**Demo Type:** Sprint 4 Progress Demonstration

This document provides the technical setup, verified functionality, demonstration workflow and known limitations for the CASR progress demo.

The demonstration uses recorded historical data rather than live transport observations. It is intended to show the project's current development progress, not final product acceptance.

## 1. Demo Overview

The prototype uses real Adelaide Metro historical data to demonstrate public transport data processing, storage, querying and visualisation.

**Recorded Dataset**

| Item | Details |
|---|---|
| Data source | Adelaide Metro GTFS / GTFS-Realtime |
| Static GTFS version | 1692 |
| Observation date | 26 September 2026 |
| Time window | 09:00–11:00 Adelaide time (UTC+09:30) |
| Selected routes | G10, M44, 506 |
| Vehicle Positions | 1,792 |
| Retained Trip Updates | 22,256 |
| Trips | 55 |
| Stops | 354 |
| Official shape variants | 8 |
| Route geometry points | 3,529 |
| Demo database size | 3.68 MiB |

**Required data label:**

Recorded Historical Data — September 2026

The dataset must not be presented as live data.

## 2. Current Functionality

Status based on the local validation conducted on 16 October 2026. Any newer frontend functionality must be tested before being included in the demonstration.

| Component | Status | Details |
|---|---|---|
| GTFS processing pipeline | Working | Fetch, decode, validation, conversion and delay processing |
| Historical SQLite storage | Working | Optimised v2 schema and historical queries |
| Backend API | Working | Routes, stops, performance, vehicle history and map-data endpoints |
| Recorded demo database | Working | Independent of CASR computer and live API |
| Frontend map | Working | Leaflet map and stop markers |
| Route selection | Working | G10, M44 and 506 |
| Route statistics | Working | Route performance summaries |
| Official route geometry API | Working | All 8 shape variants available |
| Historical vehicle API | Working | Route/time filtering and pagination |
| Route geometry rendering in browser | Pending integration | Backend data available |
| Historical vehicle playback | Pending integration | Frontend controls and rendering required |
| Recorded-data banner | Pending integration | Must clearly identify historical data |
| CASR automatic restart | Awaiting confirmation | Production-side verification required |

The browser interface and backend APIs have been tested separately.

**Backend API success does not automatically mean the corresponding frontend feature has been integrated.**

## 3. Required Demo Files

The following files are available through the team-shared OneDrive folder:

`UG-S2-15 / demo database --sprint4`

```text
demo database --sprint4/
├── adelaide_metro_demo.db
├── adelaide_metro_demo.manifest.json
└── Map data/
    ├── route-shapes.geojson
    ├── stops.geojson
    ├── trip-map.json
    └── manifest.json
```

For local setup, place the files in the following repository-relative directories:

```text
adelaide-metro-analysis/
├── data/
│   ├── demo/
│   │   └── adelaide_metro_demo.db
│   └── demo_map_data/
│       ├── route-shapes.geojson
│       ├── stops.geojson
│       ├── trip-map.json
│       └── manifest.json
```

The database manifest should be retained alongside the downloaded files for provenance and integrity checks.

These generated binary/data files are not automatically included when cloning the GitHub repository.

**Important:** Do not use or modify the original 5.59 GiB CASR historical database for this demonstration.

For detailed setup instructions, refer to:

`docs/integration/sprint4-demo-setup-and-risks.md`

## 4. Application Startup

The following commands assume Windows PowerShell, Python 3.12, and the required project dependencies.

Run all commands from the repository root.

### 4.1 Prepare Python Environment

If a suitable environment is not already available:

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Use the Python environment containing the required Flask, protobuf, GTFS and timezone dependencies.

Verify that the demo database and four map-data files have been downloaded and placed in the expected directories before starting the application.

### 4.2 Terminal A — Start Backend

```powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path

$demoSource = (Resolve-Path .\data\demo\adelaide_metro_demo.db).Path
$mapData = (Resolve-Path .\data\demo_map_data).Path

& $python -m backend.services.e2e_demo_check --database "$demoSource" --map-data "$mapData"

if ($LASTEXITCODE -ne 0) {
    throw 'Demo verification failed'
}

$demoCopy = Join-Path $env:TEMP ('adelaide-demo-' + [guid]::NewGuid().ToString('N') + '.db')

Copy-Item -LiteralPath $demoSource -Destination $demoCopy

$env:ADELAIDE_METRO_DATABASE_PATH = $demoCopy
$env:ADELAIDE_METRO_DEMO_MAP_DATA_PATH = $mapData

& $python -m flask --app backend.api.app run --host 127.0.0.1 --port 5000 --no-reload
```

Backend URL:

`http://127.0.0.1:5000`

The temporary database copy prevents the demonstration from changing the original demo database.

Ensure port 5000 is available before starting.

### 4.3 Terminal B — Start Frontend

Open a second PowerShell terminal in the repository root:

```powershell
& .\.venv\Scripts\python.exe -m http.server 8000 --bind 127.0.0.1
```

Open the application in a browser:

`http://127.0.0.1:8000/frontend/`

The frontend currently uses port 5000 for backend API requests.

Leaflet and OpenStreetMap resources may require an internet connection or existing browser cache.

## 5. API Verification

The following endpoints support the recorded demo.

| Endpoint | Purpose |
|---|---|
| `GET /api/routes` | Retrieve available routes |
| `GET /api/stops` | Retrieve available stops |
| `GET /api/routes/G10/performance` | Retrieve route performance statistics |
| `GET /api/routes/G10/map-data` | Retrieve official geometry and related map data |
| `GET /api/routes/M44/map-data` | Retrieve M44 map data |
| `GET /api/routes/506/map-data` | Retrieve 506 map data |
| `GET /api/routes/G10/vehicle-positions` | Query recorded vehicle positions by time range |
| `GET /api/stops/100618/routes` | Retrieve routes serving a selected stop |

The vehicle-history endpoint requires `start_time` and `end_time` parameters. It also supports pagination through `limit` and `offset`.

Example PowerShell verification:

```powershell
$base = 'http://127.0.0.1:5000'

Invoke-RestMethod "$base/api/routes"

(Invoke-RestMethod "$base/api/stops").Count

Invoke-RestMethod "$base/api/routes/G10/performance"

$history = Invoke-RestMethod "$base/api/routes/G10/vehicle-positions" -Method Get -Body @{
    start_time = '2026-09-26T09:00:00+09:30'
    end_time   = '2026-09-26T11:00:00+09:30'
    limit      = 3
    offset     = 0
}

$history.positions | Format-Table vehicle_id,trip_id,latitude,longitude,timestamp

$geometry = Invoke-RestMethod "$base/api/routes/G10/map-data"

$geometry.geometry.features.Count
```

Expected demo records:

| Route | Vehicle Positions | Retained Updates | Shape Variants |
|---|---:|---:|---:|
| G10 | 741 | 10,743 | 3 |
| M44 | 793 | 7,319 | 3 |
| 506 | 258 | 4,194 | 2 |
| **Total** | **1,792** | **22,256** | **8** |

**Data interpretation:** Retained Trip Update observations are not equivalent to unique completed bus services. The existing "Services analysed" label should be corrected before presenting these counts as service-level statistics.

The derived `actual_arrival` value represents a predicted arrival time, not an independently measured actual arrival.

## 6. Recommended Demo Workflow

Suggested total duration: **8–10 minutes**.

| Order | Demonstration | Approximate Duration |
|---|---|---|
| 1 | Introduce the project and identify the recorded data window | 30 seconds |
| 2 | Show the existing map, stops and route selection | 1–2 minutes |
| 3 | Demonstrate route statistics and historical database queries | 2 minutes |
| 4 | Explain the GTFS collection and historical storage workflow | 2 minutes |
| 5 | Show storage optimisation and testing evidence | 1 minute |
| 6 | Demonstrate available geometry or vehicle-history API results | 1 minute |
| 7 | Summarise current limitations and next steps | 1 minute |

Use only features that have been verified on the final demonstration environment.

If graphical historical playback is unavailable, show the verified backend APIs and recorded-data queries instead.

Do not present unimplemented features as completed.

## 7. Testing and Technical Evidence

The following results are supported by previous project validation.

| Validation | Result |
|---|---|
| SCRUM-231 — GTFS ID consistency | All checked stored route, trip and stop IDs matched static GTFS version 1692 |
| SCRUM-233 — Recorded demo dataset | Reproducible 3.68 MiB SQLite dataset |
| SCRUM-232 — Route geometry | 8 official shape variants; 3,529 points |
| SCRUM-234 — E2E integration | 245 tests passed |
| SCRUM-235 — Focused rehearsal tests | 14 tests passed |
| Historical collection reliability | 360 simulated cycles; 340 successful |
| SQLite integrity | Verified successfully |
| Full historical storage replay | 81.62% size reduction |

The storage optimisation result was measured using a controlled replay:

- Original database: 5.590 GiB
- Optimised database: 1.028 GiB
- Reduction: 81.62%

This is a verified replay benchmark, **not yet a confirmed long-running CASR production storage result**.

Detailed evidence is available in:

- `docs/architecture/historical-storage-optimisation.md`
- `docs/architecture/historical-collection-reliability.md`
- `docs/integration/gtfs-id-consistency.md`
- `docs/integration/recorded-demo-dataset.md`
- `docs/integration/recorded-demo-map-data.md`
- `docs/integration/e2e-demo-validation.md`

## 8. Offline Fallback

The project includes a verified backend fallback for cases where the browser application or external map resources are unavailable.

Run from the repository root using a prepared Python environment:

```powershell
& .\.venv\Scripts\python.exe -m backend.services.e2e_demo_check --database ".\data\demo\adelaide_metro_demo.db" --map-data ".\data\demo_map_data"
```

The fallback can verify:

- Recorded historical data
- Route and stop queries
- Historical vehicle positions
- Trip Update and delay records
- Official route geometry
- API response compatibility

It does not require:

- Live Adelaide Metro API access
- The CASR Windows computer
- A running frontend server
- External map tiles
- An active Flask server

This fallback provides technical evidence through repository queries and API test-client checks. It is not a graphical historical playback application.

## 9. Known Risks and Limitations

| Risk / Limitation | Recommended Action |
|---|---|
| Missing demo database or map files | Download the required files from the shared OneDrive folder |
| Missing Python dependencies | Prepare the virtual environment and install requirements before the meeting |
| Incorrect database configuration | Check `ADELAIDE_METRO_DATABASE_PATH` |
| Missing map-data configuration | Check `ADELAIDE_METRO_DEMO_MAP_DATA_PATH` |
| Backend port conflict | Verify port 5000 is available |
| Frontend port conflict | Verify port 8000 is available |
| Leaflet CDN or map tiles unavailable | Switch to offline backend fallback |
| Route geometry not displayed in browser | Verify frontend integration; otherwise demonstrate map-data API |
| Historical playback unavailable | Show recorded vehicle-history API and explain the current development status |
| Missing recorded-data banner | Clearly identify the September dataset during the demonstration |
| Misleading service counts | Describe values as retained prediction observations |
| CASR automatic restart unconfirmed | Request deployment logs and scheduled restart confirmation |
| Production storage growth unverified | Validate a recent CASR v2 database backup |

The original historical database, the production collector and the demo source database must not be modified during the demonstration.

## 10. Final Team Checklist

- [ ] Confirm the CASR meeting time and presenters.
- [ ] Confirm the computer used for screen sharing.
- [ ] Pull the latest reviewed GitHub `main`.
- [ ] Download the demo database and map-data files from OneDrive.
- [ ] Check file placement and database accessibility.
- [ ] Verify Python dependencies.
- [ ] Start the backend and frontend.
- [ ] Verify G10, M44 and 506 route selection.
- [ ] Check that stops and route statistics display correctly.
- [ ] Verify the required API requests.
- [ ] Confirm whether newer frontend features are ready and tested.
- [ ] Clearly identify the data as recorded September 2026 observations.
- [ ] Run the offline fallback before the meeting.
- [ ] Test the application using the presentation computer and network.
- [ ] Confirm which team member handles each section.
- [ ] Complete a short team rehearsal.
- [ ] Prepare a backup demonstration in case of network or browser issues.
- [ ] Record CASR feedback and requested changes.
- [ ] Stop temporary backend/frontend servers after the demonstration.

## 11. Next Steps

After the progress demonstration, the team should prioritise:

1. Completing and validating the remaining frontend integration.
2. Improving recorded-data labelling and statistical terminology.
3. Reviewing client feedback and updating the Jira backlog.
4. Obtaining and validating the latest CASR v2 database backup.
5. Confirming the collector's automatic restart configuration.
6. Preparing the next deployment update containing the reliability improvements.
7. Updating final integration, operation and handover documentation.

**Document scope:** This is a shared technical demonstration guide. It describes verified project functionality, setup requirements and remaining integration tasks. It does not represent final CASR acceptance or production certification.
