# Adelaide Metro Real-Time Transport Analysis

This repository contains the prototype developed for the Adelaide Metro Real-Time Transport Analysis capstone project.

The project is being developed for CASR researchers to support the collection, storage, exploration and analysis of Adelaide Metro GTFS and GTFS-Realtime data.

## Sprint 1 Status

Sprint 1 focused on establishing the technical foundation of the project.

The current prototype includes:

- Static GTFS parsing for stops, routes, trips and stop times
- GTFS-Realtime client and protobuf decoding
- Conversion into agreed shared GTFS structures
- Basic SQLite database storage and retrieval
- Delay and punctuality analysis functions
- Adelaide map prototype using Leaflet and OpenStreetMap
- Shared JSON schemas and sample GTFS datasets
- Sample data validation
- Backend unit testing
- Database and analysis integration testing

## Project Structure

```text
backend/
  analysis/
  database/
  parsers/
  realtime/
  services/
  tests/

frontend/
  components/
  css/
  js/
  map/
  pages/
  index.html

shared/
  constants/
  schemas/
  types/

tests/
  fixtures/
  test_analysis_integration.py
  test_database_analysis_integration.py

scripts/
  validate_fixtures.py

docs/
  architecture/
  testing/
```

## Installation

Python 3.12 is currently used for development.

Install the required Python dependencies from the project root:

```bash
python -m pip install -r requirements.txt
```

## Shared GTFS Data

Shared data structures are defined in:

```text
shared/schemas/
```

The current shared entities are:

- Stop
- Route
- Trip
- Stop Time
- Trip Update
- Vehicle Position

Sample data used during Sprint 1 is stored in:

```text
tests/fixtures/
```

## Validate Sample Data

Run:

```bash
python scripts/validate_fixtures.py
```

The validation checks the sample datasets against the shared schemas and also checks cross-file GTFS references.

## Backend Tests

Run the Sprint 1 backend tests using:

```bash
python -m unittest backend.tests.test_static_gtfs backend.tests.test_realtime_client backend.tests.test_realtime_decoder backend.tests.test_gtfs_converter -v
```

The current backend test suite contains 22 tests.

## Database Test

Run:

```bash
python -m backend.database.test_repository
```

The current database test checks basic stop storage, trip update storage, retrieval and duplicate handling.

## Analysis Integration Tests

Run the shared-data analysis test:

```bash
python -m unittest discover -s tests -p "test_analysis_integration.py" -v
```

Run the database-to-analysis integration test:

```bash
python -m unittest discover -s tests -p "test_database_analysis_integration.py" -v
```

The integration layer converts `delay_seconds` into minutes before passing delay values to the performance analysis functions.

## Frontend

The Sprint 1 frontend uses Leaflet and OpenStreetMap.

Start a local server from the project root:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/frontend/index.html
```

The current frontend can display the sample CBD stops using the shared stop structure.

## Current Limitations

The Sprint 1 prototype is an initial technical foundation and is not the final system.

Current limitations include:

- Continuous historical GTFS-Realtime collection is not yet implemented
- More complete database querying will be developed in later sprints
- More detailed delay and route analysis will be added later
- The current nearby-stop prototype uses straight-line distance
- Road-network distance is not yet implemented
- Browser geolocation may depend on local browser and operating system settings
- Final punctuality boundary rules still require client confirmation

## Next Steps

Later sprints will focus on:

- Connecting more components to real Adelaide Metro data
- Historical GTFS-Realtime storage
- Historical querying
- Expanded delay and punctuality analysis
- Route and time-period analysis
- Further map and accessibility integration
- More complete system integration and testing