# Sprint 4 Browser and Backend Verification

Tester: Chenchen Zhang
Date: 17 October 2026
Commit: c25be7222ef6ae6aaa09ccfbfeb84738cd54cf44

## Scope

This check used the recorded demo database and map files for G10, M44
and 506. The recording window was 26 September 2026, 09:00–11:00
Adelaide time (UTC+09:30).

Testing took place on Windows, with the backend on port 5000 and
the frontend on port 8000.

Overall result: the checks below passed, with outstanding integration
work and interface issues recorded separately.

## Regression Tests

Command:

    python -m pytest backend/tests tests -q -rs

Result: 255 passed, 1 warning in 52.81 seconds.

The warning came from dateutil using the deprecated
datetime.utcfromtimestamp() method. No tests failed.

Evidence:
[Regression result](evidence/sprint4/pytest-results-20261017.png)

## Recorded Data Integration Check

Command:

    python -m backend.services.e2e_demo_check --database .\data\demo\adelaide_metro_demo.db --map-data .\data\demo_map_data

| Route | Vehicle observations | Prediction observations | Shape variants | Geometry points |
| --- | ---: | ---: | ---: | ---: |
| G10 | 741 | 10743 | 3 | 1232 |
| M44 | 793 | 7319 | 3 | 1381 |
| 506 | 258 | 4194 | 2 | 916 |

The check completed for all three routes. The tested route, stop and
performance requests returned HTTP 200. Vehicle history API row counts
matched the database query counts.

An unknown map route returned 404. Missing map files returned 503.

The source database SHA-256 remained unchanged:

    735de9404b6fe46d52fe0b102004e6993815157b8f5905341afbf9cada465aa2

Evidence:
[Integration check output](evidence/sprint4/e2e-check-20261017.json)

## Browser Checks

| Check | Result | Observation |
| --- | --- | --- |
| Initial loading | Passed | The interface displayed 354 stops and 3 routes. |
| G10 route geometry | Passed | The route line and route stops appeared on the map. |
| Route selection | Passed for G10 to M44 | Switching routes stopped and reset the previous playback. After loading M44 history, automatic playback worked normally. |
| Stop details | Passed | Stop 3917 displayed its details and performance information. Related API requests returned 200. |
| Location selection and nearest stop | Passed | The selected map location displayed stop 3917 as the nearest stop, at 577 m. The interface identified this as straight-line distance. |
| Historical data loading | Passed | The vehicle history request returned 200 and the interface displayed observation and vehicle counts. |
| Automatic playback | Passed | Clicking Play advanced the playback time automatically. |
| Pause | Passed | Pause became available during playback and paused it. |
| Timeline slider | Passed | Changing the playback time updated the vehicle positions. |
| Invalid time range | Passed for validation message | Reversing the time range displayed a request to enter valid start and end times. Previous playback controls remained available. |
| Reset | Not yet confirmed | A separate result has not been recorded. |
| Empty recording window | Not yet checked | Confirm the no-data message and removal of previous playback vehicles. |
| Hotspot browser display | Pending integration | The reviewed frontend does not call the hotspot endpoint. |

The nearest-stop check confirmed that a result appeared. It was not an
independent numerical audit of the distance calculation.

Evidence:
[Nearest-stop browser check](evidence/sprint4/frontend-nearest-stop-20261017.png)

Playback controls and movement results include the tester's manual
observations. Static screenshots alone do not demonstrate movement.

## Hotspot API

The following request returned HTTP 200 and ranked stop results:

    GET /api/analysis/hotspots?route_id=G10&min_services=10

This confirms that the endpoint returned data. Independent validation
of the ranking and comparison with stop performance remain outstanding.

The result ranks stops that meet the minimum observation count.
The number of returned stops is not the number of stops proven to
have severe delays.

## Issues and Follow-up

Owners below are proposed follow-up responsibilities.

| Item | Finding | Follow-up | Proposed owner |
| --- | --- | --- | --- |
| Hotspot frontend | The endpoint exists, but the reviewed frontend does not call it. | Connect the endpoint, match stop IDs to map coordinates and compare displayed values with the API. | Pritish, with Chenchen testing |
| Hotspot parameter validation | A separate review of the same commit found that min_services=abc returns 200 using the default value. This was not reproduced in this Windows session. | Reject invalid values and add a regression test. | Chengxi |
| Observation label | The interface uses "Services analysed" for retained prediction observations. | Use wording that does not imply a count of unique services. | Pritish and Chengxi |
| Map layout | At normal zoom, viewing playback controls and the map requires scrolling. | Improve the layout in a later sprint. Rehearse the current layout before the demonstration. | Pritish |
| Retained stop selection | Changing the route keeps the selected location and nearest-stop result. | Clarify that the nearest stop is independent of the selected route. | Pritish |
| Invalid playback range | The validation message appears, but previous playback controls remain available. | Clarify whether the previous dataset remains active or reset the controls. | Pritish |
| Older documentation | Some earlier demo notes describe geometry and playback as not connected. | Update current guidance while preserving dated test records. | Chenchen, with feature-owner confirmation |

## Limits and Next Checks

This report does not establish that every Sprint 4 feature is complete.

Remaining checks are:

- Test the hotspot interface after integration.
- Retest fixes before closing the related issues.

CASR machine restart behaviour, long-running collection and the latest
v2 database backup are outside this local verification.