# SCRUM-268 — GTFS stop, route and trip integration

Validated locally on 26 October 2026. Clean PR base:
`59cbe6486f211dcf10754d7e4cc318411a61b7e3` (`origin/main`).
Earlier validation evidence was generated from the isolated baseline
`ecdc47794e788f3bbf4f5a7b9d635eb3f7386d4e`; results from that baseline are
identified below. No SCRUM-236 commits or additional files are included.

## Executive summary

The existing static-to-realtime-to-history workflow is reusable beyond the
three-route demo. One bounded fix rejects duplicate normalised static stop-time
keys instead of silently selecting the last timetable row. Validated feeds
1692 and 1710 remain accepted, and the saved public snapshot produces the same
1,635 exact matches and 58 sequence conflicts against 1710.

Local validation and the targeted fix are ready for review. Runtime route-to-trip
and calendar/version enforcement remain incomplete; upstream sequence semantics
remain unresolved. This is not production integration or v2.1 release approval.
The malformed CASR backup was not accessed. v2.1 remains HOLD; this PR does
not authorise deployment.

## Existing architecture

| Stage | Existing implementation | Integration boundary |
| --- | --- | --- |
| Static parsing | `backend/parsers/static_gtfs.py` | CSV parsers for routes, stops, trips and stop-times; preserve string IDs and integer sequences |
| Mapping | `backend/services/gtfs_converter.py` | Exact `(trip_id, stop_id, stop_sequence)` lookup; supplied service date determines schedule date |
| Feed processing | `backend/realtime/{validation,collector,pipeline}.py` | Validate supported fields, decode, convert, prepare records; injectable client/index |
| Historical adapter | `backend/services/historical_records.py` | Required identifiers, normalised optional fields, existing record contract |
| Persistence | `backend/services/pipeline.py`, `backend/database/repository.py` | One transaction for history, state and successful-cycle ledger |
| Queries | Repository, `backend/api/app.py`, `backend/services/vehicle_history.py` | Route/stop queries, parameterised history filters and bounded vehicle playback |
| Geometry | `backend/services/recorded_map_data.py` | Generic shape extraction; publisher and artifact labels remain recorded-demo-specific |

The runner loads a stop-time index before schema/pipeline initialisation. It
does not import all routes/stops/trips dimensions. The physical model has no
calendar tables, route `agency_id`, trip `shape_id`, or static-feed provenance
on historical rows. History does not preserve the original `stop_sequence`.

## Dataset provenance and validation scope

| Input | Applicable period | Evidence |
| --- | --- | --- |
| Static 1710 | 2026-10-16 through 2027-04-09 | Pinned official archive; SHA-256 `ef06c7e3a8e5d8613505db3c7b66d87328c02bb3bb599ab5d2054eb23b654c55` |
| Static 1692 | 2026-08-20 through 2026-10-11 | Historical archive; SHA-256 `a964fda81ff3c76c7b9a89f4b14225b42bf4dc832b6b950957493552fa25906d` |
| Saved public Trip Updates | 2026-10-21, header `2026-10-21T13:14:06Z` | 99 trips / 1,693 stop updates; SHA-256 `623d636c741920c60975a70c906232260b4da935606a348b409866ada10dea38` |
| New automated fixtures | Synthetic October service date | BEL, J1G, REGIONAL; leading-zero trip IDs; temporary SQLite only |

The earlier validation verified both archive hashes against SCRUM-267, so its
full structural checks were reused by byte identity: 1710 has 716 routes, 9,161 stops, 21,691 trips,
804,594 stop-times and 1,763 usable shapes. 1692 has 731/9,173/26,250/971,202
respectively. Both archives were additionally rebuilt into the updated lookup
and replayed during that baseline validation. Their source hashes remained
unchanged. These saved measurements are not a fresh replay on the clean PR base.

The full feed includes regional/school services. The agency-name-defined
Adelaide Metro subset in SCRUM-267 has 561 routes and 7,693 referenced stops;
it is not an administrative geographic boundary. The 120 stops not directly
referenced by stop-times are parent stations with child platforms.

The public snapshot is not CASR history or evidence of present-day operation.
No new live-feed request was made. The September demo database was not needed.
1692 is used only as an explicitly incompatible October comparator.

## Mapping results and confirmed limitations

| Check | Result |
| --- | --- |
| Correct trip/route/stop identities | Synthetic BEL/J1G/REGIONAL feeds pass parsing, conversion, adapter, persistence, stop-to-route API and route performance queries |
| Unknown trip/stop or wrong exact sequence | Skipped; no trip/stop-only or ordinal fallback |
| Missing route | Entity rejected by existing validation; valid entities continue |
| Repeated visits, gaps and terminal 999 | Exact visits remain distinct; unrelated sequence values are skipped |
| String identifiers | Leading-zero synthetic trip IDs remain unchanged through persistence |
| Duplicate exact static key | Before fix, row order chose 08:00 versus 09:00; after fix, `ValueError` before schema/pipeline creation |
| Route disagreement | Converter copies a nonempty realtime route ID; it has no static trip catalogue to verify it |
| Feed/calendar selection | An exact key alone can still convert on an incompatible date; runtime index contains no validity/calendar metadata |

