# Historical Database and Query Module — Final Design Document

**Project:** Adelaide Metro Transport Analysis  
**Client:** Centre for Automotive Safety Research (CASR)  
**Team:** UG-S2-15  
**Author:** Lixuan Zhang  
**Module:** Historical Database and Queries  
**Date:** 8 November 2026

## 1. Module Purpose and Client Requirements

The purpose of the Historical Database and Queries module is to preserve Adelaide Metro transport observations and make historical information accessible for research.

GTFS-Realtime provides information about vehicle positions and predicted arrival times. However, realtime feeds alone do not provide a permanent record that researchers can query later.

CASR requires historical information to investigate transport performance, identify delays, examine vehicle movements and compare services across different routes, stops and time periods.

My work focused on developing and verifying the historical database and its query interfaces.

The module supports three main research requirements:

- **Historical storage:** Preserve GTFS-Realtime observations for later analysis.
- **Research access:** Allow researchers to retrieve and export records using appropriate filters.
- **Data reliability:** Support duplicate handling, database integrity checks, backup and recovery.

The stored data also supports other project modules, including historical vehicle playback, route performance analysis and delay visualisation.

## 2. Main Features and Implemented Functionality

### 2.1 Historical Database Storage

The project uses SQLite to store static transport information and historical GTFS-Realtime observations.

The principal database tables include:

| Table | Purpose |
|---|---|
| `routes` | Stores route information |
| `stops` | Stores stop identifiers and locations |
| `trips` | Stores trip and service information |
| `stop_times` | Stores scheduled stop times |
| `trip_updates` | Stores historical arrival predictions and delay observations |
| `vehicle_positions` | Stores recorded vehicle GPS positions |
| `trip_update_current_state` | Maintains the latest prediction state |
| `collection_cycles` | Records successful data collection cycles |
| `schema_metadata` | Identifies the historical storage version |

The final historical storage design uses schema version 2.

Trip Update records include route, trip and stop identifiers, scheduled arrival information, delay values, observation timestamps and observation types.

Vehicle Position records include vehicle identifiers, route information, latitude, longitude and timestamps.

### 2.2 Duplicate Handling and Storage Optimisation

A challenge with GTFS-Realtime collection is that the same predicted arrival information may appear repeatedly across polling cycles.

Storing every unchanged prediction would increase database size without adding equivalent research value.

The v2 storage design therefore distinguishes between initial observations, changed predictions, periodic checkpoints and reappearances.

It uses `trip_update_current_state` to remember previously observed prediction states and `collection_cycles` to record successful collection activity.

The default checkpoint interval is 15 minutes.

The database also uses unique indexes to prevent duplicate records.

The `actual_arrival` field is not stored redundantly in the v2 Trip Update table. It is reconstructed from scheduled arrival and delay information when required by the repository interface.

This design reduces unnecessary storage while preserving meaningful prediction changes.

### 2.3 Historical Query Functions

I developed and tested database query functionality that allows historical records to be retrieved by different conditions.

The supported query capabilities include:

- Retrieving Trip Updates by route ID.
- Retrieving Trip Updates by stop ID.
- Retrieving records within a specified time range.
- Combining route, stop and time-range filters.
- Retrieving Vehicle Positions by vehicle ID, route ID and time range.

The relevant implementation is located in `backend/database/repository.py`.

The queries use parameterised SQL statements to separate query parameters from SQL commands.

Database indexes support efficient access to frequently used route, stop and timestamp fields.

### 2.4 CSV Research Export

During Sprint 5, I added `scripts/export_historical_data.py`.

This utility allows users to export historical Trip Updates and Vehicle Positions into CSV files.

It supports full-dataset exports and filtered exports based on route, stop, vehicle and time conditions, depending on the record type.

CSV exports make the collected information accessible to researchers using Excel, R or Python.

This is important because CASR researchers may require data for further statistical analysis outside the prototype.

### 2.5 Service Frequency and Reliability Summaries

I also added `scripts/summarise_service_reliability.py`.

The script combines two different data sources:

- Static GTFS timetable data for scheduled departure frequency.
- Historical GTFS-Realtime Trip Updates for predicted delay and reliability summaries.

The script reports scheduled departures, scheduled frequency, average delay and proportions of early, on-time, delayed and severely delayed observations.

The reliability percentages describe the retained prediction observations in the selected window. They should not automatically be interpreted as the measured punctuality rate of completed trips.

### 2.6 Database Verification, Backup and Recovery

