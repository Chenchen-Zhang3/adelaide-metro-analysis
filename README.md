
# Adelaide Metro Transport Analysis

**Client:** Centre for Automotive Safety Research (CASR)  
**Project Team:** University of Adelaide — UG-S2-15  
**Final Presentation:** 9 November 2026  
**Last Updated:** 7 November 2026

## 1. Project Overview

Adelaide Metro Transport Analysis is a web-based research platform developed for the Centre for Automotive Safety Research (CASR).

The platform combines Adelaide Metro GTFS Static data, historical GTFS-Realtime records, a Python Flask backend, SQLite database storage, and an interactive Leaflet map.

It enables researchers to explore Adelaide's public transport network, investigate historical delays, compare service performance, and examine recorded vehicle movements through a single website.

**Important:** This is a historical transport analysis platform, not a live vehicle-tracking service.

## 2. Key Features

### City-wide Network Visualisation
- Explore Adelaide Metro bus routes and stops.
- View route geometry and stop information.
- Navigate an interactive city-wide map.

### Route and Stop Performance
- Examine historical delay statistics.
- Compare route and stop performance.
- Review predicted delays and punctuality information.

### Network-wide Predicted Delays
- Visualise historical predicted delays across stops.
- Distinguish available data, insufficient data, and missing data.
- Explore recorded delay patterns geographically.

### Historical Delay Hotspots
- Identify locations with significant historical delays.
- Explore ranked hotspots and their corresponding map markers.
- Review available delay statistics for selected locations.

### Historical Vehicle Playback
- Select a route and historical time period.
- Load recorded vehicle-position observations.
- Examine vehicle movements using playback controls.

### Nearest-stop Search
- Select a location on the map.
- Find a nearby Adelaide Metro stop.
- View the estimated straight-line distance.

## 3. System Requirements

The final integration environment was verified using:

- Windows with PowerShell
- Python 3.12.2
- Git (optional when downloading the repository as a ZIP)
- A modern web browser
- Internet access for map tiles and online resources
- Access to the required GTFS Static and CASR historical datasets

The application uses:

| Component | Technology |
|---|---|
| Backend | Python, Flask |
| Historical Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Interactive Map | Leaflet, OpenStreetMap |
| Data Sources | GTFS Static and GTFS-Realtime |
| Automated Testing | pytest |

## 4. Quick Start — Final CASR v2 Website

**For complete installation and usage instructions, see the [Installation and User Guide](docs/handover/final-setup-and-handover.md).**

**Guide location in this repository:**

`docs/handover/final-setup-and-handover.md`

### Step 1 — Download the Source Code

Download the latest `main` branch from GitHub using:

**Code → Download ZIP**

Extract the ZIP and open the project folder in VS Code or PowerShell.

Alternatively, clone the repository using its GitHub URL.

All commands below should be executed from the project root directory.

### Step 2 — Install Python Dependencies

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```powershell
python -m pip install -r requirements.txt
python -m pip check
```

### Step 3 — Obtain the Required Data

The final website uses the following datasets:

| File or Folder | Purpose | Required |
|---|---|---|
| `static-map-1710/` | Prepared city-wide route and stop data | Yes |
| `adelaide_metro_history_v2_20261022_140923.db` | Historical predictions, delays, and vehicle positions | Yes, for historical functions |
| `official-static-1710.zip` | Original GTFS Static source data | Optional for running the prepared catalog |

The prepared static map folder contains:

```text
static-map-1710/
├── calendars.json
├── catalog.json
└── manifest.json
```

These files are not distributed through GitHub.

Obtain the approved datasets from the authorised CASR or project data-sharing location. The team has prepared a OneDrive folder named **Final presentation**, subject to the applicable data-sharing permissions.

For example, download the datasets to:

```text
C:\AdelaideMetroData\
├── static-map-1710\
│   ├── calendars.json
│   ├── catalog.json
│   └── manifest.json
├── adelaide_metro_history_v2_20261022_140923.db
└── official-static-1710.zip
```

The prepared static catalog contains:

- 384 routes
- 7,241 stops or locations
- 1,148 route shapes

The CASR v2 historical database contains approximately:

- 7.54 million historical trip-update records
- 3.69 million vehicle-position observations

**Do not upload client-provided historical datasets to a public GitHub repository.**

### Step 4 — Configure the Backend Data Paths

Open the first PowerShell terminal in the project root.

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Configure the historical database:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = "C:\AdelaideMetroData\adelaide_metro_history_v2_20261022_140923.db"
```

Configure the prepared static map directory:

```powershell
$env:ADELAIDE_METRO_STATIC_MAP_DATA_PATH = "C:\AdelaideMetroData\static-map-1710"
```

Replace the example paths with the actual locations of the downloaded data on your computer.

### Step 5 — Start the Flask Backend

In the same terminal:

```powershell
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5001
```

Backend address:

http://127.0.0.1:5001

Keep this terminal open.

### Step 6 — Start the Frontend

Open a second PowerShell terminal in the project root.

Run:

```powershell
python -m http.server 8000
```

Open the website in your browser:

**http://127.0.0.1:8000/frontend/**

The repository frontend is configured to connect to the backend on port `5001`.

Both terminals must remain running while using the application.

**There is no need to create a separate `frontend-casr-test` folder when following this configuration.**

### Step 7 — Verify the Application

After opening the website:

1. Confirm that the city-wide network map loads.
2. Select a route and view its associated stops.
3. Examine route and stop performance statistics.
4. Explore historical delay hotspots.
5. View network-wide predicted delays.
6. Load historical vehicle-position playback.

A historical playback example verified during final integration testing was:

| Setting | Value |
|---|---|
| Route | 100 |
| Date | 17 October 2026 |
| Start Time | 09:00 |
| End Time | 09:30 |
| Time Zone | Australia/Adelaide |

The verified local database returned four recorded observations for one vehicle, and playback progression was confirmed.

Other routes and time periods may have no recorded observations.

## 5. Automated Testing

Automated testing is optional for users running the website but is recommended for developers validating changes.

The `requirements.txt` file contains the runtime dependencies. Install `pytest` separately when running automated tests:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install pytest
```

