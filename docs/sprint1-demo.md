# Sprint 1 Demo Guide

## 1. Purpose

This document provides the demonstration steps for the Sprint 1 Adelaide Metro Real-Time Transport Analysis prototype.

The demo focuses on the technical foundation completed during Sprint 1.

## 2. Before the Demo

Open the project root directory.

Install the required dependencies if necessary:

```bash
python -m pip install -r requirements.txt
```

Confirm that the latest version of the project is available.

## 3. Show the Project Structure

Briefly show the main project folders:

```text
backend/
frontend/
shared/
tests/
scripts/
docs/
```

Explain that the project is separated by system responsibility so that team members can develop their modules independently.

## 4. Show Shared GTFS Structures

Open:

```text
shared/schemas/
```

Show examples such as:

```text
stop.schema.json
route.schema.json
trip.schema.json
stop-time.schema.json
trip-update.schema.json
vehicle.schema.json
```

Explain that these structures are used to keep field names consistent between modules.

## 5. Run Shared Data Validation

Run:

```bash
python scripts/validate_fixtures.py
```

Expected result:

```text
PASS: sample_stops.json
PASS: sample_routes.json
PASS: sample_trips.json
PASS: sample_stop_times.json
PASS: sample_trip_updates.json
PASS: sample_vehicles.json
PASS: Cross-file GTFS references

ALL SAMPLE GTFS DATA PASSED VALIDATION
```

Explain that this confirms the Sprint 1 sample data follows the agreed shared structures.

## 6. Demonstrate GTFS Processing

Show the backend files for:

```text
backend/parsers/
backend/realtime/
backend/services/
```

Explain that the current backend supports:

- Static GTFS parsing
- GTFS-Realtime feed access
- Protobuf decoding
- Shared data conversion
- Delay calculation

If required, run the backend tests:

```bash
python -m unittest backend.tests.test_static_gtfs backend.tests.test_realtime_client backend.tests.test_realtime_decoder backend.tests.test_gtfs_converter -v
```

Expected result:

```text
Ran 22 tests
OK
```

## 7. Demonstrate Database Storage

Show:

```text
backend/database/
```

Explain that Sprint 1 uses SQLite for the initial database prototype.

Run:

```bash
python -m backend.database.test_repository
```

Show that stop and trip update records can be inserted and retrieved and that duplicate trip updates are prevented.

## 8. Demonstrate Performance Analysis

Show:

```text
backend/analysis/metrics.py
backend/analysis/punctuality.py
```

Explain that the Sprint 1 prototype includes delay and punctuality metrics.

Run:

```bash
python -m unittest discover -s tests -p "test_analysis_integration.py" -v
```

Explain that backend delay values are stored in seconds and are converted into minutes before being passed to the analysis functions.

The sample data produces:

```text
Average delay: 4 minutes
Delay frequency: 50%
On-time rate: 50%
```

## 9. Demonstrate Database to Analysis Integration

Run:

```bash
python -m unittest discover -s tests -p "test_database_analysis_integration.py" -v
```

Explain that this test stores trip updates in the database, retrieves the records and then uses them in the analysis functions.

Expected result:

```text
Ran 1 test
OK
```

## 10. Demonstrate the Map

Start the local server:

```bash
python -m http.server 8000
```

Open:

```text
http://localhost:8000/frontend/index.html
```

Show:

- Adelaide map
- sample CBD stop markers
- stop information

Explain that the frontend reads the same shared stop fields used by the backend and sample data.

If browser geolocation is unavailable during the demonstration, explain that this is currently recorded as an environment-related issue and does not affect the shared stop data or map display.

## 11. Sprint 1 Summary

At the end of the demonstration, explain that Sprint 1 established the main technical foundation for the project.

The current prototype demonstrates:

- GTFS processing
- GTFS-Realtime decoding
- shared data structures
- sample database storage
- delay and punctuality analysis
- module integration testing
- Adelaide stop map prototype

The next sprint will continue with real-data integration, historical storage, querying, expanded analysis and further frontend integration.