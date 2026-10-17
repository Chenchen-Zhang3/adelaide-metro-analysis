# Adelaide Metro Real-Time Transport Analysis

This repository contains the prototype developed for the Adelaide Metro Real-Time Transport Analysis capstone project.

The project is being developed for CASR researchers to support the collection, storage, exploration and analysis of Adelaide Metro GTFS and GTFS-Realtime data.

## Sprint 1 and Sprint 2 Status

Sprint 1 established the technical foundation. Sprint 2 adds a reusable
GTFS-Realtime ingestion and processing workflow.

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
- Configurable GTFS-Realtime collection settings
- Scheduled Vehicle Position and Trip Update collection with bounded retry
- Record validation, database-ready historical mapping and delay handling
- Standard logging and a reusable realtime processing pipeline

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

Run the original Sprint 1 backend tests using:

```bash
python -m unittest backend.tests.test_static_gtfs backend.tests.test_realtime_client backend.tests.test_realtime_decoder backend.tests.test_gtfs_converter -v
```

Sprint 2 realtime processing tests and the database handoff contract are
documented in [GTFS Processing and Database Handoff](docs/architecture/gtfs-processing.md).

Run full backend test discovery with:

```bash
python -m unittest discover -s backend/tests -p "test_*.py" -v
```

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

The current prototype is an initial technical foundation and is not the final system.

Current limitations include:

- A deployment host is still required to run continuous GTFS-Realtime collection
- Service Alerts do not yet have a historical persistence contract
- Production monitoring and alerting are not yet configured
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


## Historical GTFS-Realtime Collection

The project supports collecting and storing live Adelaide Metro GTFS-Realtime
data in a historical SQLite database.

The collection runner processes Vehicle Positions and Trip Updates and
preserves records across multiple collection cycles for later querying and
analysis.

### Requirements

Download the latest Adelaide Metro static GTFS feed and provide the
`stop_times.txt` file locally.

Local GTFS data and generated SQLite databases are excluded from Git.

Example local structure:

```text
data/
├── static_gtfs/
│   └── stop_times.txt
└── history/
    └── adelaide_metro_history.db
```

Run One Collection Cycle

```bash
py scripts/collect_realtime_history.py --stop-times data/static_gtfs/stop_times.txt --database data/history/adelaide_metro_history.db --cycles 1
```
Run Multiple Collection Cycles

```bash
py scripts/collect_realtime_history.py --stop-times data/static_gtfs/stop_times.txt --database data/history/adelaide_metro_history.db --cycles 3
```
Run Continuous Historical Collection

```bash
py scripts/collect_realtime_history.py --stop-times data/static_gtfs/stop_times.txt --database data/history/adelaide_metro_history.db --continuous
```
Use Ctrl+C to stop continuous collection.

Historical Queries

Stored Trip Update records can be queried by:

- route ID
- stop ID
- time range
- combined route, stop and time filters

Stored Vehicle Position records can be queried by:

- vehicle ID
- route ID
- time range
- combined filters

These query interfaces support historical transport analysis and provide a
foundation for later vehicle playback functionality.

### Testing

Sprint 3 database integration is covered by automated repository, persistence,
pipeline and realtime processing integration tests.

See:

docs/testing/sprint3-database-integration-test-report.md

for the Sprint 3 database integration test results and live data verification.