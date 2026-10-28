# Database and Query Interface

## Overview

The database module stores processed GTFS and GTFS-Realtime data for later retrieval and analysis.

SQLite stores both development fixtures and the historical collector's data.
For snapshot handling, verified read-only SQL, API examples and research
limitations, use the [CASR technical guide](handover/casr-gtfs-data-collection-and-access.md).
The fields below describe physical historical storage **v2**.

The main database files are:

- `backend/database/connection.py`
- `backend/database/models.py`
- `backend/database/repository.py`

Automated database tests are located in:

- `backend/tests/test_database_repository.py`

Shared test data is located in:

- `tests/fixtures/`

---

## Database Tables

### Routes

The `routes` table stores GTFS route information.

Main fields:

- `route_id`
- `route_short_name`
- `route_long_name`
- `route_type`

### Stops

The `stops` table stores GTFS stop information.

Main fields:

- `stop_id`
- `stop_name`
- `stop_lat`
- `stop_lon`

### Trips

The `trips` table stores GTFS trip information.

Main fields:

- `trip_id`
- `route_id`
- `service_id`
- `trip_headsign`
- `direction_id`

### Stop Times

The `stop_times` table stores scheduled stop information for trips.

Main fields:

- `trip_id`
- `arrival_time`
- `departure_time`
- `stop_id`
- `stop_sequence`

### Trip Updates

The `trip_updates` table stores processed GTFS-Realtime trip updates.

Main fields:

- `trip_id`
- `route_id`
- `stop_id`
- `scheduled_arrival`
- `delay_seconds`
- `observed_at`
- `observation_kind`

`scheduled_arrival` is required INTEGER UTC epoch seconds; `observed_at` is
optional INTEGER UTC epoch seconds. `observation_kind` is 0 initial, 1 change,
2 checkpoint or 3 reappearance. Repository output converts times to Adelaide
ISO format, exposes `observed_at` as `timestamp` and derives `actual_arrival`
from schedule plus delay. That legacy field represents the supplied arrival
estimate, not independently confirmed vehicle arrival.

`trip_update_current_state` has primary key `(trip_id, route_id, stop_id)` and
stores schedule, delay, `last_seen_at`, `last_stored_at`. `collection_cycles`
records successful-cycle time and converted received/stored/suppressed counts.
No foreign keys or per-history-row cycle IDs are declared. See
[models.py](../backend/database/models.py) for the full DDL and indexes.

### Vehicle Positions

The `vehicle_positions` table stores GTFS-Realtime vehicle positions.

Main fields:

- `vehicle_id`
- `trip_id`
- `route_id`
- `latitude`
- `longitude`
- `timestamp`

Vehicle Position `timestamp` remains optional ISO TEXT; it is not the Trip
Update epoch representation.

---

## Record Insertion

The repository provides functions for storing GTFS and GTFS-Realtime records.

```python
insert_route(route)
insert_stop(stop)
insert_trip(trip)
insert_stop_time(stop_time)
insert_trip_update(trip_update)
insert_vehicle_position(vehicle)
```

The historical runner uses `persist_realtime_collection()` via
`persist_collection_result()` to include both record lists, current state and
cycle metadata in one transaction. The functions above are individual insertion
interfaces, not a replacement for that collection-cycle boundary.

## Query functions and time ranges

| Function | Filters / time behavior |
| --- | --- |
| `get_all_routes()`, `get_all_stops()`, `get_stop(stop_id)` | Static dimensions from the configured DB |
| `get_routes_by_stop(stop_id)` | Join `routes` to `trips` to `stop_times`; dimensions must be loaded |
| `get_trip_updates_filtered(route_id=None, stop_id=None, start_time=None, end_time=None)` | ISO inputs converted to epochs; inclusive observation-time bounds |
| `get_vehicle_positions_filtered(vehicle_id=None, route_id=None, start_time=None, end_time=None)` | Inclusive lexical ISO TEXT bounds; consistent stored offset/format required |
| `query_vehicle_history(route_id, start_time, end_time, limit="500", offset="0")` | API service using instant-based comparisons, offset-aware bounds, end exclusive, limit 1–1000 |

Repository queries use the ordinary connection helper, not an enforced read-only
connection. Use a working copy of a verified snapshot for these interfaces, or
the guide's `mode=ro` examples for enforced read-only SQL. Set
`ADELAIDE_METRO_DATABASE_PATH` before importing application modules. No data
queries should run against the known malformed CASR backup.
