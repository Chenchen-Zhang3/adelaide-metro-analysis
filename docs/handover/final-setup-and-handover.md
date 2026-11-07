
# Adelaide Metro Transport Analysis — Final Setup and Handover Guide

**Project:** Adelaide Metro Transport Analysis  
**Client:** Centre for Automotive Safety Research (CASR)  
**Team:** UG-S2-15  
**Last Updated:** 7 November 2026  
**Status:** Core integration verified; final handover checks pending

## 1. Project Overview

Adelaide Metro Transport Analysis is a web-based platform developed for the Centre for Automotive Safety Research (CASR).

The system combines a Python Flask backend, SQLite historical data, and an interactive Leaflet map to help researchers explore Adelaide Metro transport information.

The main features include:

- City-wide bus route and stop visualisation
- Route and stop performance statistics
- Historical delay hotspots
- Network-wide predicted delay visualisation
- Historical vehicle-position playback
- Nearest-stop search

The application supports historical transport analysis rather than live vehicle tracking.

## 2. System Requirements

- Python 3.12
- Git
- A modern web browser
- Internet connection for the map baselayer
- Project source code
- Required historical and static GTFS data files

The verified development environment used Python 3.12.2 on Windows.

## 3. Installation

Clone the project repository or download the final source code.

Open PowerShell in the project root and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

The installation should complete without unresolved dependency errors.

## 4. Required Data

The project uses three main data sources.

| Dataset | Purpose |
|---|---|
| GTFS Static 1710 | City-wide routes, stops and route geometry |
| CASR v2 historical database | Historical trip updates and vehicle positions |
| Recorded three-route demo | Reproducible demonstration and fallback |

### 4.1 GTFS Static Network

The verified GTFS Static 1710 publication was prepared into a static map catalog.

The prepared network contains:

- 384 routes
- 7,241 stops or locations
- 1,148 route shapes

The original GTFS archive and prepared static map catalog must be available to reproduce the city-wide network.

### 4.2 CASR v2 Historical Database

The historical database used for final integration testing is:

`adelaide_metro_history_v2_20261022_140923.db`

It contains approximately:

- 7.54 million historical trip-update records
- 3.69 million recorded vehicle-position observations

The database passed a read-only SQLite integrity check.

The original database must be preserved without modification. It should not be automatically upgraded or committed to GitHub.

### 4.3 Recorded Demo Dataset

The original recorded demonstration dataset covers routes G10, M44 and 506.

The following six files are required for the existing demonstration workflow:

```text
data/demo/adelaide_metro_demo.db
data/demo/adelaide_metro_demo.manifest.json
data/demo_map_data/route-shapes.geojson
data/demo_map_data/stops.geojson
data/demo_map_data/trip-map.json
data/demo_map_data/manifest.json
```

These files must be obtained through the team's approved data-sharing location if they are not included in the repository.

The recorded demo dataset should remain available separately from the CASR v2 historical database.

## 5. Running the Application

The following instructions describe the verified local development configurations.

The file paths are examples from the integration testing environment and must be adjusted on another computer.

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

Open a second PowerShell terminal in the project root and start the frontend server:

```powershell
python -m http.server 8000
```

Open:

`http://127.0.0.1:8000/frontend/`

The original frontend configuration must point to the backend on port 5001.

### 5.2 CASR v2 Historical Analysis Environment

This configuration was used to verify the real historical dataset without replacing the original demo environment.

Open PowerShell in the project root:

```powershell
.\.venv\Scripts\Activate.ps1
```

Configure the CASR v2 historical database:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = "D:\ICT Capstone\adelaide_metro_history_v2_20261022_140923.db"
```

Configure the prepared GTFS Static 1710 catalog:

```powershell
$env:ADELAIDE_METRO_STATIC_MAP_DATA_PATH = "D:\ICT Capstone\static-map-1710"
```

Configure the existing demo map data:

```powershell
$env:ADELAIDE_METRO_DEMO_MAP_DATA_PATH = (Resolve-Path ".\data\demo_map_data").Path
```

Start the CASR v2 backend:

```powershell
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5002
```

For local CASR v2 browser testing, a separate copy of the frontend was used.

The test frontend's `frontend-casr-test/js/map.js` file was configured with:

```javascript
const API_BASE_URL = "http://127.0.0.1:5002";
```

The testing copy can be created from the current frontend using PowerShell:

```powershell
Copy-Item ".\frontend" ".\frontend-casr-test" -Recurse -Force

$path = ".\frontend-casr-test\js\map.js"
$content = Get-Content $path -Raw

$content = $content.Replace(
    'const API_BASE_URL = "http://127.0.0.1:5001";',
    'const API_BASE_URL = "http://127.0.0.1:5002";'
)

Set-Content $path $content -Encoding UTF8
```

If the testing copy already exists, refresh its files from the latest repository frontend before testing to avoid using outdated JavaScript.

Open another PowerShell terminal in the project root:

```powershell
python -m http.server 8001
```

Open:

`http://127.0.0.1:8001/frontend-casr-test/`

Refresh the browser after updating frontend files.

