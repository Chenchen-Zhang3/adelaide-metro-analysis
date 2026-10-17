# Static and historical GTFS ID consistency

SCRUM-231 / S4-C01. Validated locally on 2026-10-14, from main
`6e558c1` (includes C05). Scope is ID validation and handover guidance;
no collector, storage, frontend, geometry or recorded-demo implementation changed.

## Sources and provenance

Static source: local archived Adelaide Metro feed at
`GTFS/google_transit.zip`, with extracted files in `GTFS/google_transit/`.
The declared publisher is Adelaide Metro. `feed_info.txt` identifies version
**1692**, valid **2026-08-20 to 2026-10-11**. The original download URL/time
is not recorded in that archive, so a filesystem modification time is not
claimed as a feed release or download date. No new download was necessary.

Archive size: 17,350,649 bytes. SHA-256:
`a964fda81ff3c76c7b9a89f4b14225b42bf4dc832b6b950957493552fa25906d`.
All six checked extracted files match their archive entries byte-for-byte.

| Static file | Available evidence |
| --- | --- |
| routes.txt | 731 distinct routes, 180,537 bytes |
| trips.txt | 26,250 distinct trips, 1,179,879 bytes |
| stops.txt | 9,173 distinct stops, 1,468,002 bytes |
| stop_times.txt | 971,202 rows; 970,460 distinct trip/stop pairs; 51,305,489 bytes |
| shapes.txt | Present, 40,514,418 bytes; geometry not analysed in C01 |
| feed_info.txt | Publisher, version and coverage dates preserved |

Historical source: unchanged CASR original
`CASR historical data/original/adelaide_metro_history_20260928_165052.db`.
It is a **legacy physical schema**, not a v2 production database:
684,212 Vehicle Positions and 16,547,359 Trip Updates, 6,001,827,840 bytes.
Vehicle observations cover 2026-09-25 16:27:05 to 2026-09-28 16:49:50
Adelaide time; Trip Updates cover 16:28:06 on the 25th to 16:49:06 on the 28th.

Only earlier optimisation benchmark v2 databases were found locally; none is
represented as a new client production backup. That backup remains pending.

The deployment ZIP's `stop_times.txt` is a different file (50,341,744 bytes,
SHA-256 `9cc557bf81307af0d4d6a6604603c11d5437e795ffa661a87cc609fc7bb506b2`).
Do not mix it into the complete version-1692 static directory or claim the
collector's exact static feed version has been proven by this audit.

## Method and reproducibility

`backend.services.gtfs_id_consistency` reuses `parse_routes`, `parse_trips`,
`parse_stops` and the existing `build_stop_time_index` key convention. Stop
times are streamed in 5,000-row batches; only unique trip/stop pairs survive
each batch. IDs are compared exactly as strings, preserving zeros and case.
No stripping, numeric coercion, padding or heuristic ID substitution is applied.

The history is opened with `mode=ro`, `query_only=ON` and a consistent read
transaction. SQL `GROUP BY` streams distinct identifiers with row weights;
the 16.5 million Trip Update rows are not loaded into Python. The audit groups
18,350 vehicle trip/route combinations and 678,944 Trip Update trip/route/stop
combinations. Only counts, file fingerprints and ten bounded examples per
category are exported. SQLite temporary sort storage is configured for disk.

Source byte size and modification time are checked before and after validation;
they remain unchanged. No migration, schema creation, DML, VACUUM, index change
or repository initialisation is run on the source.

```powershell
python -m backend.services.gtfs_id_consistency --static-dir "PATH\GTFS\google_transit" --static-archive "PATH\GTFS\google_transit.zip" --database "PATH\original\adelaide_metro_history_20260928_165052.db" --output "PATH\analysis\gtfs-ids-new.json"
```

The output must be a new JSON file. Existing evidence is never overwritten.
Missing static files are reported as unavailable rather than zero-percent
matches. The validator also supports v2 `observed_at` without sending legacy
history through the current v2 repository helpers.

## Results

Percentages use unique non-NULL/non-empty realtime IDs as the denominator.
The combined column is a union, not the sum of per-source unique counts.
Missing IDs are reported separately; none were found in this snapshot.

| Identifier | Static unique | Vehicle unique / matched | Trip Update unique / matched | Combined unique / matched | Match |
| --- | ---: | ---: | ---: | ---: | ---: |
| route_id | 731 | 379 / 379 | 379 / 379 | 380 / 380 | 100% |
| trip_id | 26,250 | 18,350 / 18,350 | 18,343 / 18,343 | 18,559 / 18,559 | 100% |
| stop_id | 9,173 | Not present in vehicle contract | 7,328 / 7,328 | 7,328 / 7,328 | 100% |

All 684,212 vehicle rows have a trip-to-route mapping consistent with trips.txt.
All 16,547,359 Trip Update rows have consistent trip-to-route mappings, and
all 678,944 distinct trip/route/stop groups have a compatible trip/stop pair in
stop_times.txt. There are zero missing static trips, missing stops, absent
trip/stop pairs, route conflicts, whitespace issues or non-string historical IDs
in these comparisons. Static ID duplicates/conflicting trip routes and missing
static trip/route or stop-time references were not observed.

