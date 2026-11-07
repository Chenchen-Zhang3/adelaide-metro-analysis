
# Adelaide Metro Transport Analysis — Installation and User Guide

**Client:** Centre for Automotive Safety Research (CASR)  
**Developed by:** University of Adelaide Capstone Team UG-S2-15  
**Last Updated:** 7 November 2026

## 1. Overview

Adelaide Metro Transport Analysis is a web-based research application developed for CASR.

The platform allows researchers to explore Adelaide Metro's city-wide transport network and analyse historical transport performance using a Flask backend, SQLite historical database, and an interactive Leaflet map.

### Main Features

- City-wide bus route and stop visualisation
- Historical route and stop performance analysis
- Network-wide predicted delay visualisation
- Historical delay hotspots
- Historical vehicle-position playback
- Nearest-stop search

The application supports historical transport research rather than live vehicle tracking.

Historical data availability depends on the routes, stops, and periods recorded in the supplied database.

## 2. System Requirements

The verified installation environment includes:

- Windows operating system
- PowerShell
- Python 3.12
- Git (optional when downloading the repository ZIP)
- A modern web browser
- Internet access for map resources
- Adelaide Metro source code
- Authorised access to the required datasets

Python 3.12.2 was used during final integration testing.

Commands in this guide are intended for Windows PowerShell.

## 3. Download the Project

Open the project's GitHub repository.

Select:

**Code → Download ZIP**

Extract the downloaded repository and open the project folder in VS Code.

Alternatively, clone the repository using its GitHub URL.

The project root is the directory containing:

```text
backend/
frontend/
docs/
requirements.txt
README.md
```

Open a PowerShell terminal in this directory before running the following commands.

## 4. Install Dependencies

### 4.1 Create a Virtual Environment

```powershell
python -m venv .venv
```

### 4.2 Activate the Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, execute:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

This execution policy adjustment applies only to the current PowerShell session.

### 4.3 Install Required Packages

```powershell
python -m pip install -r requirements.txt
python -m pip check
```

The installation should finish without unresolved dependency errors.

## 5. Required Data Files

The website requires prepared GTFS Static information and historical data.

The final project datasets are:

| File | Purpose | Requirement |
|---|---|---|
| `static-map-1710/` | City-wide network and map data | Required |
| `adelaide_metro_history_v2_20261022_140923.db` | Historical predictions and vehicle positions | Required for historical analysis |
| `official-static-1710.zip` | Original static GTFS archive | Optional for normal use |

These datasets are distributed separately from GitHub through an approved project or CASR data-sharing location.

An authorised OneDrive folder named **Final presentation** was prepared for the project.

### 5.1 Static Map Data

The `static-map-1710` directory must contain:

```text
static-map-1710/
├── calendars.json
├── catalog.json
└── manifest.json
```

The verified static catalog includes:

- 384 routes
- 7,241 stops or locations
- 1,148 route shapes

The prepared catalog is used to load routes and stops for the city-wide map.

The original `official-static-1710.zip` is useful for data provenance or regenerating the catalog but does not need to be extracted for the prepared final website.

### 5.2 Historical Database

The final integration environment uses:

`adelaide_metro_history_v2_20261022_140923.db`

The database contains approximately:

- 7.54 million historical trip-update records
- 3.69 million recorded vehicle-position observations

The verified local database copy passed a read-only SQLite integrity check.

Historical predictions and recorded positions provide the information used by performance analysis, hotspots, and historical playback.

The database should be kept unchanged and must not be committed to GitHub.

### 5.3 Example Data Directory

After downloading the datasets, place them in a suitable local directory.

For example:

```text
C:\AdelaideMetroData\
├── static-map-1710\
│   ├── calendars.json
│   ├── catalog.json
│   └── manifest.json
├── adelaide_metro_history_v2_20261022_140923.db
└── official-static-1710.zip
```

The exact directory location can be different on each computer.

The paths configured in the next section must match the actual locations.

## 6. Configure the Application

### 6.1 Open the Backend Terminal

