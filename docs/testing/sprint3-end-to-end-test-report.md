# Sprint 3 End-to-End Integration Test Report

## 1. Objective

The purpose of this test was to verify that the Sprint 3 modules can operate
together as one integrated workflow from database storage and querying,
through transport performance analysis and backend APIs, to the frontend map.

The tested flow was:

Database
→ Query Layer
→ Performance Analysis
→ Backend API
→ Frontend Map

## 2. Test Environment

A separate Sprint 3 integration SQLite database was created using the current
Sprint 3 database schema.

The database was seeded with controlled Adelaide Metro test records from the
shared project fixtures.

The backend was started using:

python -m flask --app backend.api.app run

The frontend was served using:

python -m http.server 8000

## 3. Backend Data Test

The following endpoints were tested successfully:

- GET /api/stops
- GET /api/routes
- GET /api/routes/ROUTE_001/performance
- GET /api/stops/STOP_001/performance
- GET /api/stops/STOP_001/routes

The database returned:

- 3 stops
- 2 routes

The test routes included:

- G10 — Adelaide CBD Service
- H30 — Adelaide Bus Service

## 4. Route Performance Test

Route G10 was selected through the frontend.

The complete workflow was:

Frontend
→ Backend API
→ Historical database query
→ Analysis module
→ Backend response
→ Frontend performance display

The result displayed:

- Services analysed: 1
- Average delay: 6.0 minutes
- On time: 0.0%
- Delayed: 100.0%
- Severe delay: 0.0%
- Early: 0.0%

Result: PASS

## 5. Stop Performance Test

Victoria Square (STOP_001) was selected from the map.

The frontend successfully displayed:

- Stop name
- Stop ID
- Geographic coordinates
- Route serving the stop
- Stop performance information

The performance result was successfully retrieved through the backend analysis
workflow.

Result: PASS

## 6. Automated Regression Testing

The complete backend automated test suite was executed using:

python -m pytest backend/tests -v

Result:

152 passed

The Sprint 3 integration tests were also executed using:

python -m pytest tests -v

Result:

4 passed

## 7. Issues Found and Resolved

### Legacy analysis test reference

Two integration tests were still referencing the old `delay_frequency`
function.

The tests were updated to use the current `delayed_rate` analysis function.

### Pipeline unit-test isolation

Two collection-loop tests were unintentionally accessing database persistence
and failed because the unit-test environment did not create the new
`collection_cycles` table.

Database persistence was mocked in these tests because their purpose is to test
collection-loop and retry behaviour rather than database schema behaviour.

### Legacy local database schema

The original local SQLite database used the earlier Sprint database schema.

A separate Sprint 3 integration database was created using the current schema
to avoid modifying or deleting the original database.

## 8. Real Data Context

Real Adelaide Metro GTFS-Realtime collection and historical database
persistence have already been validated separately during Sprint 3.

The current end-to-end interface test used a controlled integration database so
that database, analysis, backend and frontend behaviour could be tested
reproducibly.

## 9. Final Result

The Sprint 3 integrated workflow successfully connects:

GTFS historical data structure
→ Database
→ Query
→ Delay and performance analysis
→ Backend API
→ Frontend map

The core Sprint 3 integration goal has therefore been achieved.