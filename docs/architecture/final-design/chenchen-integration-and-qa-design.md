
# Integration and Quality Assurance Design

**Project:** Adelaide Metro Transport Analysis  
**Client:** Centre for Automotive Safety Research (CASR)  
**Team:** UG-S2-15  
**Author:** Chenchen Zhang  
**Role:** Team Leader, Integration and Quality Assurance  
**Last Updated:** 7 November 2026  
**Status:** Core integration verified; final handover checks pending

## 1. Purpose and Responsibilities

My main responsibility was to coordinate the integration and quality assurance process, ensuring that independently developed modules worked together as one functional website.

My contributions included:

- Organising sprint tasks, user stories and progress tracking through Jira.
- Coordinating communication with the client and supervisor.
- Managing GitHub integration and coordinating changes to the main branch.
- Verifying frontend, backend and database integration.
- Performing independent automated, API, database and browser-based testing.
- Investigating cross-module issues and communicating findings to the responsible developers.
- Preparing test evidence, setup instructions and final handover documentation.

My objective was not only to verify individual functions, but also to ensure that the integrated application supported CASR's research requirements.

## 2. Integration Design

The project uses a modular architecture consisting of:

- A Leaflet-based frontend for interactive visualisation.
- A Flask backend providing HTTP APIs.
- SQLite databases containing recorded historical observations.
- A separate GTFS Static catalog providing routes, stops and map geometry.

The frontend requests data from the backend, while the backend retrieves and analyses transport information before returning JSON responses.

To manage integration risks, I followed these principles:

1. **Independent development:** Team members developed their assigned modules separately.
2. **Controlled integration:** Changes were reviewed and tested before integration into the main branch.
3. **API-first verification:** Backend endpoints were checked before testing their frontend presentation.
4. **Environment separation:** Stable demonstration data and new historical datasets were tested in separate environments.
5. **Regression testing:** Automated tests were repeated after major integration changes.
6. **Reproducibility:** Required datasets, configuration and startup procedures were documented.

This approach reduced the risk of new changes affecting previously working features.

## 3. Quality Assurance Strategy

I used automated testing, database and API verification, and browser-based integration testing.

### 3.1 Automated Testing

Python pytest was used to verify backend functions, API behaviour and integration logic.

The recorded Sprint 5 results were:

| Test Date | Test Scope | Result |
|---|---|---|
| 3 November | Earlier backend and integration suite | 356 passed |
| 6 November | Stop Delays API | 41 passed |
| 6 November | Delay Analysis and Hotspots | 19 passed |
| 6 November | Full pre-fix regression | 397 passed |
| 7 November | Full post-fix regression | 415 passed |

The final regression suite passed **415 tests in 96.27 seconds**, with no failures.

These were separate test executions and their counts should not be added together.

To avoid interference with historical datasets, the full regression suite was executed using an independent temporary SQLite database path.

### 3.2 Database and API Verification

I used direct API requests and SQLite integrity checks to verify data availability and backend behaviour independently of the frontend.

Verification included:

- SQLite `PRAGMA integrity_check`.
- Historical database table and record checks.
- Route and stop identifier matching.
- Route and stop performance APIs.
- Network-wide prediction delay analysis.
- Historical delay hotspot ranking.
- Historical vehicle-position queries.

The recorded demo database and CASR v2 historical database were verified separately because they have different data coverage and structures.

### 3.3 Browser-Based Integration Testing

I used browser testing to verify the complete interaction between the frontend and backend.

The tested workflows included:

- Loading the city-wide route and stop network.
- Selecting routes and viewing performance statistics.
- Selecting stops and viewing stop performance.
- Finding the nearest stop from a map-selected location.
- Displaying network-wide historical prediction delays.
- Showing and hiding historical delay hotspots.
- Loading and displaying historical vehicle positions.
- Running historical playback and observing timeline progression.

This testing ensured that successful API responses were also reflected in usable frontend interactions.

## 4. Data Integration and Risk Management

The system combines GTFS Static information with recorded historical GTFS-Realtime observations.

The prepared GTFS Static 1710 catalog contained:

- 384 routes
- 7,241 stops or locations
- 1,148 route shapes

The independently verified CASR v2 historical database contained approximately:

- 7.54 million historical trip updates
- 3.69 million recorded vehicle positions

The historical and static datasets did not have identical route and stop coverage.

To manage this risk, I verified historical identifier matching and tested how the website represented missing or insufficient historical observations.

I also maintained separate local configurations:

- The original recorded demo environment.
- An isolated CASR v2 integration environment.

This allowed me to test new data integration without replacing the working demonstration configuration.

The original historical database was preserved without modification, while automated tests used temporary databases to avoid initialization conflicts.

## 5. Integration Issue Investigation and Resolution

A significant part of my work involved identifying problems that occurred between independently developed modules.

### 5.1 CASR v2 Historical Playback Compatibility

