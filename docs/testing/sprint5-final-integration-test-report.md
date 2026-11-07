
# Sprint 5 — Final Integration Test Report

**Project:** Adelaide Metro Transport Analysis  
**Client:** Centre for Automotive Safety Research (CASR)  
**Tested by:** Chenchen Zhang  
**Test Period:** 3–7 November 2026  
**Branch:** main  
**Python:** 3.12.2  
**Overall Status:** PASS WITH MINOR VERIFICATION ITEMS

## 1. Test Objective

This report documents Sprint 5 testing of the integrated Adelaide Metro Transport Analysis website, including automated testing, database integrity checks, real historical data integration, and browser-based functional verification.

Testing used both the original recorded demonstration dataset and the CASR v2 historical database.

## 2. Automated Testing

All completed automated test runs passed.

| Date | Test / Command | Result | Duration |
|---|---|---|---|
| 3 Nov | `python -m pytest backend/tests tests -q` | 356 passed | 72.73s |
| 6 Nov | `python -m pytest backend/tests/test_stop_delays.py -v` | 41 passed | 12.90s |
| 6 Nov | `python -m pytest backend/tests/test_analysis.py backend/tests/test_hotspots.py -v` | 19 passed | 0.49s |
| 6 Nov | `python -m pytest -q` | 397 passed | 74.89s |
| 7 Nov | `python -m pytest -q` | 415 passed | 96.27s |

The 3 November test used commit `1f5180f`. The Stop Delays and Hotspots tests were recorded against commit `59c6ee1`.

The initial full-suite execution on 6 November was interrupted during test collection because of legacy database protection. The suite was successfully rerun using a newly generated temporary SQLite database path:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = Join-Path $env:TEMP ("adelaide-metro-test-" + [guid]::NewGuid().ToString("N") + ".db")
python -m pytest -q
```

The 6 November run established a pre-fix baseline of 397 passing tests.

After the latest integration changes, the full suite was rerun on 7 November and **415 tests passed in 96.27 seconds**, with no failures.

**Test Evidence:**
- `docs/testing/evidence/sprint5/pytest-356-passed-20261103.png`
- `docs/testing/evidence/sprint5/stop-delays-api-test.png`
- `docs/testing/evidence/sprint5/delay-analysis-hotspots-test.png`
- `docs/testing/evidence/sprint5/sprint5-pytest-397-passed-pre-fix.png`
The final automated regression test was executed on 7 November 2026.

**Command:** `python -m pytest -q`  
**Result:** 415 passed in 96.27 seconds.  
**Status:** PASS

The result was verified from the local pytest terminal output.

These results represent separate test executions and must not be added together as unique test counts.

## 3. Database and Historical Data Verification

The original recorded demo database, `data/demo/adelaide_metro_demo.db`, passed the read-only SQLite `PRAGMA integrity_check`.

The CASR v2 historical database, `adelaide_metro_history_v2_20261022_140923.db`, was independently verified and also returned `ok`.

| CASR v2 Data | Records |
|---|---:|
| Historical trip updates | 7,536,553 |
| Historical vehicle positions | 3,691,004 |
| Routes dimension table | 0 |
| Stops dimension table | 0 |
| Trips dimension table | 0 |

The prepared GTFS Static 1710 network contained 384 routes and 7,241 stops or locations.

Historical coverage did not match the complete static network: 198 of the 231 historical prediction route IDs matched the static catalog.

Both historical databases were preserved without modifying their original records.

**Evidence:** `docs/testing/evidence/sprint5/demo-database-integrity-test.png`

## 4. CASR v2 API and Browser Integration Testing

**Test Dates:** 6–7 November 2026  
**Backend:** `http://127.0.0.1:5002`  
**Test Frontend:** `http://127.0.0.1:8001/frontend-casr-test/`

A separate backend and frontend testing environment was used to protect the original recorded demo configuration.

### Backend API Results

| Feature | Result | Observation |
|---|---|---|
| Network-wide prediction delays | PASS | Historical delay data returned |
| Route Performance — G10 | PASS | HTTP 200; 415 samples; 2.04 min average delay |
| Stop Performance — Stop 3413 | PASS | HTTP 200; 13 samples; 2.51 min average delay |
| Historical Delay Hotspots | PASS | HTTP 200; ranked hotspot results |
| CASR v2 Vehicle History API | PASS | Previous route-validation issue corrected; historical observations retrievable |