I added `scripts/verify_historical_database.py` to inspect historical storage coverage and database condition.

The verification utility reports record counts, route and vehicle coverage, timestamp ranges, collection cycle information and missing timestamps.

It can also perform a read-only SQLite quick integrity check.

The project additionally provides a shared backup implementation in `backend/services/historical_backup.py`, using SQLite's online backup API.

I tested the backup and recovery workflow using an independent restored database instead of modifying the original historical database.

## 3. System Architecture and Module Workflow

The database module connects GTFS data collection, historical storage, research queries and frontend visualisation.

### 3.1 Main Workflow

**Stage 1 — Data Collection**

The realtime collector retrieves GTFS-Realtime feeds containing vehicle positions and trip updates.

**Stage 2 — Data Processing**

The collected information is decoded, validated and converted into the fields required by the backend.

**Stage 3 — Historical Storage**

The repository writes valid records into SQLite.

Trip Update state comparison prevents unnecessary repeated storage, and successful collection cycles are recorded separately.

**Stage 4 — Historical Queries**

The repository retrieves historical observations using route, stop, vehicle and time filters.

**Stage 5 — Research Access**

The retrieved information is available through backend services, APIs and CSV export utilities.

**Stage 6 — Visualisation**

The frontend uses historical API responses to display transport performance and recorded vehicle movements.

### 3.2 Main Implementation Files

| File | Responsibility |
|---|---|
| `backend/database/connection.py` | SQLite connection configuration |
| `backend/database/models.py` | Database tables and indexes |
| `backend/database/repository.py` | Storage and query operations |
| `backend/database/historical_storage.py` | Timestamp and storage helper functions |
| `backend/services/historical_backup.py` | Database snapshot creation |
| `scripts/collect_realtime_history.py` | Historical collection runner |
| `scripts/verify_historical_database.py` | Database coverage and integrity verification |
| `scripts/export_historical_data.py` | CSV research export |
| `scripts/summarise_service_reliability.py` | Scheduled frequency and reliability summaries |

The collector, backend API and frontend are shared project components developed collaboratively by the team.

My responsibility was primarily the historical storage and query layer, together with its verification, export and handover support.

## 4. Key Design Decisions and Reasons

### 4.1 Selecting SQLite

SQLite was selected because it provides persistent relational storage without requiring a separately managed database server.

It supports SQL queries, indexes, transactions and backup operations.

This made it suitable for developing and demonstrating the historical research system within the project's available resources.

However, long-term collection at larger scales may require additional capacity planning and operational monitoring.

### 4.2 Using a Relational Schema

A relational design allows route, stop, trip and historical observation information to be organised into clearly defined tables.

Identifiers such as `route_id`, `trip_id` and `stop_id` support filtering and relationships across the transport dataset.

This structure makes it easier to retrieve data for specific research questions.

### 4.3 Using Parameterised Queries and Indexes

Historical researchers may request data for particular routes, stops or time periods.

Parameterised SQL queries support flexible filtering while avoiding direct insertion of user-supplied values into SQL statements.

Indexes were added to commonly searched fields to improve query performance.

### 4.4 Optimising Historical Storage

The original approach could repeatedly store unchanged prediction states.

The v2 design retains initial observations, meaningful changes and periodic checkpoints while suppressing unnecessary repeated predictions.

A persistent current-state table also allows the collector to retain state information across application restarts.

The project's storage optimisation benchmarks showed substantial storage savings compared with the legacy format.

### 4.5 Separating Static and Realtime Data

Scheduled frequency and historical predicted reliability answer different research questions.

Static GTFS provides scheduled services and departure times.

Historical GTFS-Realtime provides recorded predictions and vehicle positions.

Keeping these data sources conceptually separate avoids incorrectly treating repeated realtime observations as additional scheduled bus services.

### 4.6 Keeping Research Data Outside GitHub

Large historical databases, local exports and backup files are stored separately from project source code.

The application selects its historical SQLite database using the `ADELAIDE_METRO_DATABASE_PATH` environment variable.

This supports local testing and avoids committing large or changing research datasets into Git.

## 5. Important Assumptions and Limitations

The module has several limitations that researchers should understand.

**Historical coverage depends on collection activity.** The database only contains observations captured while the collector was operating. It does not automatically include all past Adelaide Metro services.

**Stored predictions are not guaranteed actual arrival measurements.** GTFS-Realtime Trip Updates contain predicted delay information, so the resulting reliability summaries should be interpreted accordingly.

