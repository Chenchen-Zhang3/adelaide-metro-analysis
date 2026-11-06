
# Sprint 5 — Final Integration Test Report

**Project:** Adelaide Metro Transport Analysis  
**Client:** Centre for Automotive Safety Research (CASR)  
**Tested by:** Chenchen Zhang  
**Test Period:** 3–6 November 2026  
**Branch:** main  
**Python:** 3.12.2  
**Overall Status:** PASS WITH OUTSTANDING ITEMS

## 1. Test Objective

This report documents Sprint 5 testing of the integrated Adelaide Metro Transport Analysis website, including automated backend testing, database verification, real historical data integration, and browser-based functional testing.

Testing was performed using the original recorded demo dataset and the separate CASR v2 historical database.

## 2. Automated Testing

All completed automated test runs passed.

| Date | Test / Command | Result | Duration |
|---|---|---|---|
| 3 Nov | `python -m pytest backend/tests tests -q` | 356 passed | 72.73s |
| 6 Nov | `python -m pytest backend/tests/test_stop_delays.py -v` | 41 passed | 12.90s |
| 6 Nov | `python -m pytest backend/tests/test_analysis.py backend/tests/test_hotspots.py -v` | 19 passed | 0.49s |
| 6 Nov | `python -m pytest -q` | 397 passed | 74.89s |

The first run used commit `1f5180f`. The Stop Delays and Hotspots tests were recorded against commit `59c6ee1`.

The initial full-suite run on 6 November was interrupted during collection by a legacy database protection check. The suite was rerun using a new temporary SQLite database path:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = Join-Path $env:TEMP ("adelaide-metro-test-" + [guid]::NewGuid().ToString("N") + ".db")
python -m pytest -q
```

All 397 tests passed in the isolated environment. This is the pre-fix regression baseline. The suite must be rerun after the final backend changes are merged.

**Test Evidence:**
- `docs/testing/evidence/sprint5/pytest-356-passed-20261103.png`
- `docs/testing/evidence/sprint5/stop-delays-api-test.png`
- `docs/testing/evidence/sprint5/delay-analysis-hotspots-test.png`
- `docs/testing/evidence/sprint5/sprint5-pytest-397-passed-pre-fix.png`

These test counts represent separate runs and must not be added together.

## 3. Database and Historical Data Verification

The original recorded demo database, `data/demo/adelaide_metro_demo.db`, passed the read-only SQLite `PRAGMA integrity_check`.

The CASR v2 database, `adelaide_metro_history_v2_20261022_140923.db`, was independently verified and also returned `ok`.

| CASR v2 Data | Records |
|---|---:|
| Historical trip updates | 7,536,553 |
| Historical vehicle positions | 3,691,004 |
| Routes dimension table | 0 |
| Stops dimension table | 0 |
| Trips dimension table | 0 |

The prepared GTFS Static 1710 network contained 384 routes and 7,241 stops or locations. Historical coverage did not match the full static network: 198 of the 231 historical prediction route IDs matched the static catalog.

Both databases were preserved without modifying their original historical records.

**Evidence:** `docs/testing/evidence/sprint5/demo-database-integrity-test.png`

## 4. CASR v2 API and Browser Integration Testing

**Test Date:** 6 November 2026  
**Backend:** `http://127.0.0.1:5002`  
**Test Frontend:** `http://127.0.0.1:8001/frontend-casr-test/`

The CASR v2 backend and a separate frontend copy were used to protect the original demo environment.

### Backend API Results

| Feature | Result | Observation |
|---|---|---|
| Network-wide prediction delays | PASS | Historical delay data returned |
| Route Performance — G10 | PASS | HTTP 200; 415 samples; 2.04 min average delay |
| Stop Performance — 3413 | PASS | HTTP 200; 13 samples; 2.51 min average delay |
| Historical Delay Hotspots | PASS | HTTP 200; ranked hotspot results |
| CASR v2 Vehicle Playback | BLOCKED | HTTP 404 — Route not found |

The time-bounded performance requests used 17 October 2026, 09:00–09:30 Adelaide time.

### Browser Results

| Feature | Result | Observation |
|---|---|---|
| City-wide network map | PASS | 384 routes and 7,241 locations displayed |
| Route switching | PASS | G10 to M44 updated map and performance |
| Route Performance | PASS | G10 and M44 statistics displayed |
| Selected Stop | PASS | Blue marker updated stop details and performance |
| Nearest Stop | PASS | Map selection returned Stop 101559, 210 m away |
| Network-wide Delay Map | PASS | Delay markers, legend and available-data popup |
| Insufficient Data | PASS | Two samples displayed as N/A |
| No Data summary | PASS | Counts and legend displayed |
| No Data marker / popup | PENDING | Individual marker not verified |
| Historical Delay Hotspots | PASS | Ranked list, visibility toggle and popup worked |
| Historical Vehicle Playback | BLOCKED | Unable to load history (404) |

For the network-wide delay analysis, the browser displayed 31 stops with available statistics, 5,144 with insufficient data, and 2,065 with no data among 7,240 eligible stops.

The Stop 3413 popup displayed a 2.51-minute average predicted delay, 61.54% predicted on-time rate and 13 prediction samples.

The hotspot panel displayed 114 mapped ranked hotspots. Hiding and restoring hotspot markers worked correctly, and selecting an orange marker displayed its historical statistics.

Browser performance values were not directly compared against the time-bounded API results because their analysis windows were not confirmed to be identical.

## 5. Outstanding Issue — CASR v2 Historical Playback

**Status:** BLOCKED — Backend compatibility issue

During browser testing, Historical Vehicle Playback returned:

`HTTP 404 — Route not found`

The root cause was traced to `backend/services/vehicle_history.py`.

The `query_vehicle_history()` function first checks the historical database's `routes` table:

```sql
SELECT 1 FROM routes WHERE route_id = ?
```

However, the CASR v2 `routes` table is empty, despite containing approximately 3.69 million vehicle-position observations. The validation therefore returns `None`, preventing the endpoint from querying those observations.

The issue was communicated to the responsible backend team member.

The required fix should support an appropriate route-validation source while preserving the original recorded demo behaviour. A valid route with no observations should also be distinguished from an unknown route.

After the fix, the following must be retested:

- Vehicle-history API response
- Load Vehicle History
- Play, Pause and Reset
- Route switching during or after playback
- Original demo playback compatibility

The recorded three-route demo remains available as a fallback. The CASR v2 playback function must not be reported as working until retested.

## 6. Final Test Summary and Handover Status

Sprint 5 testing confirmed that the integrated website can display the city-wide Adelaide Metro static network and analyse real historical transport predictions using the CASR v2 dataset.

Verified functionality includes route and stop performance, network-wide historical prediction delays, ranked delay hotspots, selected-stop information, map-based nearest-stop search and route switching.

The full pre-fix regression suite passed **397 tests in 74.89 seconds**, with no test failures.

The following items remain before final acceptance:

1. Complete and verify CASR v2 Historical Vehicle Playback compatibility.
2. Rerun automated regression tests after the final code merge.
3. Confirm final dataset access and reproducible setup instructions.
4. Document the unverified No Data marker behaviour and any remaining limitations.
5. Record the final verified Git commit and test evidence.

**Final Status: PASS WITH OUTSTANDING ITEMS.**

Core historical analysis and frontend integration were verified. Full client acceptance remains pending the outstanding playback fix and final regression testing.
