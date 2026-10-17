# Sprint 4 Database Handover

## Overview

This document provides the final handover information for the Sprint 4
database and backend work in the Adelaide Metro Real-Time Transport Analysis
project.

The database layer provides historical GTFS-Realtime storage, historical
queries, route geometry access, and historical vehicle position data for use
by the backend, analysis, and frontend components.

## Completed Database and Backend Work

The following database and backend functions are available:

- historical GTFS-Realtime storage
- route-based historical queries
- stop-based historical queries
- time-range historical queries
- combined route, stop, and time filters
- historical Vehicle Position queries
- route geometry support
- historical vehicle playback API
- pagination for large historical result sets
- duplicate record handling
- database transaction and rollback handling

## Main API Endpoints

### Route Map Data

```text
GET /api/routes/<route_id>/map-data
```

This endpoint provides route-related map information including route geometry,
stops, trips, and static GTFS metadata.

Other components should use this endpoint rather than reading static GTFS map
files directly.

### Historical Vehicle Positions

```text
GET /api/routes/<route_id>/vehicle-positions
```

This endpoint provides historical Vehicle Position records for a selected
route and time period.

The query supports:

- `start_time`
- `end_time`
- `limit`
- `offset`

The returned historical position records include information such as:

- vehicle ID
- trip ID
- route ID
- latitude
- longitude
- timestamp

These records can be used by the frontend to implement time-based vehicle
playback.

## Historical Query Layer

The database repository supports historical Trip Update queries by:

- route ID
- stop ID
- time range
- combined filters

Historical Vehicle Position queries support filtering by:

- vehicle ID
- route ID
- time range
- combined filters

The query layer should be used by backend and analysis components instead of
directly duplicating SQL logic.

## Database Behaviour

Realtime records are stored historically so that older records are retained
when newer feed data arrives.

Duplicate records are protected using database uniqueness constraints and
`INSERT OR IGNORE`.

Realtime persistence uses transactions so that a failed collection cycle does
not leave partially written data in the historical database.

Indexes are provided for commonly used route, stop, vehicle, and timestamp
queries.

## Static GTFS and Route Geometry

Static GTFS data is used to provide route and stop information and route
geometry.

The route map backend supports static GTFS information including:

- routes
- trips
- stops
- stop times
- shapes

Route geometry and stop information are exposed to other components through
the route map API.

## Testing and Verification

The relevant Sprint 4 backend tests were executed successfully.

The main test suites include:

```text
backend/tests/test_api.py
backend/tests/test_e2e_integration.py
backend/tests/test_recorded_map_data.py
```

These tests verify:

- API behaviour
- backend and database integration
- route map data
- recorded static GTFS data
- historical vehicle position access
- request validation
- expected response structures

Historical database queries were also previously verified with real Adelaide
Metro GTFS-Realtime data.

Example historical query results included:

```text
Route BEL records: 42
Stop 6665 records: 6
Time-range records: 77
Combined BEL + time records: 42
```

## Important Integration Notes

The frontend and analysis components should use the documented backend APIs and
repository interfaces rather than accessing the SQLite database directly.

Historical vehicle playback requires the frontend to request position records
from the historical vehicle API and then perform the playback visualisation.

The database/backend responsibility is to provide correctly filtered and
ordered historical records. Frontend animation and playback controls are
handled separately.

Local GTFS data and SQLite database files should not be committed to Git.

## Final Handover Status

The Sprint 4 database and backend work is ready for integration with the
remaining prototype components.

The main interfaces are stable and documented, the relevant backend tests pass,
and the historical and geographic query functions are available for use by the
rest of the project.