**Trip Update observations are not independent services.** One trip may produce multiple records across stops and collection cycles.

**The static and historical datasets may have different coverage.** A route available in the static map does not necessarily have historical observations in the selected database.

**Vehicle positions represent recorded GPS observations.** Playback uses stored positions and does not prove the exact path taken between consecutive observations.

**Timestamp representation differs between tables.** Trip Update observation times use UTC epoch seconds, while vehicle position timestamps are stored as ISO strings. Query tools must handle these representations and Adelaide daylight saving time correctly.

**Scheduled frequency has modelling limits.** The current frequency script requires careful validation of active service calendars, operating dates and service windows. The reported frequency is a timetable-derived value, not proof that every scheduled service operated.

**Large databases require operational checks.** Successful tests on a local database do not establish indefinite storage capacity, uninterrupted data collection or production readiness.

The Sprint 5 component verification dataset and the larger CASR demonstration database are separate datasets. Their record counts should not be combined or represented as the same test.

The project handover documentation also identifies an integrity failure in a separate CASR production backup and records the associated v2.1 release status as HOLD. Successful verification of an individual local database copy does not resolve that wider production issue.

## 6. Testing Methods and Results

### 6.1 Automated Database Testing

During the earlier database sprints, I added tests for historical insertion, duplicate handling and query filtering.

The repository tests covered route-based, stop-based, time-range and combined filtering, including historical vehicle position queries.

Sprint 3 database repository testing recorded 20 passing tests, and the associated pipeline testing recorded six passing tests.

These were component-level results from the relevant development stages.

### 6.2 Sprint 5 Historical Storage Verification

I created a separate v2 historical database and collected four GTFS-Realtime cycles.

The verification results were:

| Metric | Verified result |
|---|---:|
| Schema version | 2 |
| Stored Trip Updates | 3,387 |
| Trip Update routes | 28 |
| Trip Update stops | 924 |
| Distinct trips | 95 |
| Stored Vehicle Positions | 1,910 |
| Vehicle Position routes | 186 |
| Distinct vehicles | 499 |
| Successful collection cycles | 4 |
| Trip Updates received | 5,764 |
| Unchanged updates suppressed | 2,377 |
| Missing observation timestamps | 0 |

The SQLite quick integrity check returned `ok`.

These results verify the reported local collection sample, not the complete city-wide network or the larger CASR production dataset.

### 6.3 CSV Export Verification

I tested full exports from the local v2 database.

The script exported:

- 3,387 Trip Update records.
- 1,910 Vehicle Position records.

I also tested combined route and time filters for route `SEAFRD`.

The filtered Trip Update export returned 150 records, and the corresponding vehicle position export was generated successfully after using the timestamp representation present in the database.

The results demonstrated that historical records could be exported into research-friendly CSV files.

### 6.4 Service Frequency and Reliability Verification

For route `SEAFRD`, a one-hour timetable window on 26 October 2026 produced:

| Metric | Result |
|---|---:|
| Scheduled departures | 8 |
| Scheduled frequency | 8.0 trips/hour |
| Realtime observations | 150 |
| Distinct observed trips | 10 |
| Average predicted delay | 87.4 seconds |
| On-time observation rate | 94.00% |
| Delayed observation rate | 0.67% |
| Severe-delay observation rate | 0.00% |
| Early observation rate | 5.33% |

The frequency calculation was changed to use the static timetable rather than extrapolating the number of observed trips from a short realtime collection window.

These results are a demonstration of the calculation workflow, not a validated network-wide punctuality estimate.

### 6.5 Backup and Recovery Verification

I tested restoration to an independent SQLite database.

The restored verification database retained:

- 3,387 Trip Update records.
- 1,910 Vehicle Position records.
- Four collection cycles.
- Schema version 2.

The restored database also returned `ok` from the SQLite quick integrity check.

This provided evidence that the tested snapshot could be copied and read successfully without changing the original database.

### 6.6 Final Prototype Integration Test

I also tested the historical database through the final web prototype using the team's supplied CASR v2 demonstration database.

For route `100`, a direct database query returned 26,366 historical vehicle position records, while route `J1` returned 58,883.

Both routes had recorded observations spanning 12–22 October 2026.

For the browser demonstration, I selected route `100` and loaded the historical vehicle playback for 22 October 2026, approximately 13:53–14:08 Adelaide time.

The frontend displayed:

- 29 recorded observations.
- Five vehicles shown.
- A functioning playback timestamp and timeline.
- Historical vehicle markers on the map.

