# Sprint 1 Module Interfaces

## 1. Purpose

This document defines the agreed interfaces between the major Sprint 1
modules. These interfaces allow team members to develop modules
independently while maintaining compatibility during integration.

---

## 2. Data Ingestion → Shared Data

The GTFS ingestion and parsing module should convert source data into
standardised objects following the schemas in:

`shared/schemas/`

Expected entities include:

- Stop
- Route
- Trip
- Trip Update
- Vehicle Position

---

## 3. Ingestion → Historical Database

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

## 4. Historical Database → Performance Analysis

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

## 5. Backend / Analysis → Frontend

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