The last two limitations are characterised by a named regression test, not
declared fixed. Adding speculative rejection without the required static
context would change the supported interface without proving correctness.
A separate dataset-context design is needed to enforce trip/route/service/date
relationships consistently across the runner and pipeline.

The exact-key guard is not a complete GTFS validator. Duplicate
`(trip_id, stop_sequence)` rows using different stop IDs are outside this guard;
the independent structural audit checks that stronger constraint. Partial
indexes built in separate batches cannot detect duplicate keys across batches.
Validated inputs remain a prerequisite.

## stop_sequence compatibility

The saved baseline evidence records an offline audit of the pinned bytes:

| Metric | 1710 | 1692, diagnostic only |
| --- | ---: | ---: |
| Stop updates / eligible entries | 1,693 | 1,693 |
| Exact matches / converter output | 1,635 | 317 |
| Mapping skips | 58 | 1,376 |
| Unique-pair sequence mismatches | 58 | 47 |
| Missing trip entries | 0 | 569 |
| Missing trip-stop pair entries | 0 | 759 |
| Missing global stop entries | 0 | 1 |
| Active-service trip entities | 99 | 0 |
| Trip/route disagreements | 0 | 36 |

The 1710 exact-match rate is 96.5741%. All 58 conflicts again have dense-ordinal
characteristics in this particular snapshot. That does not establish a safe
producer contract or a global offset. Static 1710 also contains 548 repeated
trip/stop pairs, and terminal 999 must remain supported exactly.

`convert_trip_update` and `is_valid_stop_time_update` are unchanged. No sequence
normalisation, unique-pair fallback or global offset was introduced. The
compatibility findings above and v2.1 HOLD remain in force. The earlier audit
script and extended compatibility document belong to the preserved SCRUM-236
baseline, not this PR. This report summarises their saved results without a
relative link to files absent from `main`; neither is a runtime or test
dependency of the duplicate-key fix.

## Persistence and backend readiness

All 1,635 matched public observations cover 99 trips and 63 route IDs, including
BEL, J1G, rail/tram and many routes outside G10/M44/506. Three controlled cycles
used original observation timestamps, then synthetic +60 and +900 second
offsets; predictions/service dates were retained. A new disposable database
stored 1,635 initial rows, suppressed 1,635 unchanged rows on cycle two, then
stored 1,635 checkpoints on cycle three. Final history/state/ledger counts were
3,270 / 1,635 / 3, and integrity was `ok`. The temporary database was removed.

The saved results agree with the existing 900-second retention threshold:
cycle two updates `last_seen_at` without storing the unchanged state; at cycle
three, the gap from `last_seen_at` is 840 seconds and the gap from
`last_stored_at` is 900 seconds. Thus the final inserts are checkpoints
(`observation_kind=2`), not reappearances. Predictions and service dates do not
advance in this controlled experiment. The original helper did not explicitly
set the checkpoint environment override; a new reproduction must pin
`ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS=900`.

These are controlled replay results, not raw observation counts or production
coverage. The 58 mapping skips occur before unchanged-state suppression.

Repeated visits retain distinct converter records and scheduled arrivals, but
the durable current-state identity is `(trip_id, route_id, stop_id)`, without a
visit sequence. It must not be interpreted as one independent current-state
row per stop visit. Redesigning that existing storage identity is outside this
bounded integration fix.

| Capability | Readiness and boundary |
| --- | --- |
| Routes/stops and stop-to-route APIs | Reusable without a three-route allowlist; dimensions must actually be loaded |
| Historical route/stop/time filters | Reusable; depend on suitable retained observations, with no automatic static-version reconciliation |
| Trip queries | Internal trip/stop-time joins and vehicle trip IDs exist; no dedicated public trip-detail or trip-history filter endpoint |
| Unknown stop | Detail 404; stop-to-routes returns an empty list, preserving current API behaviour |
| Recorded map-data | G10/M44/506 artifacts remain demo-scoped; no citywide publisher added |
| Dataset selection | Deployment/manual input responsibility; no automated version/calendar/agency selection |
| Historical analytical semantics | API `actual_arrival` derives from predicted GTFS arrival; confirmed actual arrival is not established |

No frontend, citywide publishing, database schema or deployment changes are
included. Static network scope cannot establish realtime collection coverage.

## Changes and tests

Changed application behaviour: `build_stop_time_index()` now raises
`ValueError("Duplicate static stop-time key: ...")` when a normalised identity
already exists. This also rejects identical duplicates rather than hiding bad
input; valid inputs retain the same dictionary interface and values.

Changed files:

