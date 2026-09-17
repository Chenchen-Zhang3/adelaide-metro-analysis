# Sprint 3 Database Integration Test Report

## Overview

This report records the Sprint 3 integration testing for the historical database and real Adelaide Metro GTFS-Realtime data.

The purpose of the testing was to verify that real GTFS-Realtime records can be collected, processed, stored in SQLite, retained across multiple collection cycles, and retrieved using the historical database query functions.

The Sprint 3 database work covered:

- real GTFS-Realtime persistence
- route-based queries
- stop-based queries
- time-range queries
- combined filters
- historical Vehicle Position queries
- duplicate record handling
- database optimisation
- transaction and rollback handling
- integration testing
- documentation

## Real GTFS-Realtime Collection

The latest Adelaide Metro static GTFS data was used to provide the `stop_times.txt` file required for scheduled arrival and delay calculation.

The local file structure used for testing was:

```text
data/
├── static_gtfs/
│   └── stop_times.txt
└── history/
    └── adelaide_metro_history.db
```

The historical collection runner was executed using:

```powershell
py scripts/collect_realtime_history.py --stop-times data/static_gtfs/stop_times.txt --database data/history/adelaide_metro_history.db --cycles 1
```

The runner successfully loaded:

```text
Static stop-time records: 953206
Polling interval: 60 seconds
```

The first real GTFS-Realtime collection cycle successfully processed:

```text
Vehicle Positions: 5
Trip Updates: 27
```

The persistence result confirmed that all processed records were inserted:

```text
5/5 Vehicle Positions inserted
27/27 Trip Updates inserted
```

This confirmed that the real Adelaide Metro GTFS-Realtime feed could be collected, processed, and persisted into the historical SQLite database.

## Historical Record Retention

To verify that the database retained historical records rather than replacing them with only the latest realtime information, additional collection cycles were executed using the same database.

After repeated collection, the database contained:

```text
Vehicle Positions: 14
Trip Updates: 77
```

The Vehicle Position timestamp range was:

```text
2026-09-18T01:03:41+09:30
to
2026-09-18T01:07:47+09:30
```

The Trip Update timestamp range was:

```text
2026-09-18T01:04:06+09:30
to
2026-09-18T01:08:06+09:30
```

The earlier records remained in the database while newer records were added.

This confirms that the historical database preserves records across multiple collection cycles instead of overwriting previous realtime data.

## Route-Based Query

The route-based query was tested against real historical Trip Update data.

The following route was queried:

```text
Route ID: BEL
```

The result was:

```text
42 records
```

The returned records included fields such as:

- trip ID
- route ID
- stop ID
- scheduled arrival
- actual arrival
- delay in seconds
- timestamp

This confirms that the historical database supports retrieval of Trip Update records by route ID.

## Stop-Based Query

The stop-based query was tested using:

```text
Stop ID: 6665
```

The result was:

```text
6 records
```

The returned records included multiple Trip Updates associated with the selected stop.

This confirms that stored historical Trip Update records can be retrieved by stop ID.

## Time-Range Query

A time-range query was executed against the real historical database.

The tested time range was:

```text
Start: 2026-09-18T01:04:00+09:30
End:   2026-09-18T01:09:00+09:30
```

The query returned:

```text
77 records
```

The returned records had timestamps within the requested historical period.

This confirms that the repository supports timestamp-based filtering of historical Trip Update records.

## Combined Query

A combined query was also tested using both route and time filters.

The tested filters were:

```text
Route ID: BEL
Start:    2026-09-18T01:04:00+09:30
End:      2026-09-18T01:09:00+09:30
```

The result was:

```text
42 records
```

This confirms that multiple filters can be applied together when retrieving historical Trip Update data.

The database query layer therefore supports:

- route-only queries
- stop-only queries
- time-range queries
- combined route, stop, and time filters

## Vehicle Position History

Historical Vehicle Position support was added during Sprint 3.

Vehicle Position records contain:

- vehicle ID
- trip ID
- route ID
- latitude
- longitude
- timestamp

The repository supports Vehicle Position filtering by:

- vehicle ID
- route ID
- time range
- combined filters

This provides a historical location data source that can later support time-period vehicle playback and route analysis.

## Duplicate Record Handling

Realtime feeds may contain the same information across multiple collection cycles.

Duplicate protection is implemented using database uniqueness constraints together with `INSERT OR IGNORE`.

This allows the historical database to ignore identical records while still storing newer records from later collection cycles.

The repeated live collection test confirmed that the number of historical records increased over time without requiring previous records to be removed.

## Database Optimisation

Indexes are provided for frequently used historical query fields.

Trip Update indexes support queries using:

- route ID
- stop ID
- timestamp
- combined route, stop, and timestamp filters

Vehicle Position indexes support queries using:

- vehicle ID
- route ID
- timestamp
- combined vehicle, route, and timestamp filters

These indexes provide a basic optimisation foundation for historical queries as the database grows.

## Transaction and Rollback Handling

Realtime persistence uses a database transaction for each collection cycle.

Vehicle Positions and Trip Updates from the same collection cycle are persisted together.

If a database error occurs during persistence, the transaction is rolled back.

This prevents the database from keeping only part of a failed collection cycle and improves the consistency of historical data.

## Continuous Historical Collection

A collection runner was added at:

```text
scripts/collect_realtime_history.py
```

The runner supports both bounded and continuous collection.

A fixed number of collection cycles can be executed using:

```powershell
py scripts/collect_realtime_history.py --stop-times data/static_gtfs/stop_times.txt --database data/history/adelaide_metro_history.db --cycles 3
```

Continuous historical collection can be started using:

```powershell
py scripts/collect_realtime_history.py --stop-times data/static_gtfs/stop_times.txt --database data/history/adelaide_metro_history.db --continuous
```

Continuous collection can be stopped manually using:

```text
Ctrl+C
```

The runner waits for the configured polling interval between collection cycles.

This provides a practical way to build a historical GTFS-Realtime dataset over time.

## Automated Testing

The following relevant Sprint 3 test suites were executed successfully:

```text
backend/tests/test_database_repository.py
backend/tests/test_realtime_persistence.py
backend/tests/test_pipeline.py
backend/tests/test_realtime_processing_pipeline.py
```

All relevant tests passed.

The automated tests cover:

- database insertion
- database retrieval
- route-based queries
- stop-based queries
- time-range queries
- combined filters
- Vehicle Position historical queries
- duplicate handling
- database indexes
- configurable database paths
- transaction handling
- rollback behaviour
- repeated realtime collection
- historical record retention
- processing-to-database integration

The database repository test suite also completed successfully with:

```text
20 passed
```

## Local Data and Git

The downloaded static GTFS data and generated historical SQLite databases are local runtime data and should not be committed to the Git repository.

The project `.gitignore` excludes local GTFS data and SQLite database files.

Example local data paths are:

```text
data/static_gtfs/
data/history/
```

This prevents large or continuously changing transport data files from being included in source control.

## Sprint 3 Result

Sprint 3 database integration was successfully verified using both automated tests and live Adelaide Metro GTFS-Realtime data.

The verified data flow is:

```text
Adelaide Metro GTFS-Realtime
        |
        v
Realtime Collector
        |
        v
Processing and Conversion
        |
        v
Historical SQLite Database
        |
        v
Route / Stop / Time Queries
        |
        v
Analysis and Backend Components
```

The database can now collect and retain real historical GTFS-Realtime records across multiple collection cycles.

It also provides stable query interfaces for route, stop, time-range, combined-filter, and Vehicle Position historical queries.

The completed Sprint 3 database work provides the historical data foundation required for later transport reliability analysis and time-period vehicle playback.