Open PowerShell in the project root.

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 6.2 Configure the Historical Database

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = "C:\AdelaideMetroData\adelaide_metro_history_v2_20261022_140923.db"
```

Replace the example path with the actual location of the downloaded database.

### 6.3 Configure the Static Map Directory

```powershell
$env:ADELAIDE_METRO_STATIC_MAP_DATA_PATH = "C:\AdelaideMetroData\static-map-1710"
```

The path must point to the folder containing `catalog.json`, `calendars.json`, and `manifest.json`.

These environment variables apply to the current PowerShell session.

If the backend is started in another terminal, the variables must be configured again.

## 7. Start the Website

### 7.1 Start the Backend

In the configured PowerShell terminal, run:

```powershell
python -m flask --app backend.api.app run --host 127.0.0.1 --port 5001
```

The backend address is:

http://127.0.0.1:5001

Leave the terminal running.

### 7.2 Start the Frontend

Open a second PowerShell terminal in the project root.

Run:

```powershell
python -m http.server 8000
```

The frontend address is:

http://127.0.0.1:8000/frontend/

Open this address in a modern web browser.

Both terminal windows must remain open while using the application.

The committed frontend configuration connects to the Flask backend on port `5001`.

No separate test frontend is required for this setup.

## 8. Using the Website

### 8.1 Explore the City-wide Network

The interactive map provides an overview of Adelaide Metro routes and stops.

Users can:

1. Open the website.
2. Select a route from the available controls.
3. View the route geometry and associated stops.
4. Select a stop to view its details.

The city-wide static network can display routes and stops even when no historical records are available for a particular location.

### 8.2 Route and Stop Performance

Users can select a route or stop to examine available historical performance information.

The website provides statistics derived from historical prediction records.

These include predicted delays and punctuality information where sufficient data is available.

Historical predictions do not necessarily represent confirmed actual arrival times.

### 8.3 Network-wide Predicted Delays

The network-wide delay feature visualises historical prediction information on the map.

Users can:

1. Select an appropriate historical time period.
2. Load network-wide predicted delay information.
3. Examine the displayed stop markers and available statistics.
4. Distinguish locations with available, insufficient, or missing data.

Insufficient Data and No Data should not be interpreted as zero-minute delay.

### 8.4 Historical Delay Hotspots

The hotspot feature identifies locations with significant historical delay patterns.

Users can:

1. Open the historical delay hotspot tool.
2. Select the relevant time period or available filters.
3. Load hotspot information.
4. Review the ranked hotspot list.
5. Select hotspot markers on the map to inspect details.

Historical coverage varies by location and time period.

### 8.5 Historical Vehicle Playback

The playback feature allows researchers to review recorded vehicle-position observations.

Users can:

1. Open the historical playback controls.
2. Select a route.
3. Choose a historical date and time range.
4. Load recorded vehicle positions.
5. Use the playback controls to examine the available observations.

#### Verified Example

The following example was verified in the final browser test:

| Setting | Value |
|---|---|
| Route | 100 |
| Date | 17 October 2026 |
| Start Time | 09:00 |
| End Time | 09:30 |
| Time Zone | Australia/Adelaide |

The tested historical database returned four recorded observations for one vehicle.

Vehicle-position loading and playback timeline progression were confirmed.

Not all route and time combinations have historical observations.

Playback Reset and switching routes during active playback were not independently confirmed in the final browser verification.

### 8.6 Nearest-stop Search

The nearest-stop feature identifies a nearby stop from a selected map location.

Users can:

1. Select a location on the map.
2. Activate the nearest-stop function where available.
3. View the identified stop and estimated distance.

Distance is calculated as a straight-line estimate rather than a walking or driving route.

## 9. Troubleshooting

| Problem | Recommended Solution |
|---|---|
| Website opens but data does not load | Confirm the Flask backend is running on port `5001`. |
| Frontend cannot connect to the backend | Check the frontend URL and backend port configuration. |
| City-wide routes or stops do not display | Verify the `static-map-1710` folder path and required JSON files. |
| Historical analysis is unavailable | Check the historical `.db` path and selected time period. |
| Historical playback returns no vehicles | Try a route and time range known to contain observations. |
| Python reports missing modules | Activate the virtual environment and reinstall dependencies. |
| Map tiles do not display | Check internet connectivity and access to external map resources. |
| Port is already in use | Stop the conflicting process before restarting the relevant server. |
| Browser location cannot be accessed | Check browser and operating-system permissions. |

For further technical evidence, see the [Final Integration Test Report](../testing/sprint5-final-integration-test-report.md).

## 10. Automated Testing

Automated testing is optional for CASR researchers who only need to run the website.

Developers may use the regression suite to validate changes.

### 10.1 Install the Testing Dependency

The runtime `requirements.txt` does not include `pytest`.

Install it separately:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install pytest
```

