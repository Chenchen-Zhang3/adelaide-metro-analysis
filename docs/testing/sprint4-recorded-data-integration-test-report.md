# Sprint 4 Recorded-Data Integration Test Report

## Tester and Environment

- Tester: Chenchen Zhang
- Test date: 14 October 2026
- Tested commit: effa203b849dc8f4b65dcfc1eac8631c93cdc7f6
- Environment: Windows, Python 3.12.2
- Database: local copy of adelaide_metro_demo.db
- Backend: http://127.0.0.1:5000
- Frontend: http://127.0.0.1:8000/frontend/
- Dataset: recorded historical observations from 26 September 2026,
  09:00–11:00 Adelaide time.

## Verified Workflow

Recorded database → query layer → analysis → backend API → frontend display.

## Results

| Check | Observed result | Status |
| --- | --- | --- |
| Backend startup with configured demo database | Flask started on port 5000 | PASS |
| Route API | Returned 506, G10 and M44 | PASS |
| Stop API | Returned 354 stops | PASS |
| G10 performance API | Returned performance statistics | PASS |
| Stop 100618 routes API | Returned G10 | PASS |
| Stop 100618 performance API | Returned performance statistics | PASS |
| Frontend data loading | Displayed 354 stops and 3 routes | PASS |
| G10 frontend performance | Matched API values after display rounding | PASS |
| Stop 3792 selection | Displayed stop details, G10 and performance statistics | PASS |
| Stop 3792 API/display consistency | All displayed statistics matched API values after rounding | PASS |
| Browser geolocation display | Displayed coordinates and a map marker | PASS |

## Remaining Checks

- Manual map-click location selection.
- M44 and 506 performance workflows.
- Automated regression tests.
- Restart and reproducible setup verification.
- Route geometry, nearest-stop distance, delay hotspots and historical
  playback after the corresponding features are integrated.

## Issues and Limitations

- The interface needs a visible recorded historical data label and date range.
- "Services analysed" currently represents retained prediction observations,
  not distinct trips or completed services.
- Map tiles and Leaflet resources require network access unless cached.
- Geolocation display was checked; location accuracy was not independently verified.
- This report confirms only the checks listed above, not completion of the
  full Sprint 4 prototype.

## Evidence

- [Route and stop API results](evidence/sprint4/api-routes-stops.png)
- [G10 frontend performance](evidence/sprint4/frontend-g10.png)
- [Stop 3792 and geolocation display](evidence/sprint4/frontend-stop3792-location.png)
- [Stop 3792 API performance](evidence/sprint4/api-stop3792.png)

## Overall Status

PARTIALLY VERIFIED — remaining integration and acceptance checks are pending.