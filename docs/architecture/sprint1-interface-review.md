# Sprint 1 Interface Compatibility Review

## 1. Purpose

This document records the Sprint 1 interface compatibility review for the Adelaide Metro Real-Time Transport Analysis project.

The purpose of the review is to check whether the modules completed by different team members use compatible GTFS structures and whether their inputs and outputs are suitable for later integration.

The review covers:

- GTFS and GTFS-Realtime processing
- Database storage and retrieval
- Delay and punctuality analysis
- Frontend and map functionality
- Shared schemas and sample data
- Module interfaces

## 2. GTFS Processing

Status: PASS

The backend provides processing support for both static GTFS and GTFS-Realtime data.

The static GTFS parser currently supports:

- stops.txt
- routes.txt
- trips.txt
- stop_times.txt

The parser checks required fields and converts important numeric values such as coordinates, route type and stop sequence into appropriate data types.

GTFS identifiers are preserved using consistent field names including:

- stop_id
- route_id
- trip_id

The GTFS-Realtime part currently supports:

- Vehicle Positions
- Trip Updates
- Service Alerts

The realtime client retrieves GTFS-Realtime data and the decoder converts protobuf data into a usable GTFS-Realtime FeedMessage.

The GTFS converter produces data using the agreed shared field names.

Processed vehicle position records contain:

- vehicle_id
- trip_id
- route_id
- latitude
- longitude
- timestamp

Processed trip update records contain:

- trip_id
- route_id
- stop_id
- scheduled_arrival
- actual_arrival
- delay_seconds
- timestamp

The backend also matches static stop time information with realtime trip updates to calculate service delay.

No critical interface compatibility issue was found in the GTFS processing module.

## 3. Database

Status: PASS FOR SPRINT 1

The database module uses SQLite and provides tables for:

- routes
- stops
- trips
- stop_times
- trip_updates
- vehicle_positions

The table fields are consistent with the main shared GTFS structures.

For example, the trip_updates table stores:

- trip_id
- route_id
- stop_id
- scheduled_arrival
- actual_arrival
- delay_seconds
- timestamp

This is compatible with the processed trip update format produced by the backend.

Repository functions are currently available for:

- inserting stop records
- retrieving stop records
- inserting processed trip updates
- retrieving trip updates by route
- preventing duplicate trip update records

This is sufficient for the Sprint 1 sample database storage requirement.

More complete historical querying and continuous GTFS-Realtime storage will be developed in later sprints.

No critical database interface issue was identified for Sprint 1.

## 4. Performance Analysis

Status: PASS WITH INTEGRATION ACTION REQUIRED

The performance analysis module currently provides functions for:

- average delay
- delayed service count
- delay frequency
- on-time rate
- early arrival rate
- severe delay rate
- punctuality classification

The punctuality classification currently uses the following provisional categories:

- Early
- On Time
- Delayed
- Severely Delayed

The exact five-minute boundary still requires final client confirmation before the final punctuality rules are implemented.

One interface issue was identified during the review.

The backend and database store delay values using:

```text
delay_seconds
```

However, the analysis functions expect delay values in minutes.

The data therefore needs to be converted before it is passed to the analysis functions.

For example:

```python
delay_minutes = delay_seconds / 60
```

This does not require changing the shared schema.

The conversion can be performed when database or backend records are prepared for analysis.

This issue will be tested during Sprint 1 integration testing.

## 5. Frontend and Map

Status: PASS WITH ENVIRONMENT-RELATED RUNTIME ISSUE

The frontend successfully loads the Adelaide map using Leaflet and OpenStreetMap.

The shared Sprint 1 sample stop data was successfully loaded during runtime testing.

The sample CBD stops were displayed correctly as map markers.

The frontend uses the agreed shared stop fields:

- stop_id
- stop_name
- stop_lat
- stop_lon

This confirms that the frontend stop data structure is compatible with the shared Sprint 1 schema.

The current frontend also contains functionality for:

