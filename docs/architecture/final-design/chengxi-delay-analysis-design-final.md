# Delay and Reliability Analysis — Final System Design

**Project:** Adelaide Metro Real-Time Transport Analysis  
**Client:** Centre for Automotive Safety Research (CASR)  
**Team:** UG-S2-15  
**Verification date:** 7 November 2026  
**Contributor:** Chengxi Huang  
**Scope:** Delay metrics, punctuality classification, aggregation and delay hotspot identification  
**Implementation reviewed:** `metrics.py`, `punctuality.py`, `aggregation.py`

## 1. Purpose and scope

This component converts scheduled-versus-arrival-time differences into interpretable service-reliability measures. In the integrated historical GTFS-Realtime workflow, arrival values can be predictions rather than independently observed actual arrivals; metrics must be interpreted accordingly. It classifies each recorded arrival, summarises results by route, stop and time period, and ranks stops that exhibit high proportions of late or severely delayed services. It is an analytical component; the supplied modules do not themselves retrieve GTFS data, persist records, or render a user interface.

## 2. Module design and responsibilities

| Module | Key functions | Responsibility |
|---|---|---|
| `punctuality.py` | `calculate_delay_minutes`, `classify_punctuality` | Calculate signed arrival differences and assign punctuality categories. |
| `metrics.py` | `average_delay`, `average_positive_delay`, `delayed_service_count`, `total_late_count`, `delayed_rate`, `on_time_rate`, `early_arrival_rate`, `severe_delay_rate` | Compute delay averages, counts and percentages. |
| `aggregation.py` | `validate_records`, `calculate_group_metrics`, `aggregate_by_field`, `aggregate_by_route`, `aggregate_by_stop`, `aggregate_by_time_period`, `find_delay_hotspots`, `prepare_analysis_output` | Validate records, aggregate by dimensions, rank stop-level hotspots and assemble structured output. |

The dependency direction is `aggregation.py` → `metrics.py` / `punctuality.py`, and `metrics.py` → `punctuality.py`. Shared category definitions are therefore provided by `classify_punctuality`.

## 3. Delay calculation and classification

### 3.1 Signed delay

The implementation calculates:

\[
\text{delay_minutes} = \frac{\text{actual arrival timestamp} - \text{scheduled arrival timestamp}}{60}
\]

This formula applies to numeric timestamps measured in **seconds**. For two Python `datetime` values, the code subtracts them and converts the resulting duration to minutes.

- Positive values indicate arrival after the schedule.
- Negative values indicate arrival before the schedule.
- Zero indicates arrival exactly on schedule.

**Worked examples (calculated from the implementation):**

| Scheduled | Actual | Calculation | Result |
|---|---|---|---|
| 1,000 seconds | 1,420 seconds | (1,420 − 1,000) / 60 | +7 min (Delayed) |
| 1,000 seconds | 820 seconds | (820 − 1,000) / 60 | −3 min (Early) |
| 1,000 seconds | 1,180 seconds | (1,180 − 1,000) / 60 | +3 min (On Time) |
| 1,000 seconds | 1,720 seconds | (1,720 − 1,000) / 60 | +12 min (Severely Delayed) |

### 3.2 Classification thresholds

The code implements the following mutually exclusive categories:

| Classification | Condition |
|---|---|
| Early | `delay_minutes < 0` |
| On Time | `0 <= delay_minutes <= 5` |
| Delayed | `5 < delay_minutes <= 10` |
| Severely Delayed | `delay_minutes > 10` |

**Boundary cases:** exactly 0 and exactly 5 minutes are On Time; exactly 10 minutes is Delayed; only values strictly greater than 10 minutes are Severely Delayed. These are implementation thresholds, not an independently established Adelaide Metro regulatory definition.

## 4. Metrics and formulas

For a collection of `N` signed delays `d₁, …, dₙ`:

