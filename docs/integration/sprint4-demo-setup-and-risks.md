# Sprint 4 Demo Setup and Risks

Updated by Chenchen Zhang on 16 October 2026.

## Demo Data

The demo uses recorded Adelaide Metro data from 26 September 2026,
09:00–11:00 Adelaide time (UTC+09:30).

Routes: G10, M44 and 506.

This is historical data, not a live feed.


## Environment Setup

Chenchen's local tests used Python 3.12.2.

Open PowerShell in the project root. Create and activate a virtual environment:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Use this environment when starting the backend. If PowerShell blocks
activation, use the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then replace `python` with `.\.venv\Scripts\python.exe` in the backend
startup command below.

## Local Files

Download the Sprint 4 demo files from the team's shared OneDrive folder.
Sign in with your university Microsoft account if prompted.

The shared folder contains:

- adelaide_metro_demo.db
- adelaide_metro_demo.manifest.json
- Map data/route-shapes.geojson
- Map data/stops.geojson
- Map data/trip-map.json
- Map data/manifest.json

After downloading, copy the files into the project folders listed below.
Move the four files inside `Map data` into `data/demo_map_data`;
do not add another `Map data` folder inside it.

These files are shared separately and are not included in a GitHub pull.
OneDrive download was confirmed for the account used by Chenan.
Other members' access permissions have not been checked.

Copy the shared demo database and its manifest into:

    data/demo/adelaide_metro_demo.db
    data/demo/adelaide_metro_demo.manifest.json

Copy the four shared map files into:

    data/demo_map_data/route-shapes.geojson
    data/demo_map_data/stops.geojson
    data/demo_map_data/trip-map.json
    data/demo_map_data/manifest.json

Keep these files locally. Do not run the live collector against the demo database.

Before starting the backend, check that all six files exist:

```powershell
$demoFiles = @(
    ".\data\demo\adelaide_metro_demo.db"
    ".\data\demo\adelaide_metro_demo.manifest.json"
    ".\data\demo_map_data\route-shapes.geojson"
    ".\data\demo_map_data\stops.geojson"
    ".\data\demo_map_data\trip-map.json"
    ".\data\demo_map_data\manifest.json"
)

$demoFiles | ForEach-Object {
    [PSCustomObject]@{
        File = $_
        Exists = Test-Path -LiteralPath $_ -PathType Leaf
    }
}
```

Every row should show `True`. This checks file presence, not file integrity.

## Start the Backend

Open PowerShell in the project root and run:

    $env:ADELAIDE_METRO_DATABASE_PATH = (Resolve-Path .\data\demo\adelaide_metro_demo.db).Path
    $env:ADELAIDE_METRO_DEMO_MAP_DATA_PATH = (Resolve-Path .\data\demo_map_data).Path
    python -m flask --app backend.api.app run --host 127.0.0.1 --port 5000

Keep this terminal running. Set both paths again when starting from a new terminal.

## Start the Frontend

Open another terminal in the project root and run:

    python -m http.server 8000

Open:

    http://127.0.0.1:8000/frontend/

The backend must stay running while using the webpage.

## Backend Checks

The following checks were completed on 16 October:

- Map-data requests returned the expected shapes, stops and trips for all three routes.
- The G10 vehicle history request returned 741 positions.
- The recorded-dataset check verified all three routes.
- Unknown map route returned 404.
- Missing map files returned 503.
- The demo database hash was unchanged.

See the test report:

[Map and vehicle history test report](../testing/sprint4-map-history-integration-test-report.md)

These checks do not confirm that the new map and playback features work in the browser.

## Vehicle History Request Example

With the backend running, open another PowerShell terminal and run:

```powershell
$historyUrl = "http://127.0.0.1:5000/api/routes/G10/vehicle-positions?start_time=2026-09-26T09:00:00%2B09:30&end_time=2026-09-26T11:00:00%2B09:30&limit=200&offset=0"
$history = Invoke-RestMethod -Uri $historyUrl
$history | ConvertTo-Json -Depth 10
```

This requests G10 positions between 09:00 and 11:00 Adelaide time.
The start time is included and the end time is excluded.

The response contains up to 200 positions. If `next_offset` is not null,
use that value as the next request's `offset`. Continue until
`next_offset` is null.

The earlier complete-dataset check returned 741 G10 positions.
A single page with `limit=200` is not expected to contain all 741.

## Scoping Document Risk Review

Reviewed on 16 October against Section 3.1 of the signed scoping document.

The ratings below are from the original document. Owners are proposed
based on module responsibilities and need team confirmation.

