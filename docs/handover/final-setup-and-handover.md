
# Adelaide Metro Transport Analysis — Final Setup and Handover Guide

**Project:** Adelaide Metro Transport Analysis  
**Client:** Centre for Automotive Safety Research (CASR)  
**Team:** UG-S2-15  
**Last Updated:** 6 November 2026  
**Status:** Final integration testing in progress

## 1. Project Overview

This project provides a web-based platform for exploring Adelaide Metro transport data.

The system integrates a Flask backend, SQLite historical data, and a Leaflet-based interactive map.

The main features include:

- City-wide bus routes and stops
- Route and stop performance statistics
- Historical delay hotspots
- Network-wide predicted delay visualisation
- Historical vehicle playback
- Nearest-stop search

The website is intended to support CASR researchers in exploring historical public transport performance and identifying potential delay patterns.

The application is a historical analysis tool, not a live vehicle-tracking service.

## 2. System Requirements

- Python 3.12
- Git
- A modern web browser
- Internet connection for the map baselayer
- Project source code from GitHub
- Required historical and static GTFS data files

The verified development environment used Python 3.12.2 on Windows.

## 3. Installation

Clone the project repository or download the final source code.

Open PowerShell in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

The installation must complete without unresolved dependency errors.

## 4. Required Data

The project uses three main data sources.

| Dataset | Purpose |
|---|---|
| GTFS Static 1710 | City-wide routes, stops and route geometry |
| CASR v2 historical database | Historical trip updates and vehicle positions |
| Recorded three-route demo | Fallback demonstration and existing playback workflow |

### 4.1 GTFS Static Network

The verified GTFS Static 1710 publication was prepared into a static map catalog.

It contains:

- 384 routes
- 7,241 stops or locations
- 1,148 route shapes

The source GTFS archive and prepared static map catalog must be available for reproducing the city-wide network.

### 4.2 CASR v2 Historical Database

The verified historical database is:

`adelaide_metro_history_v2_20261022_140923.db`

It contains approximately 7.54 million trip-update records and 3.69 million vehicle-position records.

The original database passed a read-only SQLite integrity check.

The database should be preserved unchanged and must not be automatically upgraded or committed to GitHub.

### 4.3 Recorded Demo Dataset

The original demonstration dataset contains recorded historical data for routes G10, M44 and 506.

The following files are required for the existing demo environment:

```text
data/demo/adelaide_metro_demo.db
data/demo/adelaide_metro_demo.manifest.json
data/demo_map_data/route-shapes.geojson
data/demo_map_data/stops.geojson
data/demo_map_data/trip-map.json
data/demo_map_data/manifest.json
```

These files must be obtained through the team's approved data-sharing location if they are not included in the repository.

Do not replace the recorded demo database with CASR v2 without verifying endpoint compatibility.

## 5. Running the Application

The commands below describe the verified local development configurations.

### 5.1 Original Recorded Demo

Open PowerShell in the project root and activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Configure the recorded demo files:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = (Resolve-Path ".\data\demo\adelaide_metro_demo.db").Path
$env:ADELAIDE_METRO_DEMO_MAP_DATA_PATH = (Resolve-Path ".\data\demo_map_data").Path
```

Start the Flask backend:

```powershell
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5001
```

Open another PowerShell terminal in the project root and start the frontend server:

```powershell
python -m http.server 8000
```

Open the original frontend:

`http://127.0.0.1:8000/frontend/`

The original frontend configuration must point to the corresponding backend port.

### 5.2 CASR v2 Historical Analysis Environment

The following paths were used during local verification and must be replaced with the actual file locations on another computer.

Open PowerShell in the project root:

```powershell
.\.venv\Scripts\Activate.ps1
```

