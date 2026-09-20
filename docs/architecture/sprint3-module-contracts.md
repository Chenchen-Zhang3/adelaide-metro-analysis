# Sprint 3 Module Interfaces and Data Contracts

## 1. Purpose

This document explains how the main modules in Sprint 3 connect with each other.

The main purpose is to make sure that each module uses the same data fields, so the team can integrate the system more easily.

The main flow is:

GTFS / GTFS-Realtime
→ Database
→ Analysis
→ Backend API
→ Frontend

---

## 2. GTFS Data to Database

The GTFS processing module sends processed realtime data to the database.

For Trip Update data, the main fields are:

- trip_id
- route_id
- stop_id
- scheduled_arrival
- actual_arrival
- delay_seconds
- timestamp

For Vehicle Position data, the main fields are:

- vehicle_id
- trip_id
- route_id
- latitude
- longitude
- timestamp

The database is responsible for storing these records and allowing them to be queried later.

More details are already documented in:

`docs/architecture/gtfs-database-handover.md`

---

## 3. Database to Analysis

The analysis module uses historical records from the database.

The main fields needed for analysis are:

- route_id
- stop_id
- delay_seconds
- timestamp

Before analysis, `delay_seconds` can be converted into `delay_minutes`.

The timestamp can also be grouped into different time periods such as:

- Morning
- Afternoon
- Evening

The current integration logic is in:

`backend/services/pipeline.py`

---

## 4. Analysis Output

The analysis module produces results such as:

- total_services
- average_delay
- early_count
- on_time_count
- delayed_count
- severely_delayed_count

These results can then be used by the backend API.

The analysis module is responsible for the calculation logic.

---

## 5. Backend API to Frontend

The backend provides data to the frontend through API endpoints.

Current endpoints include:

- `GET /api/stops`
- `GET /api/routes`
- `GET /api/stops/{stop_id}`
- `GET /api/stops/{stop_id}/routes`
- `GET /api/routes/{route_id}/performance`
- `GET /api/stops/{stop_id}/performance`

The frontend uses these APIs to display:

- stop information
- route information
- nearby stops
- performance information

The frontend should not directly access the database.

---

## 6. Module Responsibilities

### GTFS Processing

Responsible for:

- getting GTFS and GTFS-Realtime data
- decoding and processing the data
- preparing data for the database

### Database

Responsible for:

- storing historical records
- querying records by route, stop and time
- handling duplicate records

### Analysis

Responsible for:

- calculating delay
- calculating punctuality
- calculating route and stop performance

### Backend / Integration

Responsible for:

- connecting database data with analysis
- providing API endpoints
- connecting backend data with frontend
- integration testing

### Frontend

Responsible for:

- showing stops on the map
- selecting a location
- showing nearby stops
- showing routes and performance information

---

## 7. Integration Rules

For Sprint 3 integration:

1. The same field names should be used across modules.
2. GTFS IDs such as stop_id, route_id and trip_id should stay consistent.
3. Shared field names should not be changed without team discussion.
4. The frontend should get data through the backend API.
5. The backend should not repeat analysis calculations.
6. Missing data should be handled without crashing the system.
7. API responses should use JSON.
8. Any interface changes should be communicated to the team.

---

## 8. Sprint 3 Goal

By the end of Sprint 3, the main data flow should work like this:

GTFS / GTFS-Realtime
→ Database
→ Analysis
→ Backend API
→ Frontend Map

This document will be used as a reference when we integrate and test the modules.