| Metric | Implementation / formula | Interpretation |
|---|---|---|
| Average delay | `sum(delays) / N` | Signed mean; early arrivals offset late arrivals. |
| Average positive delay | Mean of values where `d > 0` | Mean lateness among positive delays, including those within the On Time category. |
| Delayed service count | Count of `d > threshold` (default 5) | Counts both Delayed and Severely Delayed at the default threshold. |
| Total late count | Count of `d > 5` | Counts Delayed and Severely Delayed services. |
| Delayed rate | `count(classification == "Delayed") / N × 100` | Only the >5 to ≤10 minute category. |
| On-time rate | `count(0 <= d <= threshold) / N × 100` (default threshold 5) | On-time percentage; excludes early arrivals. |
| Early arrival rate | `count(d < 0) / N × 100` | Percentage arriving before schedule. |
| Severe delay rate | `count(d > threshold) / N × 100` (default threshold 10) | Percentage with delay above 10 minutes by default. |

For empty lists, the standalone metrics functions return `0.0`. This is a computational convention and must not be interpreted as proof of good performance when no observations exist. `calculate_group_metrics([])` instead returns an empty dictionary.

**Worked example:** With delays `[-3, 2, 5, 7, 12]` minutes:

- Total observations: **5**.
- Categories: **1 Early, 2 On Time, 1 Delayed, 1 Severely Delayed**.
- Average delay: `(-3 + 2 + 5 + 7 + 12) / 5 = 4.6` minutes.
- Average positive delay: `(2 + 5 + 7 + 12) / 4 = 6.5` minutes.
- Early rate: **20%**; On Time: **40%**; Delayed: **20%**; Severely Delayed: **20%**.
- Total late rate (`d > 5`): **40%**.

Note the distinction between **positive delay** (`d > 0`) and the operational **late classification** (`d > 5`). A 2-minute positive delay contributes to `average_positive_delay` but is still On Time.

## 5. Record validation and aggregation

### 5.1 Input validation

`validate_records` requires each input to be a dictionary containing `delay_minutes`. Its delay must be a finite `int` or `float`, excluding booleans, NaN and infinity. Invalid inputs raise `ValueError` rather than being silently discarded. `aggregate_by_field` additionally requires a non-`None` grouping field.

**Expected record shape (illustrative):**

```python
{
    "route_id": "R1",
    "stop_id": "A01",
    "time_period": "Morning",
    "delay_minutes": 7.0,
}
```

The record above is a documentation example, not evidence of a real Adelaide Metro observation. `prepare_analysis_output` requires the grouping keys used by all three aggregation methods.

### 5.2 Aggregation algorithm

`aggregate_by_field(records, field_name)` validates the records, groups their `delay_minutes` values with a `defaultdict(list)`, and calculates group metrics. Three wrappers select the grouping key:

- `aggregate_by_route` → `route_id`
- `aggregate_by_stop` → `stop_id`
- `aggregate_by_time_period` → `time_period`

For each nonempty group, `calculate_group_metrics` reports total services; signed and positive-delay averages; counts of Early, On Time, Delayed and Severely Delayed; total late count; and the corresponding percentages. Group-level averages and percentages are rounded to **two decimal places**.

The number of observations is the number of supplied records. The modules do not independently deduplicate repeated events or check whether a record represents a distinct vehicle, trip or stop arrival.

### 5.3 Structured output

`prepare_analysis_output(records, min_services=10)` returns a dictionary with:

```text
route_performance
stop_performance
time_period_performance
delay_hotspots
```

This output can be consumed by other backend components. The supplied files do not establish the exact API endpoint, database query or frontend rendering contract.

## 6. Delay hotspot identification

`find_delay_hotspots(records, min_services=10, top_n=None)` identifies **stop-level** hotspots from historical records.

**Processing steps:**

1. Validate `min_services` as a positive integer and, if provided, `top_n` as a positive integer. Booleans are rejected.
2. Aggregate records by `stop_id`.
3. Exclude stops with fewer than `min_services` observations; the default is **10**.
4. Sort eligible stops in descending order using the following priorities:
   1. `severe_delay_percentage`
   2. `total_late_percentage`
   3. `average_positive_delay`
   4. `severely_delayed_count`
5. Break any remaining ties by the string representation of `stop_id` in ascending order.
6. Apply `top_n` if specified, and assign one-based `rank` values.

**Illustrative ranking example:** Suppose Stop A and Stop B both have at least 10 records. If Stop A has a severe-delay percentage of 30% and Stop B has 20%, Stop A ranks higher, even if Stop B has a larger total late percentage. If their severe-delay percentages tie, the second criterion decides, and so on.