Set the CASR v2 historical database path:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = "D:\ICT Capstone\adelaide_metro_history_v2_20261022_140923.db"
```

Set the prepared GTFS static catalog path:

```powershell
$env:ADELAIDE_METRO_STATIC_MAP_DATA_PATH = "D:\ICT Capstone\static-map-1710"
```

Set the existing demo map-data path:

```powershell
$env:ADELAIDE_METRO_DEMO_MAP_DATA_PATH = (Resolve-Path ".\data\demo_map_data").Path
```

Start the backend:

```powershell
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5002
```

The CASR v2 frontend integration was verified using a separate local frontend copy configured with:

```javascript
const API_BASE_URL = "http://127.0.0.1:5002";
```

The test frontend was served using:

```powershell
python -m http.server 8001
```

Verified test URL:

`http://127.0.0.1:8001/frontend-casr-test/`

**Important:** `frontend-casr-test` was an isolated local testing copy. It is not automatically included in the final repository.

For final deployment, configure the repository frontend to use the intended backend address and confirm that the configuration works before handover.

## 6. Verified Functionality

Sprint 5 integration testing confirmed the following functions:

| Feature | Status |
|---|---|
| City-wide static map | PASS |
| Route and stop selection | PASS |
| Route and stop performance | PASS |
| Network-wide historical prediction delays | PASS |
| Historical delay hotspots | PASS |
| Nearest stop from map selection | PASS |
| Route switching | PASS |
| CASR v2 historical vehicle playback | Pending fix |

The complete automated regression suite passed 397 tests on 6 November 2026 using an isolated temporary SQLite database.

These results were recorded before the outstanding historical playback compatibility fix.

For details, see:

`docs/testing/sprint5-final-integration-test-report.md`

## 7. Known Limitations and Risks

### Historical Vehicle Playback

The CASR v2 database contains historical vehicle-position records but has an empty `routes` dimension table.

The current vehicle-history endpoint validates route existence against that table and returns HTTP 404.

A backend compatibility fix and final browser retest are required.

The original recorded demo can be retained as a fallback for historical playback.

### Historical Data Coverage

The static GTFS publication and the CASR v2 historical database do not have identical route and stop coverage.

Not every static route or stop has recorded historical observations.

### Data Interpretation

- Historical predicted delays are not confirmed actual arrival delays.
- Vehicle-position records are historical, not live tracking.
- Missing data must not be interpreted as zero delay.
- Insufficient observations must be distinguished from unavailable data.
- Large historical queries may exceed backend processing limits.

### Data Sharing

Large database and generated data files should not be committed to GitHub.

The team must confirm the approved dataset-sharing location and access permissions before distributing CASR-provided historical data.

## 8. Automated Testing

From the project root, activate the virtual environment and configure a fresh temporary test database:

```powershell
.\.venv\Scripts\Activate.ps1

$env:ADELAIDE_METRO_DATABASE_PATH = Join-Path $env:TEMP ("adelaide-metro-test-" + [guid]::NewGuid().ToString("N") + ".db")

python -m pytest -q
```

The pre-fix regression test on 6 November 2026 reported:

**397 passed in 74.89 seconds.**

Tests must be rerun after final code changes are merged.

Do not use the original CASR historical database as the test initialization database.

## 9. Final Handover Checklist

- [x] Verify the recorded demo database integrity.
- [x] Verify CASR v2 historical database integrity.
- [x] Verify the city-wide static network.
- [x] Test historical delay analysis and hotspots.
- [x] Test main frontend map interactions.
- [x] Complete pre-fix automated regression testing.
- [ ] Fix and verify CASR v2 historical vehicle playback.
- [ ] Rerun regression tests after the final merge.
- [ ] Confirm final GitHub commit.
- [ ] Confirm approved access to all required datasets.
- [ ] Verify final setup instructions on another computer.
- [ ] Deliver the final source code, setup guide, testing evidence and known limitations.

## 10. Handover Notes

The final deliverables should include:

- GitHub source code
- Installation and configuration instructions
- Approved access to the required datasets
- Updated system and module design documentation
- Final integration test report and evidence
- Known limitations and remaining work

The repository and associated datasets should enable CASR to reproduce the verified functions without relying on undocumented local settings.

Final acceptance remains subject to completion of the outstanding compatibility and regression checks.