The time-bounded performance API requests used 17 October 2026, 09:00–09:30 Adelaide time.

### Browser Results

| Feature | Result | Observation |
|---|---|---|
| City-wide network map | PASS | 384 routes and 7,241 locations displayed |
| Route switching | PASS | G10 to M44 updated map and performance |
| Route Performance | PASS | G10 and M44 statistics displayed |
| Selected Stop | PASS | Blue marker updated stop details and performance |
| Nearest Stop | PASS | Map selection returned Stop 101559, 210 m away |
| Network-wide Delay Map | PASS | Historical delay markers, legend and popup displayed |
| Insufficient Data | PASS | Two samples correctly displayed as N/A |
| No Data summary | PASS | Counts and legend displayed |
| No Data marker / popup | PENDING | Individual marker not independently verified |
| Historical Delay Hotspots | PASS | Ranked list, marker visibility toggle and popup worked |
| CASR v2 Historical Playback | PASS | Vehicle observations loaded and playback time progressed |
| Playback Reset / route switching | PENDING | Not independently confirmed in the final browser test |

The network-wide delay analysis displayed:

- 31 stops with available historical prediction statistics
- 5,144 stops with insufficient data
- 2,065 stops with no data
- 7,240 eligible network stops

The Stop 3413 popup displayed a 2.51-minute average predicted delay, 61.54% predicted on-time rate and 13 prediction samples.

The Historical Delay Hotspots panel displayed 114 mapped ranked hotspots. Hiding and restoring hotspot markers worked correctly, and selecting an orange marker displayed historical statistics.

Browser performance values were not directly compared with the time-bounded API results because their analysis periods were not confirmed to be identical.

## 5. CASR v2 Historical Playback — Final Verification

**Test Date:** 7 November 2026  
**Tested by:** Chenchen Zhang  
**Result:** PASS — Historical playback loading and playback progression verified

### Issue and Resolution

The initial CASR v2 Historical Vehicle Playback test returned HTTP 404 (`Route not found`).

The issue originated in `backend/services/vehicle_history.py`, where route validation previously depended on the historical database's empty `routes` table.

The backend was updated to support historical route validation using recorded vehicle-position data. The frontend was also updated to handle Australia/Adelaide daylight saving time.

The updated implementation allows historical vehicle observations to be retrieved without requiring the CASR v2 database's `routes` table to contain records.

### Browser Verification

Historical vehicle observations were successfully loaded and displayed on the interactive map using the CASR v2 database.

**Test Configuration:**

- Route: 100
- Date: 17 October 2026
- Time window: 09:00–09:30 Adelaide time
- Recorded observations loaded: 4
- Vehicles displayed: 1

The playback timeline advanced successfully, and the vehicle position was shown on the map.

The screenshot confirmed that the Play, Pause and Reset controls were enabled during playback.

However, Reset functionality and route switching during playback were not separately confirmed and remain follow-up verification items.

### Final Automated Regression

**Command:** `python -m pytest -q`  
**Result:** 415 passed in 96.27 seconds  
**Status:** PASS

The complete automated regression suite passed after the latest integration changes using an isolated temporary SQLite database.

The original September recorded demo remains available as a fallback.

**Current Status:** PASS — CASR v2 historical playback loading, playback progression and post-fix automated regression verified.

## 6. Final Test Summary and Handover Status

Sprint 5 integration testing confirmed that the Adelaide Metro Transport Analysis website can display the city-wide static network and analyse recorded historical transport information using the CASR v2 dataset.

The verified features include:

- City-wide route and stop visualisation
- Route and stop performance analysis
- Network-wide historical prediction delays
- Historical delay hotspot ranking and visualisation
- Selected-stop information
- Map-based nearest-stop search
- Route switching and performance updates
- Historical vehicle playback loading and playback progression

The previous Historical Vehicle Playback HTTP 404 issue was resolved, and the latest full automated regression suite passed **415 tests in 96.27 seconds**.

### Remaining Handover Checks

1. Independently confirm Reset and route switching during Historical Vehicle Playback.
2. Document the unverified No Data marker and popup behaviour.
3. Confirm the approved shared dataset location and reproducible setup instructions.
4. Record the final verified Git commit and save the post-fix test evidence.
5. Complete the final handover review.

**Final Status: PASS WITH MINOR VERIFICATION ITEMS.**

The core historical analysis and frontend integration workflows have been verified. Remaining checks concern specific interactions, evidence and final handover arrangements rather than the previously blocking backend playback issue.
