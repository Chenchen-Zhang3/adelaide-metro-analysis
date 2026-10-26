# Sprint 5 Historical Database Handover

## Overview

This document provides the final Sprint 5 handover for the historical database
component of the Adelaide Metro Real-Time Transport Analysis project.

Sprint 5 focused on verifying historical GTFS-Realtime coverage, research data
access, service reliability outputs, database integrity, backup and recovery.

## Historical Storage Version

The final historical database uses historical storage version 2.

The storage version is recorded in the `schema_metadata` table.

The v2 historical storage design includes:

- `trip_updates`
- `trip_update_current_state`
- `vehicle_positions`
- `collection_cycles`
- `schema_metadata`

Trip Update observations use `observed_at` as the observation timestamp.

The v2 storage design suppresses unchanged Trip Update observations to reduce
unnecessary database growth while retaining meaningful historical changes.

## Historical Data Coverage Verification

Historical database coverage was verified using real Adelaide Metro
GTFS-Realtime data.

The verified database contained:

```text
Trip Update observations: 3387
Trip Update routes: 28
Trip Update stops: 924
Trip Update trips: 95

Vehicle Positions: 1910
Vehicle Position routes: 186
Distinct vehicles: 499

Successful collection cycles: 4
```

No missing Trip Update observation times were found.

No missing Vehicle Position timestamps were found.

The collection process received:

```text
Trip Updates received: 5764
Trip Updates stored: 3387
Unchanged updates suppressed: 2377
```

This confirms that the historical storage optimisation was working as expected.

## Research Query and Export Access

Historical records can be queried and exported for research use.

CSV export support was verified for:

- all Trip Update records
- all Vehicle Position records
- route-filtered Trip Updates
- route-filtered Vehicle Positions
- time-range filters
- combined route and time filters

Example research exports include:

```text
data/exports/trip_updates.csv
data/exports/vehicle_positions.csv
data/exports/SEAFRD_trip_updates.csv
data/exports/SEAFRD_vehicle_positions.csv
```

The export utility is:

```text
scripts/export_historical_data.py
```

This allows historical records to be used in tools such as Excel, R and Python
without requiring direct manual access to SQLite.

## Service Frequency and Reliability

Service frequency and reliability outputs were also verified.

Scheduled service frequency is calculated from static GTFS timetable data.

Historical reliability is calculated from stored GTFS-Realtime Trip Updates.

For route `SEAFRD`, the verified one-hour research window produced:

```text
Scheduled departures: 8
Scheduled frequency: 8.0 trips/hour

Realtime observations: 150
Unique observed trips: 10

Average delay: 87.4 seconds
On-time rate: 94.0%
Delayed rate: 0.67%
Severe delay rate: 0.0%
Early rate: 5.33%
```

Static GTFS is used for scheduled frequency because realtime observations do
not represent scheduled service frequency.

Historical GTFS-Realtime data is used for delay and reliability analysis.

The analysis utility is:

```text
scripts/summarise_service_reliability.py
```

## Database Verification

The historical database verification utility is:

```text
scripts/verify_historical_database.py
```

It verifies:

- historical storage version
- Trip Update coverage
- Vehicle Position coverage
- route coverage
- stop coverage
- vehicle coverage
- observation time coverage
- collection cycle information
- missing timestamps
- SQLite integrity

The final SQLite quick integrity check returned:

```text
ok
```

## Backup

Historical database backup uses the existing project backup service.

The backup process creates a consistent SQLite snapshot without requiring the
live historical database to be manually copied while it is active.

Backup files should be stored separately from the live database.

Local database and backup files should not be committed to Git.

## Recovery Verification

Recovery was tested using an independent restored database:

```text
data/recovery/adelaide_metro_recovered.db
```

The restored database retained:

```text
Trip Update observations: 3387
Vehicle Positions: 1910
Collection cycles: 4
Schema version: 2
```

The restored database also passed the SQLite integrity check:

```text
Quick check: ok
```

This confirms that the historical database can be backed up and restored
without losing the verified historical records.

## Important Handover Notes

The Sprint 3 legacy database uses an older schema and should not be used with
the current v2 historical storage code.

The legacy database should be preserved separately if historical evidence from
earlier sprints is required.

New historical collection should use a v2 database.

Research users should use the provided query, export and analysis interfaces
instead of manually modifying the SQLite database.

Local runtime data, exports, backups and recovery databases should remain
outside source control.

## Final Status

The Sprint 5 historical database has been verified for:

- real GTFS-Realtime storage
- historical coverage
- timestamp completeness
- duplicate and unchanged-update suppression
- research query access
- CSV export
- scheduled service frequency
- on-time reliability
- database integrity
- backup
- recovery
- final handover

The historical database is ready for final project handover and research use.