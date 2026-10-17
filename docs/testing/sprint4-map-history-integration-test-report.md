# Sprint 4 Map and Vehicle History Test Report

## Test Details

- Tested by: Chenchen Zhang
- Date: 16 October 2026
- Commit: 4bef17094f5390106cd5f66f4c177e9c5c83e244
- Environment: Windows, Python 3.12.2
- Database: data/demo/adelaide_metro_demo.db
- Map files: data/demo_map_data/
- Data period: 26 September 2026, 09:00–11:00 Adelaide time (UTC+09:30). The end time is excluded.

## Purpose

Check that the backend can load the route map files and return historical vehicle positions from the demo database.

These tests cover the backend. They do not confirm that route shapes or vehicle playback work in the browser.

## Route Map API

I called /api/routes/<route_id>/map-data for G10, M44 and 506.

All three requests returned data. The counts matched the dataset documentation.

| Route | Shape variants | Stops | Trips |
| --- | ---: | ---: | ---: |
| G10 | 3 | 145 | 22 |
| M44 | 3 | 114 | 21 |
| 506 | 2 | 98 | 12 |

Result: PASS.

## Vehicle History API

I called /api/routes/G10/vehicle-positions with the recorded time range and a limit of 1000.

The response contained 741 positions. No further page was needed. The returned records included coordinates, route IDs and timestamps.

Result: PASS.

## Recorded Dataset Check

I ran the existing check tool from the project root:

    python -m backend.services.e2e_demo_check --database .\data\demo\adelaide_metro_demo.db --map-data .\data\demo_map_data

The tool used a temporary copy of the database. It checked the map response format and compared the paginated vehicle API results with database query results.

| Route | Shape variants | Geometry points | Vehicle records |
| --- | ---: | ---: | ---: |
| G10 | 3 | 1232 | 741 |
| M44 | 3 | 1381 | 793 |
| 506 | 2 | 916 | 258 |

The route, stop and performance requests included in the check returned HTTP 200.

The tool also checked two error cases:

| Case | Expected status | Actual status |
| --- | ---: | ---: |
| Unknown route in map-data request | 404 | 404 |
| Missing map files | 503 | 503 |

The original demo database was unchanged after the check. Its SHA-256 remained:

    735de9404b6fe46d52fe0b102004e6993815157b8f5905341afbf9cada465aa2

Result: PASS.


## Regression Tests

Command:

    python -m pytest backend/tests tests -q

Result: 245 passed, 1 warning in 47.81 seconds.

The warning came from dateutil using the deprecated
datetime.datetime.utcfromtimestamp() function. No tests failed.


## Evidence

The check output is saved here:

[Map and vehicle history check output](evidence/sprint4/map-history-check-20261016.json)

## Remaining Work

- Check route shapes in the browser after the frontend is connected to the map-data API.
- Check that switching routes removes the previous route layers.
- Test vehicle playback and time controls after frontend integration.
- Test nearest-stop distance and delay hotspots.
- Check the recorded-data label and the wording used for performance counts.
- Check how the browser handles missing map data.

The demo uses recorded September data. It should not be presented as live data. The map tiles and Leaflet files may still require an internet connection.

## Conclusion

The backend map and vehicle history checks passed for the demo dataset. Frontend testing and the remaining prototype checks are still in progress.