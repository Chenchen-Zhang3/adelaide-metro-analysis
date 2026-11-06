## Sprint 5 Automated Integration Testing

**Test Date:** 3 November 2026  
**Tested by:** Chenchen Zhang  
**Git Branch:** main  
**Git Commit:** `1f5180f`  
**Python Version:** 3.12.2  
**pytest Version:** 9.2.0

### Test Execution

The automated test suite was executed on the latest main branch to verify the backend and project-level functionality following Sprint 5 integration.

**Command:**

`python -m pytest backend/tests tests -q`

### Test Results

| Test Metric | Result |
|---|---|
| Tests Passed | 356 |
| Tests Failed | 0 |
| Execution Time | 72.73 seconds |
| Overall Status | PASS |

All 356 tests in the executed suite passed successfully. No failures were reported.

**Test Evidence:** `docs/testing/evidence/sprint5/pytest-356-passed-20261103.png`

### Next Verification Steps

Browser-based end-to-end testing is still required to verify the complete website workflow, including route selection, stop information, historical vehicle playback, delay hotspots, and the updated citywide map.

These results will be recorded separately before final client acceptance and handover.

## Sprint 5 — Stop Delays API Verification

**Test Date:** 6 November 2026  
**Tested by:** Chenchen Zhang  
**Git Branch:** main  
**Git Commit:** `59c6ee1`
**Test Type:** Backend API Automated Testing

### 1. Test Objective

The purpose of this test was to verify the newly integrated Stop Delays API before the final frontend integration.

The endpoint `GET /api/analysis/stop-delays` provides historical predicted delay statistics that can support network-wide delay visualisation for CASR researchers.

This verification was performed independently of the frontend to ensure that the backend functionality could be tested before the final map updates were merged.

### 2. Test Execution

**Test Command:**

`python -m pytest backend/tests/test_stop_delays.py -v`

**Test File:**

`backend/tests/test_stop_delays.py`

### 3. Test Results

| Test Metric | Result |
|---|---|
| Tests Passed | 41 |
| Tests Failed | 0 |
| Execution Time | 12.90 seconds |
| Overall Status | PASS |

All test cases in `test_stop_delays.py` passed successfully during the local test execution.

**Evidence:** `docs/testing/evidence/sprint5/stop-delays-api-test.png`

### 4. Verification Scope

This test verifies the behaviour covered by the Stop Delays API automated test suite.

The tests provide evidence of backend functionality but do not confirm that the new delay statistics are correctly displayed on the final interactive map.

### 5. Remaining Verification

The following checks will be completed after the final frontend integration:

- Network-wide stop delay visualisation on the map.
- Correct delay colour categories and legend.
- Display of delay statistics in stop information panels.
- Appropriate handling of stops without available historical data.
- Final browser-based end-to-end testing.

**Current Status:** Backend API automated verification passed. Final frontend integration and client acceptance testing remain pending.

## Sprint 5 — Delay Analysis and Hotspots Backend Verification

**Test Date:** 6 November 2026  
**Tested by:** Chenchen Zhang  
**Git Branch:** main  
**Git Commit:** `59c6ee1`  
**Test Type:** Backend Automated Testing

### 1. Test Objective

The purpose of this test was to verify the delay analysis and historical delay hotspot functionality independently of the frontend.

These features support CASR researchers by providing delay metrics, punctuality information, and identification of stops with significant historical delays.

### 2. Test Execution

**Test Command:**

`python -m pytest backend/tests/test_analysis.py backend/tests/test_hotspots.py -v`

**Test Files:**
- `backend/tests/test_analysis.py`
- `backend/tests/test_hotspots.py`

### 3. Test Results

| Test Metric | Result |
|---|---|
| Tests Passed | 19 |
| Tests Failed | 0 |
| Execution Time | 0.49 seconds |
| Overall Status | PASS |

All 19 automated tests passed successfully.

### 4. Verification Scope

The executed tests cover delay metric calculations, punctuality-related metrics, aggregation, hotspot ranking, minimum service thresholds, invalid delay handling, and API response behaviour.

These results provide evidence of backend functionality. They do not independently confirm the correctness of the final frontend visualisation or the suitability of every business threshold for CASR's research.

### 5. Remaining Verification

The final browser-based integration test will verify that delay information and hotspot results are displayed correctly in the frontend after the final changes have been merged into main.

**Evidence:** `docs/testing/evidence/sprint5/delay-analysis-hotspots-test.png`

**Current Status:** PASS — Backend automated verification completed. Final frontend integration remains pending.

## Sprint 5 — Demo Database Integrity Verification

**Test Date:** 6 November 2026  
**Tested by:** Chenchen Zhang  
**Git Branch:** main  
**Git Commit:** `59c6ee1`  
**Test Type:** SQLite Database Integrity Check

### 1. Test Objective

The purpose of this test was to verify the structural integrity of the local historical demo database used for the Adelaide Metro Transport Analysis website.

This verification was performed independently of the frontend and did not require any changes to the database.

### 2. Test Environment

**Database File:** `data/demo/adelaide_metro_demo.db`

**Database Engine:** SQLite

**Access Mode:** Read-only

**Verification Command:** `PRAGMA integrity_check`

### 3. Test Results

| Test Metric | Result |
|---|---|
| Database File Accessible | PASS |
| SQLite Integrity Check | ok |
| Overall Status | PASS |

The SQLite integrity check completed successfully and returned `ok`, indicating that no structural integrity errors were detected in the local demo database.

### 4. Verification Scope and Limitations

This test verifies the structural integrity of the local demo SQLite database. It does not confirm the accuracy, completeness or coverage of the historical transport records.

The result also does not apply to the separate CASR production database backup, which requires independent verification.

**Evidence:** `docs/testing/evidence/sprint5/demo-database-integrity-test.png`

**Current Status:** PASS — Local demo database integrity verified.