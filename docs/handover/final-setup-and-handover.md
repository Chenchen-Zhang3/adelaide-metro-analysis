
Adelaide Metro Transport Analysis — Installation and User Guide
Client: Centre for Automotive Safety Research (CASR)
Developed by: University of Adelaide Capstone Team UG-S2-15
Last updated: 7 November 2026

1. Overview
Adelaide Metro Transport Analysis is a browser-based research tool for exploring Adelaide Metro's bus network and historical transport performance. It combines a Python Flask API, an SQLite historical database and an interactive map built with Leaflet.

The website provides:

A city-wide map of routes and stops
Route and stop performance summaries
Network-wide historical predicted-delay visualisation
Historical delay hotspots
Playback of recorded vehicle positions
Nearest-stop search
This is a historical analysis application, not a live bus-tracking service. The availability of historical results depends on the routes, stops and dates recorded in the supplied database.

2. System requirements
The following instructions describe the Windows environment used during final integration testing.

Windows with PowerShell
Python 3.12 (Python 3.12.2 was used for the verified development environment)
Git (if cloning the repository rather than downloading a ZIP)
An up-to-date browser
Internet access for Leaflet/OpenStreetMap resources and map tiles
Access to the project source code and the authorised CASR data files
All commands below are run in PowerShell unless otherwise stated.

3. Obtain the source code
Clone the GitHub repository using its actual URL:

git clone <REPOSITORY_URL>
cd adelaide-metro-analysis
Alternatively, download the latest source-code ZIP from GitHub, extract it, and open PowerShell in the extracted project root (the folder containing requirements.txt and frontend).

4. Install Python dependencies
From the project root, run:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
If PowerShell prevents activation, run the following command in that terminal and then retry activation:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
The execution-policy change applies to the current PowerShell process only.

5. Obtain and prepare the data
The final CASR v2 website requires two prepared data resources. A third file is retained as the original static GTFS source archive.

File or folder	Purpose	Required to run the prepared final website?
static-map-1710/	Prepared city-wide route, stop and map catalog	Yes
adelaide_metro_history_v2_20261022_140923.db	Historical trip updates, predicted delays and vehicle positions	Yes, for historical analysis features
official-static-1710.zip	Original GTFS Static 1710 source archive for provenance and regeneration	No, if the prepared catalog is already available
Obtain these files from the approved project/CASR data-sharing location. The team may provide access through its OneDrive Final presentation folder where authorised. The historical database is not included in GitHub.

Check that the prepared catalog folder contains:

static-map-1710/
    calendars.json
    catalog.json
    manifest.json
The prepared static network used for integration testing contains 384 routes, 7,241 stops or locations and 1,148 route shapes. The historical database contains approximately 7.54 million trip-update records and 3.69 million vehicle-position observations. Static network coverage does not imply equivalent historical coverage.

You may store the data anywhere accessible to your computer. For example:

C:\AdelaideMetroData\
    static-map-1710\
        calendars.json
        catalog.json
        manifest.json
    adelaide_metro_history_v2_20261022_140923.db
    official-static-1710.zip
Do not extract or regenerate the original static ZIP when the prepared static-map-1710 folder has already been supplied. Do not commit these large datasets to GitHub. Keep the original historical database unchanged; perform any experimental processing on a separate copy.

6. Configure and start the final website
6.1 Start the backend
Open a PowerShell terminal in the repository root and activate the virtual environment:

.\.venv\Scripts\Activate.ps1
Set the paths to the actual locations on your computer. The following are examples:

$env:ADELAIDE_METRO_DATABASE_PATH = "C:\AdelaideMetroData\adelaide_metro_history_v2_20261022_140923.db"
$env:ADELAIDE_METRO_STATIC_MAP_DATA_PATH = "C:\AdelaideMetroData\static-map-1710"
Then start Flask:

python -m flask --app backend.api.app run --host 127.0.0.1 --port 5001
Keep this terminal running. The backend is available locally at:

http://127.0.0.1:5001

Important: PowerShell environment variables set with $env: apply to the current terminal session. Re-enter them when opening a new backend terminal.

6.2 Start the frontend
Open a second PowerShell terminal in the repository root. Run:

python -m http.server 8000
Keep this terminal running and open:

http://127.0.0.1:8000/frontend/

The repository frontend is configured to contact the local Flask backend on port 5001. There is no need to copy the frontend to a frontend-casr-test folder or change map.js when using the ports above.

Both terminals must remain running while the website is being used. Starting the frontend alone does not start the Flask API.

7. Using the website
The site combines an interactive Adelaide Metro map with analysis controls. The available results depend on the selected route, stop and historical time window.

