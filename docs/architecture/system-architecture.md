# Sprint 1 System Architecture

## 1. Purpose

This document defines the Sprint 1 system architecture, module boundaries,
data flow and integration responsibilities for the Adelaide Metro Real-Time
Transport Analysis project.

The Sprint 1 architecture is designed to allow team members to develop
individual modules independently while using agreed data structures and
interfaces for later integration.

---

## 2. High-Level Architecture

The system is divided into the following major components:

1. GTFS Data Ingestion and Processing
2. Historical Database and Querying
3. Performance Analysis
4. Map and Accessibility Interface
5. System Integration

The expected high-level data flow is:

GTFS / GTFS-Realtime Data
        ↓
Data Ingestion and Parsing
        ↓
Standardised Shared Data Structures
        ↓
Historical Database
        ↓
Query and Analysis Services
        ↓
Map / Accessibility Interface

---

## 3. Module Boundaries

### 3.1 GTFS Data Ingestion and Processing

Responsible for obtaining and processing GTFS and GTFS-Realtime data.

Main responsibilities:
- Read GTFS static data.
- Read or simulate GTFS-Realtime data.
- Parse relevant GTFS entities.
- Convert raw data into agreed shared data structures.

Expected output:
- Standardised stop, route, trip and vehicle-related data.

---

### 3.2 Historical Database and Querying

Responsible for storing processed transport data and providing access
to historical records.

Main responsibilities:
- Define database structures.
- Store processed GTFS data.
- Support historical transport queries.
- Provide data required by analysis modules.

Expected input:
- Standardised data produced by the ingestion module.

Expected output:
- Query results and historical transport records.

---

### 3.3 Performance Analysis

Responsible for analysing transport performance using historical or
processed GTFS data.

Main responsibilities:
- Calculate delay-related metrics.
- Identify frequently delayed locations or services.
- Support route and time-period performance analysis.

Expected input:
- Historical transport records or query results.

Expected output:
- Analysis results and performance metrics.

---

### 3.4 Map and Accessibility Interface

Responsible for presenting transport information to CASR researchers.

Main responsibilities:
- Display stops and routes on a map.
- Present transport analysis results.
- Support location-based accessibility functions such as identifying
  the nearest stop.

Expected input:
- Stop, route and analysis data.

Expected output:
- Interactive map and visual interface.

---

### 3.5 System Integration

Responsible for ensuring that independently developed modules can
operate together.

Main responsibilities:
- Define shared data structures.
- Define module interfaces.
- Maintain sample/mock datasets.
- Review interface compatibility.
- Coordinate integration testing.
- Identify and track integration issues.

---

## 4. Shared Components

The `shared/` directory contains definitions used across multiple modules.

Expected shared resources include:

- GTFS schemas
- Common field names
- Shared constants
- Common data types

All modules should use the agreed shared structures when exchanging data.

---

## 5. Sprint 1 Integration Strategy

During Sprint 1, modules may be developed independently using sample
or mock GTFS data.

Integration will follow this process:

1. Define common data structures.
2. Develop individual modules on separate feature branches.
3. Test modules using shared sample data.
4. Review module input and output compatibility.
5. Resolve interface issues.
6. Merge reviewed modules into the main branch.

---

## 6. Scope of Sprint 1 Architecture

Sprint 1 focuses on establishing the technical foundation of the project.

Full production integration with live Adelaide Metro GTFS-Realtime feeds
is not required at this stage. Sample and mock data may be used to verify
module structure and compatibility.