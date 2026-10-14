# Historical collection reliability and recovery

SCRUM-189 / S3-C05. Local Windows validation: 2026-10-13.
Base: `main` at `4dfe13452a85037651a20a55e6ea6382438251e9`.

## Scope and completion

Local engineering validation is complete and ready for PR review. CASR
production validation remains pending. The client reports that the updated
collector runs, but BAT startup, Task Scheduler startup/restart, a real v2
backup, and sustained v2 storage growth are not yet confirmed.

No Jira status was changed. No CASR machine, Task Scheduler setting, original
historical database, C04 output, or deployment ZIP was modified. The separate
`feature/windows-launcher-hotfix` (`af4910e`) is not incorporated.

## Existing architecture and previous coverage

- `HistoricalCollectionRunner` builds the static index, creates the schema and
  constructs its processing pipeline once per runner.
- `GTFSRealtimeClient` applies request timeouts; the collector retries connection
  and timeout errors, HTTP 408/429 and 5xx. Defaults are two retries, five seconds
  apart, in addition to the initial request. Permanent errors such as 403 are
  propagated without retry.
- The historical loop logs request, decode/validation and SQLite failures and
  continues after the normal 60-second wait. This is a delay after a completed
  attempt, not a guarantee of one successful cycle per wall-clock minute.
- One repository transaction covers vehicles, Trip Update history, persistent
  current state and the successful-cycle ledger; commit failure rolls it back.
- State identity remains `(trip_id, route_id, stop_id)`. State comparison remains
  `(scheduled_arrival, delay_seconds)`. INTEGER times and derived actual arrival
  are unchanged.
- Current state survives restart. Unchanged observations are suppressed until a
  900-second checkpoint; unchanged observations returning after an absence of
  at least 900 seconds are reappearances. A changed state takes precedence over
  reappearance classification. A shorter absence does not independently trigger
  a history row.
- Logging uses a console handler and an optional 5 MiB file with five backups.
  The CLI handles normal completion, Ctrl+C, fatal errors and duplicate startup.
- Windows startup uses a named mutex. Backup uses SQLite's online backup API
  with a read-only source and an integrity check on the completed destination.

Previous tests covered individual retries, validation, repository writes,
basic state/checkpoint behaviour, runner initialisation, one-file backup and
same-process mutex rejection. Missing evidence was the interaction of these
mechanisms over many cycles, whole-v2-table rollback, independent process
restart/crash, v2 restore, real rollover and cross-process Windows rejection.

## Confirmed defect and minimal fix

The historical loop appended every complete successful feed and persistence
result to its return list during unbounded operation. A 100-cycle regression
test on the original implementation retained all 100 payloads, proving that
the loop's memory ownership grows with successful-cycle count.

`run_collection_and_persist()` now retains only the latest successful result
when `max_cycles is None`. A bounded run still returns all successful results.
The regression test verifies that 99 old payloads become collectable after
100 unbounded-mode cycles. This does not claim a whole-process memory plateau;
it verifies the specific retained-result defect. The production CLI ignores
the return list. Fetching, polling, schema, records and persistence are unchanged.

## New automated evidence

All reliability tests are in `backend/tests/test_historical_reliability.py`.
They prohibit live HTTP, use disposable SQLite databases and injected waits,
and do not wait 15 actual minutes.

| Scenario | Verified result |
| --- | --- |
| Connection failure, timeout, HTTP 429/500/502/503 | Three failed request attempts, two five-second retry waits; failed cycle has no ledger/history; subsequent cycle persists after a 60-second polling wait. |
| Empty response / malformed protobuf | Processing failure is logged, no partial vehicle persistence, next cycle resumes. |
| Valid decoded empty feed | Successful zero-record cycle gets a ledger entry; it is not treated as a transport failure. |
| Invalid entities in decoded feeds | Aggregate skip warnings are emitted; decoded cycle can succeed with zero usable records. |
| Connection / BEGIN / vehicle insert / current-state write / ledger insert / commit failure | Failed attempt leaves all four v2 data tables unchanged; next attempt resumes. Real SQLite authorizer denial injects write failures; commit failure is injected before commit succeeds. |
| Actual SQLite write lock | A second connection holds `BEGIN IMMEDIATE`; timeout-zero test writer fails, rolls back, waits, then succeeds after lock release. Production connection timeout remains unchanged. |
| Connection release | All 30 successful persistence calls close their connection; failed opened connections close too. |
| Clean process restart | Two separate Python processes reuse one DB; unchanged state stays suppressed, changes store immediately and checkpoint timing continues from persisted state. |
| Abrupt process exit | Child exits via `os._exit(23)` at commit, after history/state/ledger writes, bypassing Python cleanup. Reopening SQLite restores the previous committed snapshot; another process resumes and integrity is `ok`. |
| Short / long key absence | Seven-minute unchanged reappearance is suppressed; sixteen-minute absence stores a reappearance. Successful empty-trip cycles still have ledger records. |
| Online backup / separate restore | Backup during an uncommitted writer transaction captures only committed state. All four v2 tables and schema version 2 match; a separate restored DB suppresses unchanged state and accepts changes without overwriting source or snapshot. All three databases have integrity `ok`. |
| Logging / shutdown | CLI start, normal stop, simulated Ctrl+C and fatal-error routes log the correct context and return codes; network and persistence tests assert failure visibility. |
| Actual rotating file rollover | Production limits are asserted; a smaller test threshold exercises real rollover, with current file plus five backups and latest messages retained. |
| Windows duplicate process / crash release | Actual Windows child process is rejected while parent holds the same mutex; a new child succeeds after release. Abrupt child exit also releases its unique test mutex. |
| Stale observation timestamps | Two successfully persisted copies of one old feed produce two ledger entries with identical observation times. |

