# CASR v2.1 static/realtime compatibility investigation

Date: 21 October 2026 (Australia/Adelaide). SCRUM-236.
**Outcome C: HOLD / NOT READY TO SEND.** The local cause of strict-join
failures is explained below; the producer's reason for conflicting sequences
and a general safe reconciliation contract remain unconfirmed. Production
matching/persistence code and the pinned static feed are unchanged.

## Source and current matching rules

Fetched main: `49c0705cebf3da4f75fc77e77b139b863ed8b110`.
SCRUM-236 is merged through PR #66. Final metadata/provenance correction
`c7f6633` is merged through PR #67. C05 is present; the separate launcher
hotfix remains excluded. No final release ZIP was created by this investigation.

Actual path through the implementation:

1. `backend.parsers.static_gtfs.parse_stop_times` parses CSV sequences as ints.
2. `backend.services.gtfs_converter.build_stop_time_index` uses string trip/stop
   IDs plus integer sequence as the exact dictionary key. Sequence gaps are
   retained; array position is not used. Duplicate exact keys would overwrite,
   so the audit checks for them: **zero** in feed 1710.
3. `backend.realtime.validation.is_valid_trip_update` requires trip, route and
   service date. `is_valid_stop_time_update` requires stop ID, nonzero sequence
   and absolute arrival time. These are the collector's supported-data rules,
   not a complete GTFS validity validator: a valid departure-only, stop-only or
   zero-sequence observation can be outside this implementation's coverage.
4. `convert_trip_update` skips unsupported entries and missing exact static
   keys. It selects the static arrival on `start_date` in Adelaide time,
   including times after 24:00, and calculates predicted arrival minus schedule.
5. `GTFSRealtimeCollector._convert_trip_updates` prepares the records for the
   repository; `GTFSRealtimeProcessingPipeline.process_once` returns them.
   Static lookup skips currently have no per-entry production log reason;
   the offline audit makes these categories visible without changing runtime.
6. `persist_realtime_collection` commits history, durable state and the cycle
   ledger in one transaction. Unchanged suppression happens **after** conversion.

## Specification boundary