The threshold of 10 observations is explicitly described as **provisional** in the code. It reduces rankings based on very small samples but does not ensure statistical significance or equal exposure across stops.

## 7. Assumptions, design decisions and limitations

1. **Input timing:** Numeric timestamps are assumed to be in seconds. The calculation supports a pair of numeric timestamps or a pair of Python `datetime` objects. Mixed types raise `TypeError`; timezone compatibility is not independently checked by this module.
2. **Punctuality definition:** Early is `< 0`, On Time is `0–5`, Delayed is `>5–10`, and Severely Delayed is `>10` minutes. Early arrivals are not counted as On Time.
3. **Signed averages:** Early arrivals can reduce the overall signed average delay, so this value should be read alongside category percentages and average positive delay.
4. **Different meanings of lateness:** `average_positive_delay` uses `d > 0`, whereas `total_late_count` and hotspot late percentages use `d > 5`.
5. **Sample-size filter:** The default `min_services=10` is provisional and configurable. The filter excludes smaller groups from hotspot results, not from ordinary stop aggregation.
6. **Record completeness:** The code validates delay values and required grouping fields, but does not independently detect duplicate observations, missing services, inconsistent trip identities, or GTFS feed quality issues.
7. **Historical interpretation:** Hotspots are ranked only over the records supplied. Results may differ by data collection window, peak/off-peak composition, route frequency and number of recorded services.
8. **Stop-level scope:** The hotspot function ranks stops, not routes or geographic clusters. A high-ranked stop indicates observed delay concentration under the implemented criteria, not the cause of the delays.
9. **Rounded ranking inputs:** Hotspot sorting uses the group metrics rounded to two decimal places. Near-equal unrounded values may therefore tie.
10. **Prediction versus actual arrival:** The historical GTFS-Realtime Trip Update workflow can provide predicted arrival times; a predicted delay is not proof of an actual completed late arrival. Upstream record selection and deduplication are outside these three modules.
11. **No causal inference:** The modules describe observed performance; they do not establish causes such as traffic, weather, incidents or operational decisions.

## 8. Testing and debugging verification

### 8.1 Test environment and scope

Local verification was performed on **7 November 2026** in VS Code on **macOS (Darwin)** using **Python 3.11.7** and **pytest 7.4.0**. The commands below were run from the repository root. Verification is documented through reproducible commands and recorded results; no screenshot files are required.

These are targeted tests and a controlled demonstration, not a complete production validation or a claim that all tests in the repository were run locally.

### 8.2 Delay analysis and hotspot unit tests

Command:

```bash
python -m pytest backend/tests/test_analysis.py backend/tests/test_hotspots.py -v
```

**Observed result: 19 passed in 0.25 seconds; 0 failed.** The terminal output lists cases for signed delay calculation, early/on-time/delayed/severe categories, averages and rates, sample-data analysis, prediction deduplication, multiple scheduled arrivals, boundary conditions, stop aggregation, hotspot ranking, minimum service filtering, invalid delays and backend output.



### 8.3 Pipeline integration testing

Command:

```bash
python -m pytest backend/tests/test_pipeline.py -v
```

**Observed result: 6 passed in 0.14 seconds; 0 failed.** The six named tests were:

| Test | Result |
|---|---|
| `test_persist_collection_result` | PASSED |
| `test_query_and_analyse` | PASSED |
| `test_pipeline_with_database` | PASSED |
| `test_run_collection_and_persist_repeats_cycles` | PASSED |
| `test_run_collection_and_persist_continues_after_retry_failure` | PASSED |
| `test_run_collection_and_persist_keeps_historical_records` | PASSED |

These tests provide supporting evidence for the wider collection/persistence/query workflow; they are not all exclusively authored by the delay-analysis contributor. Across the first two executions, **25 distinct test cases passed**.



### 8.4 Separate hotspot regression execution

The hotspot tests were also run independently:

```bash
python -m pytest backend/tests/test_hotspots.py -v
```

**Observed result: 7 passed in 0.07 seconds; 0 failed.** These seven tests were already included in the 19-test execution in Section 8.2 and must **not** be added to the distinct-test total.