During initial integration testing, Historical Vehicle Playback returned:

`HTTP 404 — Route not found`

I reproduced the error through a direct API request and traced it to:

`backend/services/vehicle_history.py`

The original `query_vehicle_history()` implementation checked whether the selected route existed in the historical database's `routes` table before retrieving vehicle positions.

However, the CASR v2 database contained historical vehicle-position observations while its `routes` table was empty.

This caused the service to reject valid historical queries.

I documented the root cause and communicated the issue to the responsible backend team member.

The backend was subsequently updated to support route validation using recorded historical vehicle-position data.

The frontend was also updated to handle Australia/Adelaide daylight saving time correctly.

On 7 November 2026, I independently retested the updated application.

Using Route 100 and historical observations from 17 October 2026, the website successfully loaded recorded vehicle positions, displayed them on the map and advanced the playback timeline.

The final automated regression suite also passed 415 tests.

**Result:** PASS — Historical playback loading and progression verified after the compatibility fix.

Reset and route switching during playback remain separate follow-up checks.

### 5.2 Missing and Insufficient Historical Data

During network-wide delay testing, I verified that the interface distinguished between:

- Available historical prediction statistics.
- Insufficient prediction samples.
- No historical prediction data.

For example, Stop 3569 had only two prediction samples and correctly displayed `N/A` for its delay and punctuality metrics under the minimum sample threshold of 10.

This prevents insufficient information from being presented as a reliable performance result.

The No Data summary was verified, while individual No Data marker behaviour remains to be independently confirmed.

### 5.3 Frontend Route and Stop Interaction

I verified that switching from G10 to M44 updated the map route and Route Performance panel.

I also checked that manual stop selection operated independently from route selection.

This distinction was important because retaining a manually selected network stop after switching routes is not necessarily an error.

Testing therefore considered the intended interaction design before classifying behaviour as a defect.

### 5.4 Database Protection During Regression Testing

During the initial full pytest execution, test collection was interrupted by a legacy historical database protection error.

Rather than modifying the existing database or disabling its protection, I configured a new temporary SQLite database path and repeated the regression suite.

The test run then completed successfully with 397 passing tests.

After the final integration changes, I repeated the full suite and confirmed 415 passing tests.

This approach preserved historical data integrity while maintaining regression test coverage.

## 6. Documentation and Handover Design

I prepared integration and QA documentation to support reproducibility, maintenance and final client handover.

The documentation covers:

- Development environment and dependencies.
- Backend and frontend startup procedures.
- Required static and historical datasets.
- Database integrity and data coverage.
- API and browser integration testing.
- Known issues and their resolution.
- Final regression testing.
- Remaining limitations and handover requirements.

The main documents include:

- `docs/testing/sprint5-final-integration-test-report.md`
- `docs/handover/final-setup-and-handover.md`
- Previous sprint integration and verification documents.

The handover design separates GitHub source code from large historical datasets requiring approved external distribution.

This supports reproducibility without introducing unnecessary data files or local testing environments into the repository.

## 7. Key Design Decisions and Trade-offs

| Design Decision | Reason |
|---|---|
| Test backend APIs before browser integration | Isolate backend problems from frontend issues |
| Maintain separate demo and CASR v2 environments | Protect the stable demonstration workflow |
| Preserve historical databases without modification | Reduce data integrity risks |
| Use temporary SQLite databases for pytest | Avoid conflicts with existing historical data |
| Distinguish missing and insufficient observations | Prevent misleading delay statistics |
| Investigate errors before assigning fixes | Provide developers with reproducible root causes |
| Repeat regression tests after integration changes | Detect regressions in previously working features |
| Document setup and limitations | Support independent reproduction and client handover |

These decisions balanced integration reliability, research data integrity and the limited time available before the final presentation.

## 8. Final Verification and Remaining Work

Sprint 5 integration testing confirmed that the website could combine city-wide GTFS Static information with CASR v2 historical data.

The verified functionality included:

- City-wide route and stop visualisation.
- Route and stop performance analysis.
- Network-wide historical prediction delays.
- Historical delay hotspot ranking and map interaction.
- Stop selection and nearest-stop search.
- Route switching.
- Historical vehicle playback loading and timeline progression.

The final automated regression suite passed **415 tests in 96.27 seconds** on 7 November 2026.

The remaining QA and handover activities are:

1. Confirm Reset and route switching during historical playback.
2. Record the remaining No Data marker verification limitation.
3. Confirm approved dataset-sharing arrangements.
4. Verify the final setup on an independent computer.
5. Record the final Git commit and complete handover review.

My overall contribution was to coordinate a controlled integration process, independently verify the main system workflows, identify and investigate cross-module compatibility issues, and document the evidence and procedures needed for reliable delivery to CASR.

Detailed test results are available in:

`docs/testing/sprint5-final-integration-test-report.md`