There are no genuine unmatched-ID examples to list. Synthetic tests exercise
unknown routes/trips/stops, route conflicts, absent pairs, missing identifiers,
whitespace and ambiguous static mappings without inventing real mismatches.
Static IDs unobserved during a three-day sample are not validation failures.

## What these results do not prove

- Stored Trip Updates have already passed the collector's static stop-time
  enrichment. Raw feed records without a matching index entry can be skipped
  before storage. Therefore 100% stored-ID coverage is not 100% raw-feed coverage.
- Version-1692 coverage includes the September observation dates, but exact
  production static-version equivalence is not proven. ID reuse can retain
  membership while schedules change. A newer feed may legitimately have new
  or retired trips; preserve both feed manifests before attributing a mismatch
  to a parsing defect.
- This verifies membership and mappings, not service calendars, scheduled
  arrival equality, complete trip coverage, stop order or route geometry.
  History does not retain stop_sequence, so repeated visits to one stop cannot
  be matched to an exact `(trip_id, stop_id, stop_sequence)` here.
- No source parsing/integration bug was identified. New code is an audit utility
  only, with focused tests; existing runtime interfaces remain unchanged.

## Integration contract

| Value | Handover rule |
| --- | --- |
| route_id / trip_id / stop_id | Exact GTFS strings as in shared JSON schemas; preserve leading zeros, case and punctuation. Use route_id, not route_short_name, as the join/filter key. |
| Optional vehicle trip/route IDs | Retain null where allowed by the existing vehicle contract; report separately rather than manufacture an ID. |
| Trip to route | Resolve trips.trip_id to trips.route_id; membership alone does not validate that relationship. |
| Route to stop | Join routes → trips → stop_times → stops; it is many-to-many, not one route per stop. |
| stop_time_index | Preserve existing `(trip_id, stop_id, int(stop_sequence))` convention. The audit's pair membership is deliberately weaker because history has no sequence. |
| timestamp | Historical observation time in Adelaide ISO-8601 at the Python/API boundary; v2 stores epoch internally and derives actual_arrival. Preserve September dates for recorded replay. |
| Frontend | Keep string IDs in JSON and URL-encode them for route/stop API paths. Existing map/API code already follows this pattern. |

The raw historical snapshot has zero routes/stops/trips/stop_times reference
rows. Consequently ID matching alone does not make `/api/routes`, `/api/stops`
or stop-to-route joins populated. Current repository Trip Update queries expect
v2 columns; do not point the prototype at the original legacy database. SCRUM-233
must prepare a separate demo database or explicit adapter, preserving the source.
The existing Sprint 3 fixture seeder is synthetic and is not a real-data loader.

Shared trip-update JSON permits nullable/omitted arrival fields, while v2 writes
require scheduled_arrival for derivation. The recorded-demo handover must honour
the stricter persistence boundary already documented in the database handover.

## Inputs recommended for SCRUM-233

Use September history and the complete pinned version-1692 static feed.
Keep the archive/hash manifest, feed_info, and small audit JSON together.
Representative fully compatible route/trip/stop examples, ranked by historical
Trip Update row volume, include:

| route_id | trip_id | stop_id | Compatible route history rows |
| --- | --- | --- | ---: |
| G10 | 1134894 | 100425 | 495,905 |
| M44 | 945469 | 100256 | 378,955 |
| H30 | 1028977 | 100232 | 364,553 |
| 506 | 1027468 | 100083 | 291,320 |
| 300 | 1134716 | 100000 | 276,354 |

These are membership-verified candidate keys, not a ready replay dataset or
a guarantee that both feed types overlap at a chosen instant. SCRUM-233 should
select a bounded time window, verify per-vehicle/trip overlap and analysis
coverage, populate static reference tables in a separate demo store, and expose
the existing API contract. Row volumes include repeated predictions and are not
counts of completed services. Geometry remains S4-C02 work.

Version 1692 ends on 11 October; it is suitable for replay of September data,
not evidence of current service on the tentative 19 October demonstration date.
Label the demo as recorded data and preserve its original observation timezone
and dates. Do not shift timestamps to pretend the recordings are live.

## Evidence, tests and completion

Machine-readable real-data evidence is committed as
`docs/integration/evidence/gtfs-id-consistency-1692.json`; the same full audit is
saved under `CASR historical data/analysis/gtfs-id-consistency/` outside Git.
Only a small report is committed, not CSV source files or historical databases.

Focused validation and related parser/converter/repository/pipeline/API/analysis
regression tests: **88 passed**, including 16 new audit tests. C05 reliability
tests were not unnecessarily repeated because its implementation was unchanged.

SCRUM-231's ID-consistency work is ready for PR review and can be accepted as
Done after review. This is not a claim that the demo is ready: separate demo
store population, time-window selection and API wiring remain SCRUM-233 inputs;
route geometry remains S4-C02. A fresh v2 production backup is still useful for
later validation but is not a blocker for these September ID results. Jira was
not updated; no automatic merge or next-task implementation was performed.
