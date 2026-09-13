# Sprint 2 End-to-End Integration Test Report

## Purpose

This test verifies that the main Sprint 2 modules can operate together as an integrated prototype.

The tested workflow includes:

GTFS / stored transport data
→ Database
→ Query and analysis services
→ Backend API
→ Map interface

## Test Environment

- Backend: Flask
- Database: SQLite
- Frontend: HTML / JavaScript / Leaflet
- Testing: Pytest and manual browser testing

## Automated Testing

### Backend tests

Command:

python -m pytest backend/tests -v

Result:

105 tests passed.

### Frontend JavaScript syntax check

Command:

node --check frontend/js/map.js

Result:

No JavaScript syntax errors were reported.

## End-to-End Test Results

| Test | Expected Result | Actual Result | Status |
|---|---|---|---|
| Load map interface | Adelaide map loads successfully | Map displayed correctly | Pass |
| Load stop data | Stops are retrieved from the backend API | Stop marker displayed on the map | Pass |
| Select map location | User can select Location A on the map | Selected coordinates displayed | Pass |
| Find nearest stop | System identifies the nearest available stop | Sample Adelaide Stop identified with distance | Pass |
| Select stop | Stop information is displayed | Stop name and stop ID displayed | Pass |
| Display routes | Routes serving the selected stop are shown | R1 – Sample Adelaide Route displayed | Pass |
| Display performance | Performance analysis is shown for the selected stop | Total services, average delay and punctuality counts displayed | Pass |
| Missing performance data | Interface remains usable when performance data is unavailable | No-data message displayed without breaking the map | Pass |
| Backend regression testing | Existing backend functionality continues to work | 105 backend tests passed | Pass |

## Integration Issues Identified

### Issue 1 — Performance response format mismatch

The frontend originally expected stop performance data as an array of individual records.

The backend performance endpoint returns an aggregated object containing:

- total services
- average delay
- early count
- on-time count
- delayed count
- severely delayed count

### Resolution

The frontend map logic was updated to use the aggregated backend performance structure directly.

The frontend now displays the performance metrics correctly.

---

### Issue 2 — Flask CORS dependency missing from local environment

After the frontend integration changes were merged, backend tests initially failed because the local Python environment did not contain `flask-cors`.

### Resolution

The project dependencies were installed from `requirements.txt`.

The backend then started successfully and the full test suite could run.

## Final Result

The Sprint 2 integrated workflow was successfully tested.

The database, backend API, analysis module and map interface can operate together, and stop route and performance information can be displayed through the frontend.

The current demonstration uses sample development data for integration verification. Real Adelaide Metro data integration and further refinement will continue in later sprints.