**Important:** `frontend-casr-test` is a local integration testing copy and is not part of the final GitHub source code by default.

For final deployment, the repository frontend must be configured to use the intended backend URL. The recipient should not be required to reproduce undocumented local testing changes.

## 6. Verified Functionality

Sprint 5 integration testing verified the following features:

| Feature | Status |
|---|---|
| City-wide static map | PASS |
| Route and stop selection | PASS |
| Route and stop performance | PASS |
| Network-wide historical prediction delays | PASS |
| Historical delay hotspots | PASS |
| Nearest stop from map selection | PASS |
| Route switching and performance updates | PASS |
| CASR v2 historical vehicle playback loading | PASS |
| Historical playback progression | PASS |
| Playback Reset and route switching | Pending separate confirmation |
| Individual No Data marker and popup | Pending separate confirmation |

### Historical Vehicle Playback Verification

The initial CASR v2 playback test returned HTTP 404 because the backend route-validation logic depended on the historical database's empty `routes` table.

This issue was corrected by updating historical route validation to support recorded vehicle-position data.

The frontend was also updated to handle `Australia/Adelaide` daylight saving time.

On 7 November 2026, the historical playback feature was tested in the browser using:

- Route 100
- 17 October 2026
- 09:00–09:30 Adelaide time

The application successfully loaded four recorded observations for one vehicle, displayed its position on the map and advanced the playback timeline.

This verified the previously blocked loading and playback progression functions.

Reset and route-switching behaviour during playback were not separately confirmed.

Detailed results are documented in:

`docs/testing/sprint5-final-integration-test-report.md`

## 7. Known Limitations and Risks

### Historical Data Coverage

The GTFS Static 1710 publication and CASR v2 historical database have different route and stop coverage.

Not every static route or stop has recorded historical observations.

A successful city-wide static map does not imply complete historical coverage for every route.

### Historical Data Interpretation

- Historical predicted delays are not confirmed actual arrival delays.
- Recorded vehicle positions are not live tracking.
- Movement between recorded observations is not estimated.
- Missing data must not be interpreted as zero-minute delay.
- Insufficient historical samples must be distinguished from unavailable observations.
- Large historical queries may exceed backend processing limits.

### Historical Playback

The previous CASR v2 HTTP 404 compatibility issue was resolved.

The application supports Australia/Adelaide daylight saving time when interpreting historical playback dates.

The tested October playback window successfully displayed recorded observations and playback progression.

Reset and route-switching behaviour should be confirmed separately before describing all playback controls as fully verified.

### Dataset Protection and Sharing

The historical database should be preserved without modification.

Large database files, generated catalogs and local testing datasets should not be committed to GitHub.

The team must confirm the approved sharing location and access permissions before distributing CASR-provided historical data.

### Reproducibility

The historical database and prepared GTFS Static 1710 catalog were stored outside the GitHub repository during final verification.

Another computer will need access to these datasets and the correct local paths.

The setup process should be tested independently before final client handover.

## 8. Automated Testing

Automated tests should use a fresh temporary SQLite database instead of the original CASR v2 historical database.

Open PowerShell in the project root:

```powershell
.\.venv\Scripts\Activate.ps1

$env:ADELAIDE_METRO_DATABASE_PATH = Join-Path $env:TEMP ("adelaide-metro-test-" + [guid]::NewGuid().ToString("N") + ".db")

python -m pytest -q
```

### Final Regression Result

**Test Date:** 7 November 2026  
**Command:** `python -m pytest -q`  
**Result:** 415 passed in 96.27 seconds  
**Status:** PASS

The complete automated regression suite passed after the backend historical playback compatibility fix and frontend integration updates.

The earlier 6 November run passed 397 tests and is retained as a pre-fix regression baseline.

Automated test success does not replace browser verification of every user interaction.

For the complete test history, see:

`docs/testing/sprint5-final-integration-test-report.md`

## 9. Final Handover Checklist

- [x] Verify the recorded demo database integrity.
- [x] Verify CASR v2 historical database integrity.
- [x] Verify the city-wide GTFS Static 1710 network.
- [x] Test historical delay analysis and hotspots.
- [x] Test route and stop performance.
- [x] Test the main interactive map functions.
- [x] Fix and verify CASR v2 historical playback loading and progression.
- [x] Complete post-fix automated regression testing (415 passed).
- [ ] Independently verify playback Reset and route-switching behaviour.
- [ ] Document the remaining No Data marker verification limitation.
- [ ] Confirm the final verified GitHub commit.
- [ ] Confirm approved access to all required datasets.
- [ ] Verify final installation and setup on another computer.
- [ ] Deliver the final source code, documentation, data access instructions and known limitations.

## 10. Handover Notes

The final handover package should include:

- GitHub repository and final source code
- Installation and environment configuration instructions
- Approved access to static GTFS and historical datasets
- Updated final system and module design documentation
- Final integration test report
- Known limitations and future improvement recommendations

The project should remain reproducible without relying on undocumented settings or files available only on an individual developer's computer.

**Current Handover Status:** Core functionality and post-fix regression verified. Final data-sharing arrangements, independent setup verification and remaining interaction checks are pending.