- `backend/services/gtfs_converter.py`: four added lines.
- `backend/tests/test_gtfs_integration.py`: eleven focused parametrised cases,
  including startup-before-write and a multi-route temporary-SQLite integration.
- This report.

| Test stage | Result |
| --- | --- |
| Existing selected baseline | 153 passed in 15.72s |
| New tests before fix | 4 expected defect failures, 7 passed |
| Earlier selected suite on isolated baseline | 164 passed in 14.27s; final review rerun 164 passed in 12.96s |
| Saved public fixture persistence replay | Expected 1,635 / 0 / 1,635 inserts; integrity `ok` |
| Clean PR base regression and integration suite | 206 passed in 24.74s across 18 modules; no failures |

The clean-base suite includes this integration module, the existing static
parsing/converter/time-edge/ID checks, realtime validation/collector/pipeline,
historical adapters/pipeline/repository/runner/deployment tests, APIs, map
artifacts, analysis, historical reliability and storage optimisation. It
preserves the latest `main` analysis behavior and omits the unmerged SCRUM-236
compatibility test module. The earlier count of 164 belongs to its original
baseline and must not be read as the clean branch's test count.

From the repository root, with the project's test dependencies available:

```powershell
python -m pytest -p no:cacheprovider -q `
  backend/tests/test_static_gtfs.py backend/tests/test_gtfs_converter.py `
  backend/tests/test_gtfs_time_edges.py backend/tests/test_gtfs_id_consistency.py `
  backend/tests/test_realtime_validation.py backend/tests/test_realtime_collector.py `
  backend/tests/test_realtime_processing_pipeline.py backend/tests/test_historical_records.py `
  backend/tests/test_pipeline.py backend/tests/test_database_repository.py `
  backend/tests/test_historical_collection_runner.py backend/tests/test_historical_deployment.py `
  backend/tests/test_api.py backend/tests/test_recorded_map_data.py `
  backend/tests/test_gtfs_integration.py backend/tests/test_analysis.py `
  backend/tests/test_historical_reliability.py backend/tests/test_historical_storage_optimisation.py
```

Earlier selected test modules cover static parsing, converter/time edges,
GTFS ID audit, SCRUM-236 sequence compatibility, realtime validation/collector/pipeline,
historical adapters, persistence, repositories, runner/deployment helpers, APIs
and map artifacts. Existing dependencies are reused; pytest is loaded from the
external SCRUM-267 dependency directory. No project environment was installed
or changed. Full repository discovery and CASR runtime were not tested.

## Acceptance and next steps

| Requested acceptance area | Assessment |
| --- | --- |
| Inspect actual integration before editing | Complete; baseline defect demonstrated before the patch |
| Validate positive/negative relationships beyond the demo | Complete within documented fixtures and saved public snapshot |
| Investigate sequence cases without speculative remapping | Complete; upstream resolution remains open |
| Assess backend readiness | Complete, with explicit runtime version/route and map-publisher limitations |
| Implement justified small improvement and tests | Complete locally; duplicate-key fix and regressions pass |
| Preserve data/work | Complete; original review worktree and SCRUM-236 branch retained; clean PR branch starts from current main |

The task's local validation/fix deliverables are complete and reviewable.
Universal route/date correctness and release readiness are not satisfied by
these results. Prioritise a separately reviewed static context carrying feed
identity, validity, trip-route/service relations and calendars; retain strict
stop identity matching. Obtain authoritative sequence semantics before changing
conversion. Extend citywide artifacts separately and revalidate historical
coverage only after CASR supplies a verified replacement backup.

## Reproducibility and evidence

Outputs are separate from production datasets:

```text
D:\Adelaide study\2026\ICT Capstone Project\GTFS\analysis_outputs\scrum268-20261026
```

`baseline-tests.txt`, `regression-before-fix.txt`, `final-tests.txt` and their
JUnit XML files record actual results. `public-snapshot-audit-1710.json` and
`public-snapshot-audit-1692.json` contain complete offline categories and bounded
examples. `public-fixture-persistence.json` records the three synthetic cycles;
`input-preservation.json` records before/after hashes. `scrum268-summary.json`
and `repository-evidence.json` provide structured metrics and source hashes.

`reproduce.ps1` records the earlier baseline commands; `scrum268_replay.py` only reads the two
known static archives and saved public protobuf, blocks feed HTTP and creates a
new temporary database. Reproduction should use a fresh output directory or
preserve existing evidence before rerunning. Do not point it at an existing
database. The malformed CASR backup is not a test input or a script parameter.

Those external helpers are retained evidence, not portable PR test commands:
they use the original worktree and its SCRUM-236 audit script. Replaying their
full audit requires that preserved baseline. The regression tests in this PR
use only synthetic inputs and temporary SQLite, and require no external feed,
CASR database or SCRUM-236 files. The evidence files are outside Git and must
be supplied separately if another reviewer needs to reproduce the saved
snapshot measurements.