After clicking Play, the displayed time advanced and the vehicle markers changed position.

**Result:** The historical database, backend API and frontend playback worked together successfully for this selected demonstration.

This is evidence of integration for the tested route and time window, rather than proof that all routes and historical periods have been tested.

## 7. Major Bugs, Fixes and Remaining Issues

### 7.1 Legacy Schema Compatibility

**Problem:** The older Sprint 3 database stored Trip Updates using `actual_arrival` and `timestamp`, while the v2 schema uses `observed_at` and a different physical representation.

**Resolution:** I used a separate v2 database for Sprint 5 verification and preserved the original historical database. The project's database setup also includes a legacy-schema guard to prevent unsafe in-place changes.

**Remaining limitation:** Old and new databases should not be used interchangeably without appropriate compatibility handling.

### 7.2 Unreasonable Service Frequency

**Problem:** An initial service-frequency calculation used unique observed trips divided by a short observation window. This produced an unrealistic result of 150 trips per hour.

**Resolution:** I changed the calculation to use scheduled departures from static GTFS rather than counting realtime observations as departures.

**Verification:** The selected SEAFRD one-hour demonstration returned eight scheduled departures and a frequency of eight trips per hour.

**Remaining limitation:** Calendar and timetable edge cases require further validation before the calculation is used as a comprehensive research measure.

### 7.3 Historical Vehicle Timestamp Filtering

**Problem:** A filtered Vehicle Position export initially returned no records even though the requested route had stored observations.

**Cause:** The vehicle timestamp values used Adelaide local ISO time, while the filter values used a different UTC representation. The current query implementation compares stored timestamp strings.

**Resolution:** I inspected the timestamps in the database and used a matching time representation for the demonstration query.

**Remaining limitation:** A future improvement would normalise vehicle timestamps consistently before comparison.

### 7.4 Historical Playback Route Validation

**Problem:** The team's final CASR v2 playback integration initially returned a route-not-found response for routes with historical vehicle records.

**Cause:** The API checked static route information in a table that was empty in the selected historical database.

**Team resolution:** The backend integration was updated to support historical route validation, allowing recorded Vehicle Positions to be retrieved without requiring that table to contain the route.

This was an integration issue resolved by another team member; it is included here because it affected the database-to-playback workflow.

### 7.5 Remaining Issues

The remaining technical and operational considerations include:

- Validation of additional service dates and timetable edge cases.
- Consistent handling of timestamp formats and daylight saving changes.
- Incomplete historical coverage when data collection has not operated continuously.
- Separate validation of production backups and long-term collector reliability.
- Careful interpretation of predictions, samples and missing historical information.

## 8. Third-Party Libraries and External Data Sources

### 8.1 SQLite

SQLite provides persistent relational storage, SQL queries, indexes and database integrity checks.

The project uses Python's built-in `sqlite3` module to interact with SQLite and to create consistent backup snapshots.

### 8.2 Python Standard Library

The database and research utilities use standard Python modules including:

- `sqlite3` for database operations.
- `csv` for exporting research data.
- `datetime` and `zoneinfo` for timestamp handling.
- `argparse` for command-line interfaces.
- `pathlib` for file-path handling.
- `logging` for application diagnostics.

### 8.3 GTFS and GTFS-Realtime

Adelaide Metro provides static and realtime transport data used by the project.

Static GTFS includes route, trip, stop, timetable and calendar information.

GTFS-Realtime provides vehicle-position and trip-update observations.

The overall project uses GTFS-Realtime protocol bindings and Protocol Buffers for decoding realtime feed content.

The database module receives processed records through the project's collection and repository interfaces.

### 8.4 Flask and Frontend Integration

Flask is used by the shared backend API layer to expose data and analysis results.

The frontend uses JavaScript and Leaflet to display the transport network and historical information on an interactive map.

These frontend technologies are maintained by other team members but depend on the historical records and backend query interfaces.

## Conclusion

My main contribution to the Adelaide Metro Transport Analysis project was developing and verifying the historical database and query functionality.

Across the project, I worked on database schema development, data insertion, duplicate handling, historical filtering, vehicle position queries, CSV exports, research summaries, verification and handover documentation.

The final prototype demonstrates that historical vehicle records can be retrieved from the database and displayed through an interactive playback interface.

This provides CASR researchers with a foundation for investigating past transport activity and service reliability.

The historical database also supports further research and future system development, provided that dataset coverage, integrity and operational limitations are considered.