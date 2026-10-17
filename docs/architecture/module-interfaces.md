# Sprint 1 Module Interfaces

## 1. Purpose

This document defines the agreed interfaces between the major Sprint 1
modules. These interfaces allow team members to develop modules
independently while maintaining compatibility during integration.

---

## 2. Data Ingestion - Shared Data

The GTFS ingestion and parsing module should convert source data into
standardised objects following the schemas in:

`shared/schemas/`

Expected entities include:

- Stop
- Route
- Trip
- Trip Update
- Vehicle Position
- Stop Time

---

## 3. Ingestion - Historical Database

### Input

Processed GTFS objects following the shared schemas.

### Expected behaviour

The database module should be able to store identifiers such as:

- stop_id
- route_id
- trip_id
- vehicle_id

These identifiers should remain consistent across modules.

---

## 4. Historical Database - Performance Analysis

### Input

Historical or queryable transport records.

### Required information may include

- route_id
- trip_id
- stop_id
- scheduled arrival time
- actual arrival time
- delay_seconds
- timestamp

### Output

Calculated performance information such as:

- delay
- route performance
- frequently delayed stops or locations
- time-period statistics

---

## 5. Backend / Analysis - Frontend

The frontend should receive processed data rather than raw GTFS files.

Expected information may include:

- Stops and coordinates
- Routes
- Vehicle positions
- Delay information
- Analysis results
- Accessibility results

---

## 6. Interface Rules

All modules should:

1. Use consistent GTFS identifiers.
2. Follow the shared schemas where applicable.
3. Avoid changing shared field names without team agreement.
4. Avoid hard-coded local file paths.
5. Handle missing or optional data safely.
6. Document changes that may affect another module.

## Sprint 4 Recorded Map and Vehicle History APIs

Updated by Chenchen Zhang on 16 October 2026.

### Local Configuration

Set both environment variables before starting Flask:

- ADELAIDE_METRO_DATABASE_PATH: path to adelaide_metro_demo.db.
- ADELAIDE_METRO_DEMO_MAP_DATA_PATH: directory containing
  route-shapes.geojson, stops.geojson, trip-map.json and manifest.json.

The demo uses recorded data from 26 September 2026, 09:00–11:00
Adelaide time (UTC+09:30). It is not a live feed.

### Route Map Data

GET /api/routes/<route_id>/map-data

The response includes:

- label
- static_feed_version
- observation_window
- route_id
- geometry
- stops
- trips

Geometry contains separate official route shape variants.
Use the trip mapping when selecting a shape for a particular trip.

GeoJSON coordinates use [longitude, latitude].
Leaflet L.geoJSON handles this order directly.
Arrays passed to L.polyline instead use [latitude, longitude].

An unknown route returns 404.
Missing or inconsistent map files return 503.

### Historical Vehicle Positions

GET /api/routes/<route_id>/vehicle-positions

Required query parameters:

- start_time: ISO timestamp with a UTC offset.
- end_time: ISO timestamp with a UTC offset.

Optional query parameters:

- limit: 1–1000, default 500.
- offset: non-negative integer, default 0.

The time range includes start_time and excludes end_time.

The response includes route_id, start_time, end_exclusive, limit,
offset, next_offset and positions.

Continue requesting pages using next_offset until it is null.
Pagination is intended for a fixed recorded dataset.

Invalid parameters return 400.
An unknown route returns 404.

### Frontend Handover

The frontend should:

- Load map data when a route is selected.
- Remove previous route layers before drawing the next route.
- Use historical vehicle timestamps for playback.
- Handle pagination when loading vehicle records.
- Show a recorded-data label and date range.
- Display a clear message when data is missing or a request fails.

Frontend implementation is assigned to Pritish.
Chenchen will check the integrated browser workflows after the changes
are available.

### Verification

Backend map and vehicle history checks passed for G10, M44 and 506.
The automated regression run completed with 245 passed and 1 warning.

Browser route geometry, playback, nearest-stop distance and hotspots
still require acceptance testing.

See:

- ../testing/sprint4-map-history-integration-test-report.md
- ../integration/sprint4-demo-setup-and-risks.md