### Run the Regression Test Suite

Tests must use an isolated temporary SQLite database rather than the original CASR historical database.

In a separate PowerShell terminal:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = Join-Path $env:TEMP ("adelaide-metro-test-" + [guid]::NewGuid().ToString("N") + ".db")

python -m pytest -q
```

**Latest verified regression result:**

| Item | Result |
|---|---|
| Date | 7 November 2026 |
| Command | `python -m pytest -q` |
| Tests Passed | 415 |
| Execution Time | 96.27 seconds |
| Status | PASS |

Test results may vary with code changes and local environment conditions.

**Important:** After testing, restore `ADELAIDE_METRO_DATABASE_PATH` to the intended CASR v2 database before restarting the website.

For detailed testing evidence, see:

[Final Integration Test Report](docs/testing/sprint5-final-integration-test-report.md)

## 6. Project Structure

```text
adelaide-metro-analysis/
├── backend/
│   ├── analysis/
│   ├── database/
│   ├── parsers/
│   ├── realtime/
│   ├── services/
│   └── tests/
│
├── frontend/
│   ├── components/
│   ├── css/
│   ├── js/
│   ├── map/
│   ├── pages/
│   └── index.html
│
├── shared/
│   ├── constants/
│   ├── schemas/
│   └── types/
│
├── tests/
├── scripts/
├── docs/
├── requirements.txt
└── README.md
```

The source code is maintained in the project GitHub repository. Large historical datasets and generated static catalogs are stored separately.

## 7. Documentation

The following documents are available in the GitHub repository.

### Installation and Client Usage

**[Installation and User Guide](docs/handover/final-setup-and-handover.md)**

Path: `docs/handover/final-setup-and-handover.md`

Provides the complete installation process, data configuration, website usage instructions, troubleshooting, and known limitations.

### Testing and Verification

**[Sprint 5 Final Integration Test Report](docs/testing/sprint5-final-integration-test-report.md)**

Path: `docs/testing/sprint5-final-integration-test-report.md`

Documents verified functionality, backend testing, browser testing, regression results, and remaining verification limitations.

### Data Collection and Access

**[CASR GTFS Collection and Data Access Guide](docs/handover/casr-gtfs-data-collection-and-access.md)**

Path: `docs/handover/casr-gtfs-data-collection-and-access.md`

Explains GTFS collection, historical storage, access methods, and operational considerations.

### Historical Playback

**[CASR Vehicle Playback Integration](docs/integration/casr-vehicle-playback.md)**

Path: `docs/integration/casr-vehicle-playback.md`

Explains historical vehicle playback integration and backend compatibility.

### City-wide Static Map Data

**[City-wide Static Map Preparation](docs/integration/citywide-static-map-data.md)**

Path: `docs/integration/citywide-static-map-data.md`

Documents the preparation and use of the GTFS Static 1710 map catalog.

### Sprint 5 GTFS Integration

**[Sprint 5 GTFS Integration Report](docs/integration/sprint5-gtfs-integration.md)**

Path: `docs/integration/sprint5-gtfs-integration.md`

Provides information about GTFS network integration and related engineering changes.

### System and Module Design

**[Final Design Documentation Index](docs/architecture/final-design/README.md)**

Path: `docs/architecture/final-design/README.md`

Provides access to the final design documentation directory, including module-level design documents.

Some design documents may still be undergoing final integration.

### Historical Collector Deployment

**[Windows Historical Collector Deployment Guide](docs/deployment/windows-historical-collector.md)**

Path: `docs/deployment/windows-historical-collector.md`

Documents the separate Windows deployment process for the historical GTFS collection service.

### Archived Sprint 4 Demonstration

**[Sprint 4 Demo Setup and Risks](docs/integration/sprint4-demo-setup-and-risks.md)**

Path: `docs/integration/sprint4-demo-setup-and-risks.md`

Describes the earlier recorded demonstration using routes G10, M44, and 506.

This archived setup is not required for the final CASR v2 website.

## 8. Known Limitations

- The website supports historical analysis rather than live vehicle tracking.
- Historical predicted delays are not necessarily confirmed actual arrival delays.
- Static network coverage and historical data coverage are different.
- Not every route or stop has sufficient historical observations.
- Missing observations must not be interpreted as zero-minute delay.
- Playback displays recorded positions rather than the exact continuous paths travelled.
- Some large historical queries may exceed backend processing limits.
- Nearest-stop distances are straight-line estimates rather than walking-route distances.
- Online map tiles require internet access or cached resources.
- Browser geolocation requires the appropriate permissions.
- Playback Reset, route switching during active playback, and individual No Data marker popups were not independently confirmed in the final browser check.
- A local CASR v2 database copy passed SQLite integrity validation; this does not establish the reliability of all production backups or the continuous collector.

## 9. Data Security and Access

Client-provided historical datasets must be handled according to CASR's approved access and sharing arrangements.

The repository does not include large historical database files or the prepared GTFS Static catalog.

Researchers must obtain the required data from an authorised source before using the historical analysis functions.

Do not commit restricted datasets, credentials, or private configuration information to a public repository.

For installation, configuration, and troubleshooting, refer to the **[Installation and User Guide](docs/handover/final-setup-and-handover.md)**.