### 10.2 Configure an Isolated Test Database

Automated tests must not run against the original CASR historical database.

Configure a fresh temporary SQLite database:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = Join-Path $env:TEMP ("adelaide-metro-test-" + [guid]::NewGuid().ToString("N") + ".db")
```

### 10.3 Run Automated Tests

```powershell
python -m pytest -q
```

The final regression test recorded on 7 November 2026 produced:

**415 passed in 96.27 seconds.**

This result reflects the tested version and environment.

Automated test success does not guarantee that every browser interaction or possible historical data selection has been verified.

After running tests, restore the CASR v2 database configuration before starting the website.

Full testing evidence is available in the [Sprint 5 Final Integration Test Report](../testing/sprint5-final-integration-test-report.md).

## 11. Known Limitations

### Historical Data Coverage

The prepared static GTFS network and CASR historical database have different coverage.

Not every route or stop has recorded historical observations.

### Historical Data Interpretation

- Predicted delays are not necessarily confirmed actual arrival delays.
- Missing data should not be treated as a zero-minute delay.
- Insufficient historical samples should be distinguished from missing observations.
- Historical vehicle positions are not live vehicle locations.

### Historical Playback

Playback displays recorded observations rather than a continuously recorded vehicle path.

The final browser test verified position loading and timeline progression.

Playback Reset and route switching during an active playback session were not independently confirmed.

### Performance and Environment

- Large historical queries may be subject to processing limits.
- Online map tiles depend on internet access or cached resources.
- Browser geolocation requires appropriate permissions.
- Some user interactions may behave differently across browsers or environments.

### Data Integrity

The verified local CASR v2 database copy passed a read-only SQLite integrity check.

This does not establish the integrity of other production backups or the long-term reliability of the production collection service.

## 12. Data Security

CASR-provided datasets must be handled according to approved access, storage, sharing, and retention arrangements.

The historical database and prepared static map data are distributed separately from the source code.

Do not upload restricted datasets, credentials, or sensitive configuration files to public GitHub repositories.

Use authorised copies of the data for local research and testing.

## 13. Related Documentation

The following documents are included in the GitHub repository.

| Document | Repository Path |
|---|---|
| [Project README](../../README.md) | `README.md` |
| [Final Integration Test Report](../testing/sprint5-final-integration-test-report.md) | `docs/testing/sprint5-final-integration-test-report.md` |
| [CASR GTFS Collection and Data Access Guide](casr-gtfs-data-collection-and-access.md) | `docs/handover/casr-gtfs-data-collection-and-access.md` |
| [CASR Vehicle Playback Integration](../integration/casr-vehicle-playback.md) | `docs/integration/casr-vehicle-playback.md` |
| [City-wide Static Map Preparation](../integration/citywide-static-map-data.md) | `docs/integration/citywide-static-map-data.md` |
| [Sprint 5 GTFS Integration](../integration/sprint5-gtfs-integration.md) | `docs/integration/sprint5-gtfs-integration.md` |
| [Final Design Documentation Index](../architecture/final-design/README.md) | `docs/architecture/final-design/README.md` |
| [Windows Historical Collector Deployment](../deployment/windows-historical-collector.md) | `docs/deployment/windows-historical-collector.md` |
| [Archived Sprint 4 Demo Setup](../integration/sprint4-demo-setup-and-risks.md) | `docs/integration/sprint4-demo-setup-and-risks.md` |

The final design documentation index provides access to the available module design files. Some design documents may still be undergoing final integration.