## Controlled sustained simulation

The deterministic simulation attempts 360 one-minute observations, split into
two 180-cycle runners to exercise reinitialisation. Static-index loading and
pipeline construction occur once per runner, never per cycle. It injects nine
request timeouts, six actual-arrival consistency failures (real rollback) and
five invalid-feed processing failures. These injected errors are expected.
Separate full-collector tests exercise the actual feed retry and protobuf path.

| Metric | Result |
| --- | ---: |
| Attempted cycles | 360 |
| Successful cycles | 340 |
| Expected failed cycles | 20 |
| Vehicle rows | 340 |
| Trip Update history rows | 26 |
| Initial / change / checkpoint / reappearance | 1 / 8 / 16 / 1 |
| Persistent current-state keys | 1 |
| Collection-cycle rows | 340 |
| Mocked 60-second poll waits | 358 |
| Largest observed ledger gap | 180 seconds |
| SQLite integrity | `ok` |

No real polling sleeps occurred. Two runs each omit their final wait, hence
358 waits. Successful ledger times exactly match successful synthetic
observation times, and received = stored + suppressed for every ledger row.
An exclusive transaction can be acquired afterwards; no prior transaction
remains active. This six-hour simulated sequence is not proof of several days
of unattended operation on CASR hardware.

## Ledger interpretation and read-only operating checks

Use successful ledger entries, not an increasing Trip Update count, to check
continued persistence. The history count can stay fixed during normal operation.
The latest current-state `last_seen_at` helps inspect a particular key.

For cycles with timestamped records, ledger `observed_at` is the maximum source
record timestamp, not the runner's wall-clock execution timestamp. Empty cycles
use current epoch time. Stale feeds can repeat times; mixed feed timestamps and
clock movement can affect gap interpretation. The ledger does not store the
identity of every suppressed/absent entity or a failed-cycle row. Combine it
with logs, row order and feed freshness rather than treating gaps as an exact
downtime measurement or exact per-key reconstruction. No schema/helper change
is needed for C05's verification queries.

Open SQLite in read-only mode and run these checks:

```sql
SELECT id, observed_at, vehicle_positions_received, trip_updates_received,
       trip_updates_stored, trip_updates_suppressed
FROM collection_cycles ORDER BY id DESC LIMIT 10;

SELECT id, observed_at, gap_seconds FROM (
    SELECT id, observed_at,
           observed_at - LAG(observed_at) OVER (ORDER BY id) AS gap_seconds
    FROM collection_cycles
) WHERE gap_seconds > 90 ORDER BY id DESC LIMIT 20;
```

The 90-second example is an investigation threshold for 60-second polling,
not a universal outage alarm. Request/retry/processing time can lengthen the
interval. Investigate stale timestamps and log failures alongside larger gaps.

## Windows and production limitations

The unprefixed mutex provides tested same-session protection across processes.
Cross-session or cross-user singleton protection was not tested and is not
guaranteed. SQLite locks protect transactions, not singleton operation: two
collectors can run between transactions, duplicate polling and ledger entries,
or encounter contention. Use one scheduled task/account and “Do not start a
new instance”; check for separately launched VS Code collectors before startup.

The launcher on main still expects a project `.venv` unless an executable is
explicitly configured. Interpreter detection improvements remain separately
on `feature/windows-launcher-hotfix`; C05 neither merges nor changes that work.

| Evidence source | Status |
| --- | --- |
| Automated v2 recovery, restart, checkpoint, rollback and restore | Verified locally |
| Actual local Windows subprocess/mutex and file rotation | Verified locally |
| CASR feedback that updated collector runs | Reported by client; no new backup inspected |
| CASR BAT launcher | Awaiting confirmation |
| CASR Task Scheduler startup and automatic recovery after restart | Awaiting confirmation |
| CASR recent v2 backup, multi-day liveness and storage growth | Awaiting evidence |

Abrupt-process tests do not simulate power loss, disk failure, disk-full
conditions or production filesystem durability. No live-feed smoke test was
performed; complete synthetic protobuf-to-v2-persistence tests exercise that
path without external traffic. No permanent collector process remains.

Recommended checks: inspect recent success/failure logs and feed timestamps;
confirm ledger activity; create an online backup and verify its integrity;
retain old history as an archive; restart the intended single scheduled task;
then request recent logs and a v2 snapshot to verify recovery and storage growth.

## Regression results and handoff

Baseline backend suite: 152 passed. New C05 suite: 31 tests. Final complete
repository suite: **187 passed**, including Windows tests; no skips or failures.
The old root-level `delay_frequency` import failures have already been repaired
on latest main and did not recur. `git diff --check` passes.

Reproduce from the repository root with the project's test environment:

```powershell
python -m pytest backend/tests/test_historical_reliability.py -q -s
python -m pytest -q
```

C05 is locally validated and ready for PR review, awaiting production evidence.
If Done requires unattended production reliability, keep it pending until the
client evidence above is checked. C06 engineering can proceed if its acceptance
criteria do not depend on those unverified production claims. No automatic
merge or Jira transition is performed.
