# Sprint 4 Database Backend Review

## Overview

This document records the Sprint 4 backend and database review for the Adelaide Metro Real-Time Transport Analysis project.

The review focuses on the database query contracts, static route geometry support, and historical vehicle playback API.

## SCRUM-238 - Database Query and API Contracts

The Sprint 4 database and API contracts were reviewed against the current backend implementation.

The following route map endpoint is available:

```text
GET /api/routes/<route_id>/map-data
```

This endpoint provides route-related map data including route geometry, stops, trips, and recorded static feed information.

The following historical vehicle endpoint is also available:

```text
GET /api/routes/<route_id>/vehicle-positions
```

The historical vehicle query supports:

- route ID
- start time
- end time
- pagination limit
- pagination offset

The API contract and backend implementation were checked to ensure that the expected request parameters and response structures are consistent.

## SCRUM-239 - Static Data and Route Geometry

Static GTFS route geometry support is available in the backend.

The recorded map data processing supports static GTFS information including:

- routes
- trips
- stops
- stop times
- shapes

The generated map data can provide:

- route geometry
- stop locations
- trip information
- static GTFS metadata

The route geometry data is exposed through:

```text
GET /api/routes/<route_id>/map-data
```

This provides the backend data required by other modules to display route geometry and stop information.

The relevant recorded map data tests were executed successfully.

## SCRUM-240 - Historical Vehicle Playback API

Historical vehicle position support is available through:

```text
GET /api/routes/<route_id>/vehicle-positions
```

The API supports historical queries using:

- route ID
- start time
- end time
- limit
- offset

Historical Vehicle Position records include information such as:

- vehicle ID
- trip ID
- route ID
- latitude
- longitude
- timestamp

The results are returned in historical order and can be used by the frontend or other components to implement time-based vehicle playback.

Pagination support allows larger historical result sets to be retrieved in multiple requests.

## Testing

The following Sprint 4 backend tests were executed successfully:

```text
backend/tests/test_api.py
backend/tests/test_e2e_integration.py
backend/tests/test_recorded_map_data.py
```

All relevant tests passed.

These tests verify:

- API behaviour
- backend and database integration
- route map data
- recorded static GTFS map data
- historical vehicle position access
- request validation
- expected API response structures

## Result

The Sprint 4 database and backend components for SCRUM-238, SCRUM-239 and SCRUM-240 were reviewed successfully.

The backend currently provides:

- stable database and API contracts
- static GTFS route geometry support
- route and stop map data
- historical vehicle position queries
- pagination support for historical data
- backend interfaces required by later frontend playback and demo integration

The frontend visualisation and final demo validation are handled separately from this backend review.