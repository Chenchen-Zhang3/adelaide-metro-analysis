# Database and Query Interface

## Overview

The database module stores processed GTFS and GTFS-Realtime data for later retrieval and analysis.

SQLite is used as the current development database.

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
- `actual_arrival`
- `delay_seconds`
- `timestamp`

The `timestamp` field is optional.

### Vehicle Positions

The `vehicle_positions` table stores GTFS-Realtime vehicle positions.

Main fields:

- `vehicle_id`
- `trip_id`
- `route_id`
- `latitude`
- `longitude`
- `timestamp`

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