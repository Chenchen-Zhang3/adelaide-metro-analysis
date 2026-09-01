# Sprint 1 Technical Summary

## 1. Sprint 1 Goal

Sprint 1 focused on establishing the initial technical foundation for the Adelaide Metro Real-Time Transport Analysis project.

The team developed the main module structures independently and used shared GTFS data structures and sample datasets to support later integration.

## 2. GTFS Processing

The GTFS processing module supports both static GTFS and GTFS-Realtime data.

Static GTFS support currently includes:

- stops.txt
- routes.txt
- trips.txt
- stop_times.txt

The GTFS-Realtime component includes:

- Vehicle Positions
- Trip Updates
- Service Alerts

Realtime protobuf feeds can be retrieved and decoded before being converted into the agreed shared data structures.

The backend also supports matching scheduled stop times with realtime trip updates and calculating delay in seconds.

## 3. Database

The Sprint 1 database prototype uses SQLite.

The current database contains tables for:

- routes
- stops
- trips
- stop_times
- trip_updates
- vehicle_positions

Basic repository functions were implemented for storing and retrieving stops and trip updates.

Duplicate trip update handling was also tested successfully.

The current database provides the foundation for historical data storage and querying in later sprints.

## 4. Performance Analysis

The current performance analysis module includes:

- average delay
- delayed service count
- delay frequency
- on-time rate
- early arrival rate
- severe delay rate
- punctuality classification

An interface difference was identified during integration review.

The backend and database use `delay_seconds`, while the analysis functions use delay values in minutes.

The integration layer now converts delay values using:

```python
delay_minutes = delay_seconds / 60
```

This conversion was tested successfully using both shared sample data and database records.

## 5. Frontend and Map

The Sprint 1 frontend prototype uses Leaflet and OpenStreetMap.

The frontend successfully reads the shared sample stop data and displays the sample Adelaide CBD stops on the map.

The current frontend includes:

- Adelaide map display
- stop markers
- browser geolocation support
- nearby-stop calculation
- straight-line distance calculation
- display of the three nearest stops

During testing, browser geolocation returned an environment-related error. The map and shared stop data continued to work correctly.

The geolocation issue has been recorded for later testing.

## 6. Shared Data and Integration

Shared JSON schemas were created for:

- Stop
- Route
- Trip
- Stop Time
- Trip Update
- Vehicle Position

Sample datasets were created using the same field names.

The shared validation script checks:

- schema compatibility
- route references
- trip references
- stop references

This provides a common structure that can be used by the backend, database, analysis and frontend modules.

## 7. Testing Results

The following Sprint 1 tests were completed successfully:

```text
Shared sample data validation: PASS

Backend unit tests: PASS
22 tests completed

Database storage and retrieval: PASS

Duplicate handling: PASS

Shared data to analysis integration: PASS
3 tests completed

Database to analysis integration: PASS
1 integration test completed

Frontend map and sample stop loading: PASS
```

The browser geolocation issue remains recorded as an environment-related runtime issue.

No critical integration issue currently prevents the Sprint 1 prototype from being demonstrated.

## 8. Issues Identified

### Delay Unit Difference

The database stores delay values in seconds while the analysis functions use minutes.

Status: Resolved for integration.

The integration tests convert delay values before analysis.

### Browser Geolocation

The browser returned a GeolocationPositionError during testing.

Status: Open for later testing.

The error appears to be related to the local browser or operating system environment rather than the GTFS data interface.

## 9. Sprint 1 Outcome

Sprint 1 successfully established the initial architecture and module structure required for later project development.

The current prototype demonstrates that:

- GTFS data can be parsed
- GTFS-Realtime data can be retrieved and decoded
- processed data can follow shared structures
- sample transport data can be stored in a database
- database delay data can be used by the analysis module
- sample stops can be displayed on the map
- modules can be tested using common sample data

The next sprint will build on this foundation by increasing the use of real Adelaide Metro data and expanding historical storage, querying, analysis and system integration.