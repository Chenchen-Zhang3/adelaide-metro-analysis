# Sprint 1 Integration Test Report

## 1. Purpose

This document records the Sprint 1 integration testing results for the Adelaide Metro Real-Time Transport Analysis project.

The purpose of the testing is to confirm that the modules developed during Sprint 1 can use the agreed shared data structures and can operate together at the current prototype stage.

## 2. Shared Sample Data Validation

Status: PASS

The shared sample GTFS datasets were validated using:

```bash
python scripts/validate_fixtures.py
```

The validation covered:

- sample stops
- sample routes
- sample trips
- sample stop times
- sample trip updates
- sample vehicle positions
- cross-file GTFS references

All sample datasets passed validation.

## 3. Backend Unit Testing

Status: PASS

The backend unit tests were run for:

- Static GTFS parsing
- GTFS-Realtime client
- GTFS-Realtime protobuf decoding
- GTFS data conversion
- Stop time processing
- Vehicle position conversion
- Trip update conversion

A total of 22 backend tests were executed.

Result:

```text
Ran 22 tests
OK
```

No critical backend error was identified.

## 4. Database Testing

Status: PASS

The Sprint 1 database test checked:

- inserting a stop
- retrieving a stop
- inserting a trip update
- retrieving trip updates
- duplicate trip update handling

The duplicate handling test passed successfully.

This confirms that the current Sprint 1 SQLite database can store and retrieve the sample records required for basic integration testing.

## 5. Shared Data to Analysis Integration

Status: PASS

The shared sample trip update data stores delay using:

```text
delay_seconds
```

The analysis functions use delay values in minutes.

The integration test converts the values using:

```python
delay_minutes = delay_seconds / 60
```

The sample delays were:

```text
360 seconds = 6 minutes
120 seconds = 2 minutes
```

The expected analysis results were successfully produced:

- Average delay: 4.0 minutes
- Delayed service count: 1
- Delay frequency: 50%
- On-time rate: 50%
- Early arrival rate: 0%
- Severe delay rate: 0%
- 6 minutes: Delayed
- 2 minutes: On Time

Three shared-data analysis integration tests passed successfully.

## 6. Database to Analysis Integration

Status: PASS

A separate integration test was created to confirm that trip update records can be:

1. inserted into the SQLite database
2. retrieved from the database
3. converted from delay_seconds to minutes
4. passed into the performance analysis functions
5. classified using the punctuality functions

A temporary test database was used so that the main development database was not modified.

Result:

```text
Ran 1 test
OK
```

This confirms that the current database output can be used by the Sprint 1 performance analysis module after applying the required seconds-to-minutes conversion.

## 7. Frontend and Map Testing

Status: PASS WITH ENVIRONMENT-RELATED ISSUE

The frontend was started using a local HTTP server.

The following functions were successfully tested:

- Leaflet map loading
- OpenStreetMap base layer loading
- shared sample stop data loading
- CBD sample stop marker display
- use of stop_id
- use of stop_name
- use of stop_lat
- use of stop_lon

The sample GTFS stop data was displayed correctly on the Adelaide map.

The browser geolocation function was also tested.

The browser returned:

```text
GeolocationPositionError
code: 2
```

The developer console also reported that the network location provider request was blocked by the client environment.

Because the current location could not be obtained, the nearby-stop function could not be fully tested during this run.

The issue appears to be related to the browser, browser extensions or operating system location environment rather than the GTFS data interface.

The issue is recorded for future testing.

## 8. Issues Found During Integration

### Issue 1: Delay unit difference

Description:

The backend and database store delay values in seconds, while the analysis functions use delay values in minutes.

Resolution:

Convert delay_seconds to minutes before passing delay values to the analysis module.

Status:

Resolved and tested successfully.

### Issue 2: Browser geolocation unavailable

Description:

The map and sample stop data load correctly, but browser geolocation could not obtain the current location.

The browser returned GeolocationPositionError code 2 and reported that the network location provider was blocked by the client environment.

Status:

Open as an environment-related issue.

Impact:

The issue does not prevent the Sprint 1 map or shared stop data integration from working. It currently prevents full runtime testing of the nearby-stop function.

## 9. Overall Test Result

The Sprint 1 integration tests produced the following results:

```text
Shared Sample Data Validation: PASS

Backend Unit Tests: PASS

Database Storage and Retrieval: PASS

Shared Data to Analysis Integration: PASS

Database to Analysis Integration: PASS

Frontend Map and Sample Stop Integration: PASS

Browser Geolocation: ENVIRONMENT-RELATED ISSUE
```

No critical integration issue currently prevents the Sprint 1 prototype from proceeding to the Sprint Review preparation stage.

The major data interface issue identified during SCRUM-108 was successfully resolved and tested.

The remaining browser geolocation issue has been recorded for later testing.

The Sprint 1 integration testing stage is therefore considered complete.