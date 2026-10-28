# Adelaide Metro Real-Time Transport Analysis

This repository contains the prototype developed for the Adelaide Metro Real-Time Transport Analysis capstone project.

The project is being developed for CASR researchers to support the collection, storage, exploration and analysis of Adelaide Metro GTFS and GTFS-Realtime data.

## CASR technical guide — Sprint 5

Start with the [CASR GTFS collection and data-access guide](docs/handover/casr-gtfs-data-collection-and-access.md)
for the processing architecture, collection lifecycle, v2 schema, verified
research examples, API boundaries and Windows operation/recovery references.
The [Sprint 5 integration report](docs/integration/sprint5-gtfs-integration.md)
records static coverage and the SCRUM-268 duplicate-key fix merged through PR #69.

The October CASR production v2 backup failed integrity validation. Production
coverage and sustained reliability remain unverified pending a separately
verified replacement. **v2.1 remains HOLD.** Local tests and the database team's
separate verification do not remove that release restriction.

## Current Prototype Status

The prototype collects and stores Adelaide Metro GTFS-Realtime data
and provides a browser interface for exploring recorded transport data.

The current implementation includes:

- Static GTFS parsing and shared data structures.
- Vehicle Position and Trip Update collection with SQLite persistence.
- Historical queries by route, stop, vehicle and time range.
- Storage optimisation for repeated Trip Update observations.
- Route and stop performance APIs.
- A delay-hotspot backend endpoint.
- A Leaflet map with route geometry and stop selection.
- Nearest-stop lookup using straight-line distance.
- Historical vehicle playback with time selection and playback controls.

The collector has been deployed on a CASR Windows computer.
Automatic restart after a power interruption still needs confirmation.

The Sprint 4 demo uses recorded data from 26 September 2026,
09:00–11:00 Adelaide time, for routes G10, M44 and 506.
The browser demo is not a live feed.

The hotspot interface has not yet been integrated into the frontend.
Further verification is needed as the remaining features are completed.

For local data placement, dependency installation, startup commands
and known issues, follow the
[Sprint 4 Demo Setup and Risks](docs/integration/sprint4-demo-setup-and-risks.md).

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


Run the backend and project test suites from the project root:

```powershell
python -m pytest backend/tests tests -q
```

If pytest is not installed in the active Python environment, install it first:

```powershell
python -m pip install pytest
```

For the recorded-data integration check, see the
[Sprint 4 Browser and Backend Verification Report](docs/testing/sprint4-browser-and-backend-verification-20261017.md).


Run the original Sprint 1 backend tests using:

```bash
python -m unittest backend.tests.test_static_gtfs backend.tests.test_realtime_client backend.tests.test_realtime_decoder backend.tests.test_gtfs_converter -v
```

Sprint 2 realtime processing tests and the database handoff contract are
documented in [GTFS Processing and Database Handoff](docs/architecture/gtfs-processing.md).

## Continuous Historical Collection

After extracting a current static GTFS feed to a local directory containing
`stop_times.txt`, start the collector with:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = "$PWD\data\historical\adelaide-metro-history.db"
python -m backend.services.historical_collection --static-gtfs-dir "$PWD\data\static-gtfs"
```

The runner reuses the existing scheduled collector and collection-cycle SQLite
transaction. Full setup, shutdown, restart and hosting guidance is in
[Continuous Historical GTFS Collection Runner](docs/architecture/historical-collection-runner.md).

For the CASR always-on Windows computer, use the
[Windows Historical Collector Deployment Guide](docs/deployment/windows-historical-collector.md)
and `scripts/start_historical_collector.bat`.

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

The frontend uses Leaflet and OpenStreetMap and connects to the local
Flask backend for route, stop, performance and vehicle-history data.

Before starting the application, follow the
[Sprint 4 Demo Setup and Risks](docs/integration/sprint4-demo-setup-and-risks.md)
to install dependencies, place the six required local data files
and configure the backend data paths.

Start the backend using the commands in that guide.
Keep the backend terminal running.

Open a second terminal in the project root and start the frontend server:

```powershell
python -m http.server 8000
```

Open <http://127.0.0.1:8000/frontend/>.

Both servers must remain running while using the application.
Starting the frontend server alone does not start the backend.

Leaflet and basemap tiles require internet access or cached resources.


## Current Limitations

- The demo uses a fixed recorded dataset rather than a live browser feed.
- The delay-hotspot endpoint is available, but the hotspot frontend is not yet integrated.
- Nearest-stop distance is straight-line distance, not road-network distance.
- Backend performance counts use the latest prediction per trip/stop/scheduled-arrival key in the query result, not unique completed services; the separate reliability CLI aggregates retained rows.
- Some interface labels and the map/control layout still need improvement.
- Leaflet and basemap tiles depend on online or cached resources.
- Browser geolocation depends on browser permissions and operating system settings.
- Automatic collector restart after a power interruption on the CASR computer has not been confirmed.
- The October CASR v2 backup failed integrity validation; production coverage and long-term storage growth need a verified replacement and supporting logs.
- Service Alerts do not yet have a historical persistence contract.
- Production monitoring and alerting are not yet configured.

Local verification results and outstanding issues are recorded in the
[Sprint 4 Browser and Backend Verification Report](docs/testing/sprint4-browser-and-backend-verification-20261017.md).


## Next Steps

- Integrate the hotspot endpoint into the frontend and test the displayed results.
- Clarify performance metric labels and recorded-data information.
- Improve the map and control layout for browser use and screen sharing.
- Retest reported issues after fixes are merged.
- Review the remaining features and acceptance criteria with the client.
- Follow up on the CASR collector restart setup, database backup and storage growth.
- Keep setup, API and data preparation documentation consistent with the tested version.
- Prepare the final demonstration and project handover.



## Historical GTFS-Realtime Collection

The project supports collecting and storing live Adelaide Metro GTFS-Realtime
data in a historical SQLite database.

The collection runner processes Vehicle Positions and Trip Updates and
preserves records across multiple collection cycles for later querying and
analysis.

Trip Updates use the storage-optimised schema: state changes are stored
immediately, unchanged predictions receive periodic checkpoints, timestamps are
stored internally as epoch integers, and `actual_arrival` is reconstructed from
the schedule plus delay. See
[Historical storage optimisation](docs/architecture/historical-storage-optimisation.md) for controlled replay benchmarks and safe
deployment guidance.

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

Testing

Sprint 3 database integration is covered by automated repository, persistence,
pipeline and realtime processing integration tests.

See:

docs/testing/sprint3-database-integration-test-report.md

for the Sprint 3 database integration test results and live data verification.