The [GTFS Schedule reference](https://gtfs.org/documentation/schedule/reference/#stop_timestxt)
allows increasing non-consecutive stop sequences. Gaps in a static pattern do
not by themselves indicate an invalid timetable.

The [GTFS Realtime reference](https://gtfs.org/documentation/realtime/reference/#message-stoptimeupdate)
relates a supplied sequence to the corresponding static schedule and uses it
to distinguish repeated visits to the same stop. Stop ID can identify a unique
visit when sequence is absent, but that is different from resolving two
supplied identifiers that contradict each other. A global offset is unsafe.
This sample declares realtime specification **1.0**; the current reference's
newer semantic guarantees must not be assumed for its producer.

## Evidence and reproducibility

The previous 2,908/3,151 result is retained as historical evidence only. Its raw
protobuf was not saved; only totals, examples and payload hash remain. Exact
replay of that snapshot is therefore unavailable. The following is a **new**
measurement, not a reproduction of those counts.

One Trip Updates request was saved from:
`https://gtfs.adelaidemetro.com.au/v1/realtime/trip_updates`.

- Retrieved: `2026-10-21T13:14:19.2408616Z` / 23:44:19 Adelaide.
- Header observation: `1792588446` / `2026-10-21T13:14:06Z`.
- Snapshot age at capture: about 13 seconds.
- Payload SHA-256:
  `623d636c741920c60975a70c906232260b4da935606a348b409866ada10dea38`.
- All 99 trips specify service date `20261021`; static calendars/exceptions
  mark all 99 services active. No route disagreement or start_time override
  was observed. The header does not identify the source static feed version.

Pinned official static **1710**, validity 2026-10-16 through 2027-04-09:

- 804,594 stop-time rows and 804,594 exact keys; no duplicate-key overwrite.
- Archive SHA-256:
  `ef06c7e3a8e5d8613505db3c7b66d87328c02bb3bb599ab5d2054eb23b654c55`.
- stop_times SHA-256:
  `27a89074977f68a388becff076a7e00b316b786ef3d5a17cf08f66d6580a240f`.
- A diagnostic download of official `static/latest/google_transit.zip` at
  13:14:20Z was byte-identical. Packaging data was not replaced.

Evidence is preserved outside Git in:

```text
D:\Adelaide study\2026\ICT Capstone Project\CASR historical data\analysis\release_compatibility_20261021_131419
```

Files: `trip_updates.pb`, `official-static-1710.zip`, `capture-provenance.json`,
`audit1710-ordinals.json`, `audit1692.json`, `controlled-persistence-result.json`.
The September archive is only a diagnostic comparator, never the release feed.

Replay offline from the repository root; output must be a new file:

```powershell
python scripts/audit_static_realtime_compatibility.py --static-zip <official-static-1710.zip> --snapshot <trip_updates.pb> --output <new-audit.json>
```

This command performs no HTTP or database writes. It reports current converter
output alongside structural matches and arrival eligibility.

## Counts and actual converter impact

| Stage/category | Count | Denominator/meaning |
| --- | ---: | --- |
| Trip Update entities / unique trips | 99 / 99 | Feed entities |
| Stop-time entries examined | 1,693 | All stop updates in those entities |
| Eligible before static lookup | 1,693 | Current supported-data rules; all have arrival time |
| Exact trip/stop/sequence matches | 1,635 | 96.5741% of 1,693 entries |
| Sequence conflicts with a unique trip/stop pair | 58 | 3.4259% of 1,693 entries |
| Missing trip IDs / global stop IDs / trip-stop pairs | 0 / 0 / 0 | Same 1,693 entries |
| Ambiguous repeated-stop pairs in the snapshot | 0 | Same 1,693 entries |
| Other conversion skips | 0 | Snapshot replay |
| Direct converter output | 1,635 | Actual function invocation |
| Collector database-ready output | 1,635 | Actual collector conversion |

Thus **58 supported arrival observations are filtered by static mapping in
this one snapshot**, before SQLite. This is not an estimate of CASR's missing
history, nor evidence that 3.43% of all production data is missing. The previous
7.71% was also a structural sample statistic, not a historical storage measure.

## Representative cases and confirmed pattern

All new cases below have service date 20261021 and active service in 1710.
Each conflicting pair has exactly one static visit. Current action is skip.

| Trip | Route | Stop | RT seq | Static seq | Static ordinal | Scheduled arrival | Shape |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 1183400 | J1G | 1212 | 52 | 53 | 52 | 23:41:07 | 13731 |
| 683703 | BEL | 6679 | 5 | 6 | 5 | 23:54:00 | 15016 |
| 925796 | 733A | 5513 | 11 | 12 | 11 | 24:05:00 | 16540 |
| 925797 | 733A | 6117 | 65 | 66 | 65 | 23:38:41 | 16540 |
| 925870 | 734A | 5857 | 33 | 34 | 33 | 24:16:38 | 16541 |

Matched counterexamples: trip 1086192 / GAWC / stop 6702 uses sequence 22 in
both feeds, scheduled 23:45:00, shape 3884; its terminal stop 6665 uses 999 in
both feeds despite having static ordinal 25. These records are kept.

Original reported example 1180165 / stop 417: static 1710 identifies route
400, shape 15338, scheduled 23:07:41, sequence 30, **ordinal 29**. The prior
report's realtime value 29 fits the same pattern. This trip was no longer in
the new snapshot; its old realtime service date/details cannot be rechecked.

All **58/58** current sequence conflicts have realtime sequence equal to the
1-based ordinal of that stop in the sorted static trip, while its static
sequence is ordinal + 1. They follow gaps in static numbering:

| Trips | Static gap | Conflicting entries |
| --- | --- | ---: |
| 1183400 | 24 -> 26 | 11 |
| 683703 | 4 -> 6 | 6 |
| 925796 and 925797 | 10 -> 12 | 32 + 4 |
| 925870 | 32 -> 34 | 5 |

This explains the observed mismatch mechanism: the realtime values compact the
numbering gap for these visits. It is not a universal zero-based convention:
entries before gaps match, and observed terminal 999 values remain 999. Nor
is it an array-index assumption introduced by this application's dictionary.

What remains a hypothesis: the producer may compact a stop list during its
own export, or use an internal timetable/variant with different numbering.
The public header provides no version linkage or export algorithm. Matching
the available latest archive rules out a stale *local latest-download* as the
simple remedy; it cannot establish the producer's internal source version.

## Other hypotheses checked

- **Version/time:** 1710 covers all observed service dates and is currently
  the published latest archive. Archived 1692 ends 11 October and has no active
  service for the 21 October sample. Replaying it yields only 317/1,693 exact
  matches (18.7242%), 569 missing-trip entries, 759 missing trip/stop pairs,
  one missing stop, 47 sequence conflicts and 36 route disagreements at entity
  level. It is not a suitable replacement or a source for mixing rows.
- **Producer documentation:** the official archive's `Release Notes.txt`
  mentions a database reversion following the October service change and
  Outer Harbour closure, but gives no sequence remapping contract. The
  [Adelaide Metro developer page](https://www.adelaidemetro.com.au/developer-info)
  refers to GTFS specifications and those release notes; it does not resolve
  the conflicting tuple fields. Connecting the reversion to these gaps would
  be speculation, not a confirmed producer root cause.
- **Repeated visits:** 1710 has 548 repeated trip/stop pairs globally. None
  are among this snapshot's examined relationships. A unique-pair workaround
  on these 58 does not prove a general loop-safe rule.
- **Parsing/indexing:** string IDs and integer sequences preserve identity;
  804,594 keys remain. Non-consecutive values and terminal 999 are handled.
- **Variants:** conflicts span bus and rail routes and four shape patterns;
  two 733A trips share shape 16540. There is no route-global offset to apply.
- **Internals:** no mismatched route, inactive calendar or missing absolute
  arrival explains these 58. Their contradictory stop/sequence relationship
  already exists in the decoded public protobuf.

## Fix decision and safety

No production converter defect causing these 58 conflicts is confirmed. Exact
identity matching is conservative and prevents inventing a schedule. No runtime
fallback, global offset, schema change or static replacement is implemented.

A unique trip/stop pair lets us list a candidate scheduled time, but does not
by itself establish which conflicting field is authoritative. Before a
fallback can be approved, obtain evidence linking the producer's timetable and
sequence semantics to this static schedule, including repeated visits, changed
patterns and terminal handling. A guessed offset cannot be justified from
current unique-pair coverage. The existing state key also lacks stop_sequence;
do not claim loop-history semantics were redesigned or validated here.

Current correctly matched records retain the exact selected schedule and raw
delay arithmetic. Correct delay for the 58 excluded entries cannot be approved
until their schedule association is confirmed. Do not reduce this uncertainty
to a target percentage or accept conflicting records merely to increase count.

## Controlled E2E, suppression and regression

Saved protobuf -> decode -> existing validation/static matching -> delay ->
record preparation -> SQLite v2 -> query was replayed without HTTP. An empty
Vehicle Positions feed isolates Trip Updates. Only disposable databases were
used; one sentinel history row existed before the replay.

| Controlled cycle | Observation timestamp offset | Converted | Inserted | Suppressed |
| --- | ---: | ---: | ---: | ---: |
| First | Original captured timestamps | 1,635 | 1,635 | 0 |
| Repeat | +60 seconds | 1,635 | 0 | 1,635 |
| Checkpoint | +900 seconds | 1,635 | 1,635 | 0 |

The +60/+900 timestamps are controlled test advances, not additional live
observations. Final history 3,271, current state 1,636, ledger 4 include the
preexisting sentinel. Integrity is `ok`; old history survives. Mapping skips
remain 58 per replay and are not counted as unchanged suppression.

Thirteen new tests cover exact/gapped/999 sequences, repeated visits with
correct schedule selection, conflicting/missing/ambiguous keys, missing
arrival, different static schedules, delay arithmetic, audit denominators and
decode-through-persistence restart/checkpoint behavior. Full scoped suite:
**275 passed, 1 deselected** in 31.43 seconds; the 360-cycle simulation was
deliberately not repeated. Existing v2 schema and collector code are unchanged;
backward-compatibility/recovery regression remains passing.

## Release gates and next evidence

| Gate | Assessment |
| --- | --- |
| A. Metadata/provenance | PASS — PR #67 merged, final-mode tests pass |
| B. Windows package integrity | PASS for existing validated artifacts/components; no new final ZIP built |
| C. Existing v2 compatibility | PASS locally; runtime/schema unchanged and regressions passing |
| D. Static/realtime compatibility | UNRESOLVED for the 58 conflicts |
| E. Correct delay calculation | PASS for exact associations; UNRESOLVED for conflicting entries |
| F. Data preservation | PASS — disposable writes only; original/demo/client data unchanged |
| G. Local tests | PASS — 275 passed, 1 deselected |
| H. CASR production verification | PENDING |

**Do not proceed to the final approved v2.1 build yet.** The next specific
technical evidence is a provider timetable/export mapping for the five trips
and the earlier 1180165 example: which static feed version was used, why gaps
are compacted but terminal 999 is preserved, and how repeated visits/variants
are represented. Alternatively obtain corresponding archived source timetables
that demonstrate a compatible mapping. Any proposed fallback needs separate
positive/negative and loop-safe regression review before approval.

CASR's backup/startup evidence remains a separate pending handover dependency.
Do not wait for that reply to inspect public-feed evidence; do not infer its
production results from this local sample. No contact with the provider or
CASR was made by this investigation.
