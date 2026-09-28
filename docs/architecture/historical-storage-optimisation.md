# Historical SQLite storage optimisation

## Why the schema changed

The C04 CASR snapshot covered approximately 72 hours and occupied 5.590 GiB.
It contained 684,212 Vehicle Positions and 16,547,359 Trip Updates. Trip Update
tables and indexes accounted for about 96.9% of the file, and 58.47% of Trip
Update rows repeated an unchanged logical state at a new collection timestamp.
All 16,547,359 rows also satisfied:

```text
actual_arrival = scheduled_arrival + delay_seconds
```

The optimisation keeps the 60-second collection interval. It changes how
repeated predictions are represented instead of reducing source resolution.

## Representative benchmark

Every candidate used the same real window, 2026-09-26 09:00–12:00 Adelaide
time: 875,591 Trip Updates and 35,297 Vehicle Positions. Query timings are the
median of five warm executions on the generated SQLite database.

| Strategy | Size | Reduction | Trip rows retained | Indexed source rows/s | Time query | Route query | Stop query | Delay query |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 272.47 MiB | 0.00% | 875,591 | 169,199 | 3.275 ms | 2.468 ms | 0.602 ms | 14.071 ms |
| Change + 15-minute checkpoint | 123.23 MiB | 54.77% | 381,248 | 256,179 | 1.333 ms | 1.087 ms | 0.357 ms | 6.871 ms |
| INTEGER timestamps | 129.58 MiB | 52.44% | 875,591 | 145,807 | 2.936 ms | 8.788 ms | 0.674 ms | 13.367 ms |
| Remove `actual_arrival` | 227.75 MiB | 16.41% | 875,591 | 177,059 | 3.594 ms | 9.236 ms | 1.140 ms | 14.878 ms |
| Remove redundant route index | 262.27 MiB | 3.74% | 875,591 | 178,115 | 4.046 ms | 11.242 ms | 0.678 ms | 15.364 ms |
| Selected combination | 55.86 MiB | 79.50% | 381,248 | 189,357 | 1.379 ms | 4.311 ms | 0.313 ms | 6.113 ms |

The wider `(route_id, timestamp, stop_id)` and `(stop_id, timestamp, route_id)`
index experiment grew to 287.7 MiB and was rejected. ID normalisation was not
selected because the safer candidates already exceeded 79% reduction without
mapping tables, joins, or a risky identifier migration.

## Full C04 replay

The selected design was then applied to the complete read-only C04 snapshot.

| Measurement | Legacy snapshot | Optimised disposable DB |
|---|---:|---:|
| File size | 5.590 GiB | 1.028 GiB |
| Trip Update rows | 16,547,359 | 7,204,094 |
| Vehicle Position rows | 684,212 | 684,212 |
| SQLite integrity check | `ok` | `ok` |

Measured storage reduction was **81.62%**. The retained Trip Update history
contained 678,944 initial states, 6,396,477 state changes, 128,671 checkpoints,
and 2 long-gap reappearances. The persistent current-state table contained
678,944 logical keys, and the cycle ledger contained all 3,495 collection
timestamps.

| Full-data query | Legacy median | Optimised median | Result |
|---|---:|---:|---|
| Time range | 3.516 ms | 1.550 ms | 2.27× faster |
| Route aggregate | 47.276 ms | 45.830 ms | Comparable |
| Stop aggregate | 20.317 ms | 1.738 ms | 11.69× faster |
| Trip history | 0.447 ms | 0.263 ms | 1.70× faster |
| Delay aggregate | 15.926 ms | 17.047 ms | 7% slower, still low latency |
| Route + stop + time | 0.021 ms | 0.153 ms | Slower but still sub-millisecond |

A real 5,645-row repository cycle completed in 0.068 seconds for initial
states, 0.065 seconds when all states were unchanged, and 0.092 seconds when
all states changed. This is well inside the 60-second collection interval.

Using the same 3.0158-day C04 span, measured linear growth falls from about
1.99 GB/day to about 0.366 GB/day. The estimated optimised sizes are 2.56 GB
after one week, 10.98 GB after 30 days, and 32.93 GB after 90 days. These remain
short-window estimates rather than capacity guarantees.

## Checkpoint choice

| Checkpoint | Rows retained | Row reduction | Maximum unchanged-state evidence gap |
|---|---:|---:|---:|
| 5 minutes | 422,422 | 51.76% | 5 minutes |
| 15 minutes | 381,248 | 56.46% | 15 minutes |
| 30 minutes | 376,301 | 57.02% | 30 minutes |

Moving from 5 to 15 minutes materially improves storage. Moving from 15 to 30
minutes saves only another 0.56 percentage points while doubling the liveness
evidence gap, so 15 minutes is the default. It is configurable through
`ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS`.

## New Trip Update representation

`trip_updates` stores:

- `trip_id`, `route_id`, `stop_id`
- `scheduled_arrival` as UTC epoch seconds (`INTEGER`)
- `delay_seconds`
- `observed_at` as UTC epoch seconds (`INTEGER`)
- `observation_kind`: initial, change, checkpoint, or reappearance

`actual_arrival` is reconstructed at the repository boundary, and callers still
receive Adelaide ISO-8601 values. A supplied value is validated before writing;
an inconsistent arrival rolls back the complete collection transaction.

The retained indexes are:

- unique state/observation protection beginning with `trip_id`
- `stop_id`
- `observed_at`
- `(route_id, stop_id, observed_at)`, whose route prefix replaces the redundant
  single-column route index

## Change, checkpoint, and restart behaviour

The logical identity is `(trip_id, route_id, stop_id)`. The state is
`(scheduled_arrival, delay_seconds)`.

- First observation: store immediately.
- Changed state: store immediately.
- Unchanged state: update current-state liveness but do not append history.
- Fifteen minutes since the last stored state: store a checkpoint.
- Same state reappearing after a checkpoint-length absence: store a
  reappearance observation.

`trip_update_current_state` is updated in the same transaction as history. It
survives process and computer restarts, so restart does not cause a full feed
snapshot to be appended again. `collection_cycles` stores one small row for
every successful cycle, distinguishing “collector ran and state was unchanged”
from “collector was offline”.

## Compatibility

The Python repository continues accepting ISO-8601 records and returning
`scheduled_arrival`, derived `actual_arrival`, `delay_seconds`, and `timestamp`
in Adelaide ISO format. Direct SQL consumers must use the new physical column
names and derive actual arrival.

The old and new databases should not be joined by assuming identical physical
schemas. Analysis can use the repository/export boundary or separate adapters.

## Safe CASR rollout

1. Keep the 5.590 GiB database unchanged as a read-only archive.
2. Back it up with the existing SQLite online backup command.
3. Deploy the merged code and refreshed batch/documentation package.
4. Configure `ADELAIDE_METRO_DATABASE_PATH` to a new filename, for example
   `adelaide_metro_history_v2.db`.
5. Run one bounded cycle and confirm schema version 2, log output, cycle ledger,
   state table, and history rows.
6. Run several more cycles and confirm unchanged updates are suppressed while
   changed updates and checkpoints are stored.
7. Re-enable the scheduled continuous collector and monitor file growth.

There is no destructive in-place migration and the old file is not required to
restart collection. A separate conversion is suitable for analysis benchmarking
but is not a production deployment prerequisite.