### 8.5 Hotspot ranking verification with synthetic observations

A separate manual execution invoked `backend.analysis.aggregation.find_delay_hotspots` with **30 synthetic observations**, 10 per stop, and `min_services=10`. The stop identifiers `A01`, `A02` and `A03` are illustrative, not verified Adelaide Metro stop IDs.

The synthetic delays were:

```python
sample_delays = {
    "A01": [12, 15, 11, 8, 7, 14, 3, 2, 13, 6],
    "A02": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "A03": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
}
records = [
    {"stop_id": stop_id, "delay_minutes": delay}
    for stop_id, delays in sample_delays.items()
    for delay in delays
]
ranked = find_delay_hotspots(records, min_services=10)
```

**Observed output:**

| Rank | Stop | Severe delay (%) | Total late (%) | Average positive delay (min) |
|---|---|---:|---:|---:|
| 1 | A01 | 50.0 | 80.0 | 9.1 |
| 2 | A02 | 10.0 | 60.0 | 6.5 |
| 3 | A03 | 0.0 | 50.0 | 5.5 |

The result follows the configured descending severe-delay ranking priority. The output also illustrates that positive delay (`>0`) differs from the late category (`>5`). The demonstration verifies this specific controlled input only; it is not a real historical-performance finding.



### 8.6 Debugging evidence

During the manual demonstration, the first shell command failed with `zsh: parse error near '&'`. The copied heredoc operator had been HTML-escaped as `&lt;&lt;` rather than the literal shell operator `<<`. The problem was in the terminal command text, **not** in `aggregation.py` or the hotspot algorithm. Re-running the demonstration as a Python one-line command produced the successful ranking reported in Section 8.5. No Python source changes were required.

This is a genuine **verification-command formatting** incident, not evidence of a repaired application defect.

### 8.7 Team-level integration and QA evidence

The team integration and QA document (`chenchen-integration-and-qa-design.md`) records a **19-passed Delay Analysis and Hotspots** run on 6 November 2026 and a **415-passed full post-fix regression suite in 96.27 seconds** on 7 November 2026. These are **separate team QA executions**, not the author's local runs and not additive to the 25 distinct targeted local tests above.

The team report also describes verification of historical prediction-delay analysis and hotspot map interactions. For the underlying detailed report, see [`docs/testing/sprint5-final-integration-test-report.md`](../../testing/sprint5-final-integration-test-report.md) if that path exists in the final repository.

### 8.8 Evidence boundaries and remaining verification

- Local test results are reported as text; the hotspot ranking demonstration uses synthetic data.
- The pipeline tests and the team-wide regression do not independently prove live feed completeness, statistical representativeness, actual vehicle arrival times, or production uptime.
- A real historical-data example of route/stop/time-period aggregation can be added if available and appropriately attributed.
- The final repository commit, exact production API response contract and deployment configuration should be checked against the team's latest `main` branch before handover.

## 9. Code review notes and final checks

The uploaded functions already have descriptive docstrings, and the hotspot function documents its ranking order and provisional threshold. Before handover:

- Check whether the project's wider documentation uses **positive delay** and **late service** consistently; the implementation distinguishes `d > 0` from `d > 5`.
- Confirm that all downstream consumers expect exactly the category strings `Early`, `On Time`, `Delayed`, and `Severely Delayed`.
- Confirm that upstream records provide `route_id`, `stop_id`, `time_period` and finite numeric `delay_minutes` values when the full output is requested.
- Confirm the business justification for the `0/5/10`-minute boundaries and the provisional `min_services=10` default with the project team or client.
- Keep local verification results distinct from team QA and production acceptance; rerun the documented commands when needed.

## 10. Summary

The delay and reliability component provides consistent signed delay calculations, four-category punctuality classification, reusable performance metrics, grouping by route/stop/time period, and a deterministic stop-level hotspot ranking. The implementation is suitable for descriptive reliability analysis when valid records are supplied. Its main interpretation risks concern the chosen thresholds, sample representativeness, upstream data quality and the distinction between a positive delay and an operationally late arrival. Local targeted testing and a controlled hotspot demonstration are documented above; team-level QA is separately attributed. Production data and deployment limitations remain applicable.