- displaying the Adelaide map
- displaying stop markers
- using browser geolocation
- calculating nearby stops
- calculating straight-line distance using the Haversine formula
- displaying the three nearest stops
- moving the map to a selected nearby stop

During runtime testing, the sample stop markers loaded successfully.

The browser geolocation function was also tested. The browser returned a GeolocationPositionError with code 2 and the developer console showed that the network location provider request was blocked by the client environment.

The location issue appears to be related to the browser, browser extensions or operating system location services rather than the shared GTFS data interface.

Because the current location could not be obtained, the full nearby-stop runtime process could not be completed during this test.

This issue will remain recorded for further testing during SCRUM-109.

The current Sprint 1 prototype uses straight-line distance. Road-network distance is not implemented at this stage and can be investigated in later development where technically feasible.

## 6. Shared Schemas and Sample Data

Status: PASS

The project currently contains shared schemas for:

- Stop
- Route
- Trip
- Stop Time
- Trip Update
- Vehicle Position

These schemas provide common field names and data structures for modules developed by different team members.

Sample datasets are available for:

- stops
- routes
- trips
- stop times
- trip updates
- vehicle positions

The shared sample data allows team members to develop and test their modules without depending on the full real-data integration process.

The validation script:

```text
scripts/validate_fixtures.py
```

checks that the sample datasets follow the shared schemas.

It also checks cross-file references such as:

- route_id
- trip_id
- stop_id

The validation script has previously completed successfully with all sample GTFS data passing validation.

## 7. Module Interface Review

The current Sprint 1 module flow is:

```text
GTFS and GTFS-Realtime data

GTFS processing

Shared data structures

Database storage

Performance analysis

Frontend and map
```

The review found that the main GTFS identifiers are being used consistently between the implemented modules.

The main shared identifiers include:

- stop_id
- route_id
- trip_id
- vehicle_id

The backend processing output and database structures are compatible for the current Sprint 1 data.

The frontend also correctly uses the shared stop structure.

The main integration action identified is the conversion of delay_seconds into minutes before delay values are passed to the analysis metrics.

## 8. Documentation and Dependency Review

Status: PASS

During the interface review, several minor documentation and dependency issues were identified and corrected.

The following updates were completed:

1. stop-time.schema.json was added to the schema list in shared/README.md.
2. Stop Time was added to the expected shared entities in module-interfaces.md.
3. jsonschema was added to requirements.txt because it is required by the shared sample-data validation script.

These changes make the current project documentation and dependency list consistent with the implemented Sprint 1 files.

## 9. Issues Identified

### Issue 1: Delay unit difference

Description:

The backend and database store delay values as delay_seconds, while the performance analysis functions use delay values in minutes.

Status:

Open for integration testing.

Planned action:

Convert delay_seconds to minutes before values are passed to the analysis functions.

### Issue 2: Browser geolocation unavailable

Description:

The frontend map and sample stop markers load correctly, but the browser was unable to provide the user's current location during testing.

The browser developer console reported a GeolocationPositionError with code 2 and indicated that the network location provider request was blocked by the client environment.

Status:

Environment-related runtime issue.

Planned action:

Retest browser geolocation during integration testing. The issue does not currently indicate an incompatibility between the frontend and shared GTFS data structures.

## 10. Overall Review Result

The Sprint 1 interface compatibility review found no critical interface issue that prevents the current modules from proceeding to integration testing.

Current module results are:

```text
GTFS Processing: PASS

Database: PASS FOR SPRINT 1

Performance Analysis: PASS WITH INTEGRATION ACTION REQUIRED

Frontend and Map: PASS WITH ENVIRONMENT-RELATED RUNTIME ISSUE

Shared Schemas and Sample Data: PASS

Documentation and Dependencies: PASS
```

The modules use consistent GTFS identifiers and the implemented data structures are generally compatible.

The remaining issues will be handled and tested during SCRUM-109 integration testing and bug triage.

The Sprint 1 modules are therefore ready to proceed to the integration testing stage.