
# Integration and Quality Assurance Design

**Project:** Adelaide Metro Transport Analysis  
**Client:** Centre for Automotive Safety Research (CASR)  
**Team:** UG-S2-15  
**Author:** Chenchen Zhang  
**Role:** Team Leader, Integration and Quality Assurance  
**Last Updated:** 6 November 2026

## 1. Purpose and Responsibilities

My responsibility was to coordinate the integration and quality assurance process, ensuring that independently developed components could work together as a complete website.

My main contributions included:

- Organising sprint tasks and tracking progress through Jira.
- Coordinating communication with the client and supervisor.
- Managing GitHub integration and reviewing the readiness of changes before merging into main.
- Verifying frontend and backend integration.
- Performing independent API, database and browser testing.
- Identifying integration issues and coordinating fixes with module owners.
- Preparing testing evidence, demonstration instructions and final handover documentation.

The goal was not only to check whether individual modules worked, but also to verify that users could complete the main transport analysis workflows.

## 2. Integration Design

The project follows a modular architecture consisting of a frontend, Flask backend, SQLite historical database and static GTFS network data.

The frontend communicates with the backend through HTTP APIs. The backend retrieves and analyses transport records before returning JSON responses for the interactive map.

My integration approach focused on the following principles:

1. **Independent development:** Team members developed and checked their assigned modules separately.
2. **Controlled integration:** Changes were reviewed and tested before being integrated into main.
3. **Interface verification:** Backend API responses were checked before testing their frontend presentation.
4. **Reproducibility:** Required datasets, environment settings and startup instructions were documented.
5. **Regression prevention:** Automated tests were rerun after major integration changes.

This reduced the risk of introducing new errors while combining independently developed components.

## 3. Quality Assurance Strategy

I used three complementary testing methods.

### 3.1 Automated Testing

Python pytest was used to check backend functions, API behaviour and integration logic.

Automated testing helped detect regressions in existing functionality after code changes.

During Sprint 5, the following test results were recorded:

| Test | Result |
|---|---|
| Earlier integration suite | 356 passed |
| Stop Delays API tests | 41 passed |
| Delay Analysis and Hotspots tests | 19 passed |
| Full pre-fix regression suite | 397 passed |

The full regression suite was run using an isolated temporary SQLite database to avoid modifying an existing historical database.

These results represent separate test executions and are not cumulative counts.

### 3.2 API and Database Verification

I independently tested Flask API endpoints and checked database integrity before proceeding to browser testing.

This included:

- SQLite integrity checks using `PRAGMA integrity_check`.
- Historical data coverage and identifier checks.
- Route and stop performance API responses.
- Network-wide historical prediction delay responses.
- Historical delay hotspot API results.
- Vehicle-history API error investigation.

The original recorded demo database and the CASR v2 historical database were tested separately to avoid confusing their different data coverage and configurations.

### 3.3 Browser-Based Integration Testing

Browser testing verified whether the frontend displayed backend results correctly and supported the main user workflows.

I checked:

- City-wide map loading.
- Route selection and route performance updates.
- Stop selection and stop performance information.
- Nearest-stop search from a selected map location.
- Network-wide historical delay markers and popups.
- Historical delay hotspot rankings and visibility controls.
- Historical vehicle playback loading and controls.

The purpose was to validate the application from the user's perspective, rather than relying only on successful backend test results.

## 4. Data Integration and Risk Control

The project uses static GTFS data and recorded historical GTFS-Realtime observations.

These sources have different purposes and may contain different route and stop identifiers.

During final integration verification, I confirmed that the prepared GTFS Static 1710 catalog contained 384 routes and 7,241 stops or locations.

I also verified the CASR v2 historical database, which contained approximately 7.54 million trip-update observations and 3.69 million vehicle-position observations.

To protect the working demonstration environment, I used a separate local backend and frontend configuration for testing CASR v2.

The original demo environment was preserved as a fallback.

I also avoided modifying the original historical database and used isolated temporary databases for automated tests.

This approach reduced the risk of data corruption and allowed new integration issues to be investigated without disrupting the existing demonstration setup.

## 5. Integration Issue Investigation

A key part of my QA work was identifying and investigating issues that occurred between modules.

### 5.1 CASR v2 Historical Playback

During browser testing, the historical playback feature returned HTTP 404 with the message `Route not found`.

I reproduced the issue through a direct API request and traced it to the backend vehicle-history service.

The service validates route existence against the historical database's `routes` table before querying recorded vehicle positions.

However, the CASR v2 database contains historical vehicle-position records while its `routes` table is empty.

This explained why historical prediction analysis worked but the existing vehicle playback endpoint could not load the CASR v2 data.

I documented the issue and communicated the findings to the responsible team member for a compatibility fix.

**Status:** Pending backend correction and final regression testing.

### 5.2 Missing and Insufficient Historical Data

During network-wide delay testing, I verified that the interface distinguished between:

- Available historical prediction statistics.
- Insufficient prediction samples.
- No historical prediction data.

For example, a stop with only two prediction samples displayed `N/A` instead of an unreliable average delay.

This prevented missing or insufficient information from being presented as a confirmed transport performance result.

Individual No Data marker behaviour remains a pending verification item.

### 5.3 Route and Stop Interaction

I verified that switching from G10 to M44 updated the displayed route and performance statistics.

I also confirmed that manually selecting a stop was a separate interaction from selecting a route.

The testing distinguished independent stop selection from route-specific information, avoiding the incorrect classification of expected behaviour as a defect.

## 6. Documentation and Handover Design

I prepared integration and setup documentation to support reproducibility and reduce dependence on individual developers.

The documentation covers:

- Required development tools and Python dependencies.
- Backend and frontend startup procedures.
- Required historical and static data files.
- Environment configuration.
- Database integrity and historical data limitations.
- Integration test results and supporting evidence.
- Known issues and follow-up verification requirements.

Important documents include:

- `docs/testing/sprint5-final-integration-test-report.md`
- `docs/handover/final-setup-and-handover.md`
- Earlier sprint integration and verification documentation.

The final handover approach separates GitHub source code from large historical datasets that require approved external sharing.

## 7. Design Decisions and Trade-offs

| Decision | Reason |
|---|---|
| Test APIs before browser integration | Isolate backend issues from frontend display problems |
| Use separate CASR v2 and demo environments | Protect the stable demonstration setup |
| Preserve historical databases | Avoid unintended data modification |
| Use independent temporary databases for pytest | Prevent test initialization conflicts |
| Keep missing and insufficient data separate | Avoid misleading analysis results |
| Record unresolved defects explicitly | Prevent unverified features from being reported as complete |
| Maintain integration and handover documentation | Support reproducibility and future maintenance |

These decisions helped balance project delivery, data integrity, reliability and the limited time available before the final presentation.

## 8. Verification Status and Future Work

Sprint 5 testing confirmed that the integrated website could display the city-wide static network and perform route performance, stop performance, network-wide prediction delay and hotspot analysis using CASR v2 historical data.

The full pre-fix automated regression suite passed 397 tests.

The remaining priorities are:

1. Verify the CASR v2 historical playback compatibility fix.
2. Repeat the final automated regression tests after all changes are merged.
3. Confirm that the final setup works with the approved shared datasets.
4. Update the final testing and handover documentation with the verified Git commit.
5. Record any remaining data coverage and system limitations.

My final integration and QA contribution was to establish a repeatable verification process, identify cross-module risks, and provide evidence of which features were ready for demonstration and which required further work.

For detailed results, see `docs/testing/sprint5-final-integration-test-report.md`.
