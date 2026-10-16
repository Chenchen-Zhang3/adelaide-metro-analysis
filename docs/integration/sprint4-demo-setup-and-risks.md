# Sprint 4 Demo Setup and Risks

Updated by Chenchen Zhang on 16 October 2026.

## Demo Data

The demo uses recorded Adelaide Metro data from 26 September 2026,
09:00–11:00 Adelaide time (UTC+09:30).

Routes: G10, M44 and 506.

This is historical data, not a live feed.

## Local Files

Copy the shared demo database and its manifest into:

    data/demo/adelaide_metro_demo.db
    data/demo/adelaide_metro_demo.manifest.json

Copy the four shared map files into:

    data/demo_map_data/route-shapes.geojson
    data/demo_map_data/stops.geojson
    data/demo_map_data/trip-map.json
    data/demo_map_data/manifest.json

Keep these files locally. Do not run the live collector against the demo database.

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

## Setup Status

The backend was started successfully with both local data paths on 16 October.
The complete demo setup still needs a final restart and browser check after
frontend integration.