| Original risk | Original likelihood / impact | Current position | Follow-up | Proposed owner |
| --- | --- | --- | --- | --- |
| Incomplete or incorrectly processed GTFS data affects analysis. | High / High | Recorded-data checks passed for the three demo routes. The dataset covers a limited recording window. | Document missing-data and matching limitations. Check the final demo files against their manifests. | Chenan and Lixuan |
| Incorrect punctuality logic produces misleading results. | Medium / High | The regression suite passed. Selected API and frontend results were compared earlier. | Confirm threshold boundary tests and correct the interface wording for observation counts. | Chengxi and Pritish |
| Modules do not work correctly when integrated. | Medium / High | Backend APIs and the existing browser functions were checked. Route geometry and playback remain incomplete in the frontend. | Finish integration, test the remaining workflows and record fixes. | Module owners and Chenchen |
| Collection or database failures create gaps in historical records. | Medium / High | The fixed demo database can be queried. This does not confirm continuous collection reliability. | Record known collection gaps, retain a backup and check collection failure handling. | Chenan and Lixuan |
| API access restrictions interrupt collection. | Medium / High | The recorded demo does not require new Adelaide Metro feed requests. Collector compliance was not checked in this setup verification. | Review polling, retries and back-off against the applicable API requirements. | Chenan |

These risks remain open for monitoring.

## Current Risks and Follow-up

| Risk or issue | Current position | Next action | Suggested owner |
| --- | --- | --- | --- |
| Frontend integration is unfinished | Backend map and vehicle history checks passed; browser integration is still pending | Connect the APIs and test route switching and playback | Pritish, with Chenchen testing |
| Local files or paths are missing | Map-data requests return 503 when artifacts are unavailable | Check all files and configure both paths before the demo | Chenchen |
| Map tiles or Leaflet cannot load | Local transport data does not include the basemap or Leaflet files | Check internet access and prepare backup screenshots or a recording | Pritish and Chenchen |
| Historical data could be mistaken for live data | The dataset contains September observations | Add a visible recorded-data label and date range | Pritish |
| Performance counts could be misunderstood | "Services analysed" counts retained prediction observations | Agree on the metric wording and update the interface | Chengxi and Pritish |
| Remaining features are not yet verified | Nearest-stop distance, hotspots and browser playback remain on the test list | Test each feature after it is integrated and record any problems | Feature owners and Chenchen |

The owners above are proposed coordination responsibilities, not a record of confirmed assignments.

## Before the Demo

- Start the backend and frontend from fresh terminals.
- Check that the application uses the correct demo database and map files.
- Check all three routes in the browser.
- Test the features included in the agreed demo scope.
- Check screen-sharing readability and recording.
- Keep backup screenshots or a recording available.
- Record unresolved issues rather than marking untested features as passed.

## Stop the Servers

Press Ctrl+C in the Flask terminal and in the frontend server terminal.
Both terminals should return to the PowerShell prompt.

## Independent Setup Verification

Feedback provided by Chenan Wang on 16 October 2026.

Tested commit: `24388749bf6d41d0408750f2c9a98b543fbdc615`

Result: PASS WITH ISSUES.

### What was checked

Chenan reported that the backend started after installing dependencies,
and the frontend opened successfully.

The browser displayed the basemap and 354 stops. G10, M44 and 506 could
be selected, route performance values updated, and stop 3771 could be
selected and displayed. Map-data and vehicle-history API requests also
worked. No critical browser errors were reported during those checks.

OneDrive download was confirmed manually using an authenticated university
account. All six required files were present locally, and both manifests
could be opened. SHA-256 checks were not performed on those downloaded copies.
Other members' OneDrive access has not been verified.

### Problems found

The original instructions did not include:

- Python version, virtual environment and dependency installation.
- Clear OneDrive download and local file placement instructions.
- A complete vehicle-history request.
- File checks before backend startup.

These instructions have now been added. The revised instructions have
not yet been followed by another member from start to finish.

### Remaining limitations

Route geometry, historical vehicle playback and the recorded-data banner
were reported as incomplete in the tested frontend.

The browser also relies on online or cached Leaflet and map-tile resources.

The setup result applies to the functions checked above. It does not
confirm acceptance of all project features or a fresh installation
using the revised document alone.

## Handover Checklist

- [x] Document local data paths and startup commands.
- [x] Record backend checks and regression results.
- [x] Obtain and record independent setup feedback.
- [x] Add the missing setup instructions identified in that feedback.
- [x] Review the original scoping risks.
- [ ] Confirm risk owners and follow-up actions with the team.
- [ ] Check that the README links to this setup guide.
- [ ] Check that architecture and data preparation documentation match the demo.
- [ ] Complete browser acceptance checks after frontend integration.
- [ ] Prepare backup screenshots or a recording for the demo.

## Setup Status

The tested version could be started with additional setup instructions.
The documentation has been updated to cover the gaps reported by Chenan.

Backend checks and regression results are recorded in the integration
test report. Final browser acceptance remains pending for unfinished features.