7.1 Explore the network
Use the route selection controls to display routes and stops. Select a stop or route to inspect its available details. The prepared static catalog supports city-wide network exploration even where no historical observations exist.

7.2 Review route and stop performance
Select a route or stop and an appropriate historical time range to view performance statistics. The interface can show predicted delays and on-time information for observations available in the connected database.

These measurements reflect the available historical prediction records and should not be interpreted as independently confirmed actual arrival times.

7.3 View predicted delays and hotspots
Use the network-wide prediction-delay view or the historical delay-hotspot feature to examine areas with recorded delay patterns. Some stops may display Insufficient Data or No Data rather than a numerical delay. These states must not be interpreted as zero delay.

7.4 Play back recorded vehicle positions
Open the historical playback controls, select a route and an available recorded time window, then load the vehicle history. Use the playback controls to inspect how recorded positions change over time.

A browser verification on 7 November 2026 successfully loaded Route 100 for 17 October 2026, 09:00–09:30 Adelaide time, displaying four recorded observations for one vehicle and progressing through the playback timeline.

This window is a reproducible example from the verified local dataset, not a guarantee that every route or date contains observations. Playback Reset and changing routes during an active playback session were not independently verified in that final check.

7.5 Find a nearby stop
Use the nearest-stop function with a selected map location where available. Reported distance is calculated as a straight-line distance and is not a walking or driving distance.

8. Troubleshooting
Problem	Suggested checks
The webpage opens but no data loads	Verify Flask is still running on port 5001. Open the browser developer console and check for failed API requests.
The frontend cannot connect to the API	Confirm the frontend URL is http://127.0.0.1:8000/frontend/ and the backend uses port 5001.
Routes or stops do not display	Check that ADELAIDE_METRO_STATIC_MAP_DATA_PATH points to the folder containing catalog.json, calendars.json and manifest.json.
Historical performance results are missing	Confirm ADELAIDE_METRO_DATABASE_PATH points to the complete .db file and select a route/date range with observations.
Historical playback shows no vehicles	Try the verified Route 100 example above; a different time range may contain no recorded positions.
Python reports a missing module	Activate .venv and reinstall the dependencies using python -m pip install -r requirements.txt.
Map tiles do not appear	Check internet access and any restrictions on external map resources.
Port 5001 or 8000 is already in use	Close the other application using that port rather than changing only one side of the website configuration.
If an issue persists, refer to the repository's technical documentation and the final integration test report.

9. Verification and testing
The final integration checks confirmed that the city-wide map, route and stop selection, performance analysis, network-wide predicted-delay visualisation, delay hotspots, nearest-stop function and historical playback loading/progression worked in the tested environment.

The automated regression run on 7 November 2026 completed with 415 tests passed in 96.27 seconds. Automated tests do not guarantee that every browser interaction or every possible historical data selection has been verified.

Developers can run the test suite against a separate temporary database. Do not run tests against the original CASR historical database. In a new PowerShell terminal at the project root:

.\.venv\Scripts\Activate.ps1
$env:ADELAIDE_METRO_DATABASE_PATH = Join-Path $env:TEMP ("adelaide-metro-test-" + [guid]::NewGuid().ToString("N") + ".db")
python -m pytest -q
Further details: docs/testing/sprint5-final-integration-test-report.md.

10. Data interpretation, limitations and privacy
The website analyses historical records and does not show live vehicle locations.
Predicted delays are not necessarily confirmed actual arrival delays.
The GTFS Static 1710 network and CASR v2 historical database have different coverage; not all routes or stops have historical observations.
Limited sample counts, missing data and unavailable observations should be interpreted separately.
Playback displays recorded observations; it does not establish the exact path taken between observations.
Large historical queries may be constrained by backend processing limits.
Basemap resources require internet connectivity or an available cache.
Browser geolocation, where used, requires the relevant permissions.
Playback Reset and route switching during active playback, and an individual No Data marker/popup, were not independently confirmed in the final browser verification.
The validated local CASR v2 database copy passed a read-only SQLite integrity check. This does not establish the integrity or reliability of every production backup or the long-term collection system.
Access to CASR-provided data must follow the client's approved sharing and retention arrangements. Avoid publishing historical database files in a public repository.
11. Additional documentation
Project README — project overview and quick-start instructions
Final Integration Test Report — verification evidence and remaining limitations
Final Design Documentation — module and system design information
CASR GTFS Data Collection and Access — collection and historical data details
For historical Sprint 4 demonstration instructions, see docs/integration/sprint4-demo-setup-and-risks.md. That workflow uses a separate recorded three-route dataset and is not required to run the final CASR v2 website described above.

