# Historical collection reliability and recovery

**Latest validation:** [SCRUM-270 revalidation — 29 October 2026](#scrum-270-revalidation--29-october-2026).
Local checks passed; CASR production uptime, Task Scheduler and real power-loss
recovery remain unverified. **v2.1 remains ON HOLD.** The SCRUM-189 sections
below preserve the original Sprint 3 evidence and test counts.

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

## SCRUM-270 revalidation — 29 October 2026

This section supersedes the older production-evidence status above. Tested base:
`efd8a7e2ebd24bf11595f803b1e14fca663dba40` (SCRUM-268 PR #69 and SCRUM-269
PR #70 integrated). The October CASR backup failed integrity validation; its
cause is unknown and this does not establish corruption of the live collector.
It was not opened for this task. No independently verified replacement was
provided for this validation. **v2.1 remains ON HOLD** for unresolved realtime
stop_sequence compatibility. Local tests do not establish production uptime.

### Scope and existing architecture

Windows BAT resolves its application root and configured Python/static/DB/log
paths, then invokes `backend.services.historical_collection`. The CLI acquires
the Windows mutex, loads `stop_times.txt` and builds the exact index before
schema initialisation. `GTFSRealtimeProcessingPipeline` provides its collector
to `run_collection_and_persist`: fetch vehicles then trips, decode, validate,
convert, adapt, persist one transaction, log, wait, repeat. The standalone
processing pipeline does not persist. Existing Sprint 3 integration and Sprint 4
database/backend reports were reviewed as historical evidence, not new CASR
measurements. C05 already implemented the reliability/recovery tests below;
SCRUM-270 reuses them without rebuilding functionality.

Reviewed sources include realtime client/config/collector/decoder/validation/
pipeline, historical runner, database repository/models/storage helpers,
online backup, Windows mutex and BAT launcher. Operational procedures remain in
the [Windows guide](../deployment/windows-historical-collector.md) and
[CASR handover](../handover/casr-gtfs-data-collection-and-access.md).

### Environment, scenarios and outcomes

Local Windows; existing project Python 3.12.4; fresh temporary SQLite databases,
injected feeds and bounded subprocesses. Checkpoint explicitly configured to
900 seconds. No live requests, continuous unattended collector, real reboot,
production/demo database access, migration or deployment occurred.

**117 existing tests passed in 19.09 seconds; zero failures/errors/skips.**
Modules: realtime client, collector, decoder, validation, logging, processing
pipeline and persistence; historical runner, deployment, reliability and storage
optimisation; GTFS integration. Supplemental experiments passed separately and
are not counted as additional pytest cases.

Final documentation-delivery review reran the 117-case selection plus API,
analysis, hotspots, GTFS time-edge, database repository and historical-record
tests: **187 passed in 22.25 seconds**, zero failures/errors/skips. This is a
fresh expanded targeted run, not the historical C05 187-test full-suite result
above. Supplemental experiments were rerun successfully as well. Fresh outputs
are `final-review-tests.txt`, `final-review-tests.xml` and
`final-review-experiments.json` in the external evidence directory; the initial
117-test run and its 19.09-second timing remain the earlier validation record.

| Scenario | Expected and observed outcome | Evidence |
| --- | --- | --- |
| Valid protobuf cycle | Both record types processed, transactional inserts and successful ledger row | Existing collector/pipeline/persistence tests passed |
| Connection/timeout/429/5xx exhaustion | Three total attempts, two 5-second retry waits, next scheduled cycle after 60-second wait succeeds | Historical reliability tests passed |
| HTTP 408 | Three attempts, waits `[5,5]`, bounded exhaustion | Supplemental experiment passed |
| HTTP 403 | One attempt and no immediate retry | Existing and supplemental tests passed; future scheduled cycles still retry after polling delay |
| Empty/malformed feed and invalid entities | Decode failure skips cycle; invalid entities do not discard valid neighbours | Existing tests passed |
| Setup/write/ledger/COMMIT failure and actual write lock | No partially committed history/state/ledger; later cycle recovers | Existing historical reliability fault-injection tests passed |
| Restart / abrupt exit before commit | Existing history preserved, journal recovery and state reuse | Existing bounded subprocess tests passed |
| Shutdown | Stop event prevents another cycle; CLI handles injected KeyboardInterrupt; connections close | Existing tests passed; no power-loss durability claim |
| Mutex | Second process rejected, then restart allowed; abrupt-exit handle release | Actual local Windows subprocess tests passed, same session only |
| Logging | Startup, retry, decode/entity skips, persistence failures, success and shutdown observable; actual bounded rollover | Existing logging/reliability tests passed |
| Long simulated sequence | 360 bounded simulated cycles with injected faults and restart, consistent ledger/state/history | Existing test passed; simulated time is not unattended production duration |

Default request timeout is 10 seconds, with two retries after the first attempt.
Polling is a 60-second delay after work; retry/processing time adds to the cycle
duration. Permanent errors are not immediately retried, but the scheduler keeps
attempting later cycles. A handled failure can leave a finite CLI run returning
zero: verify completed-cycle logs and ledger activity, not exit status alone.

### Explicit retention and recovery evidence

One synthetic Trip Update per cycle, fixed trip/route/stop and scheduled arrival;
no Vehicle Positions in this small count experiment. Expected inserts matched
actual inserts in every row. The wider existing tests exercise both record types.

| Observation offset (s) | Delay (s) | Expected/actual inserts | History rows | Current-state rows | Ledger rows |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 60 | 1 / 1 | 1 | 1 | 1 |
| 60 | 60 | 0 / 0 | 1 | 1 | 2 |
| 900 | 60 | 1 / 1 | 2 | 1 | 3 |
| 960 | 120 | 1 / 1 | 3 | 1 | 4 |
| 960, duplicate | 120 | 0 / 0 | 3 | 1 | 5 |

The +900 observation is a checkpoint (last-seen gap 840 seconds, last-stored
gap 900). Changed state is stored immediately; repeated state is suppressed.
These five input observations are not five retained history rows or actual
arrivals. No production growth rate was calculated.

The existing `create_sqlite_backup` was called while a controlled source writer
held `BEGIN IMMEDIATE` with an uncommitted state change. Backup contained the
committed state, excluding the uncommitted change. Writer rollback left source
bytes/SHA-256 unchanged. A second online backup into a distinct recovery path
produced matching counts: 3 history, 1 current-state, 5 ledger, 0 vehicle rows.
Source, backup and recovery each returned `PRAGMA integrity_check = ok`.
Existing recovery tests also resumed collection in a recovered database while
preserving source and snapshot. Missing-source, same-source/destination and
existing-destination refusals passed; timestamp naming is covered by the suite.

The utility uses the SQLite online backup API and checks destination integrity;
it does not prove source provenance, timetable compatibility, completeness or
power-loss durability. It has no overall backup deadline or atomic exclusive
destination reservation for competing backup processes. Concurrent destination
creation, persistent lock contention, disk-full and real power-loss scenarios
were not tested. Coordinate one backup job and unique paths; larger operational
hardening is a follow-up, not a change in this validation. Failed output may
remain and must not be distributed as a verified backup. Never substitute a
plain filesystem copy of an active SQLite file for this procedure.

### Windows deployment and observability checklist

An exact BAT copy ran in a disposable installation from a different working
directory: missing Python returned 2; missing static file returned 3; configured
real interpreter with `--help` returned 0 and displayed correctly rooted DB/log
paths. This validates prerequisite/path dispatch only, not live collection.
Dependencies were reviewed against `requirements-collector.txt`; no new runtime
was installed. The real local mutex tests cover duplicate processes and restart.

| Area | Local status | CASR evidence still required |
| --- | --- | --- |
| Startup and continuous loop | Locally verified, bounded simulation | Actual Python/dependency versions, configured absolute paths, static hash, launch and sustained logs |
| Retry/error handling | Locally verified | Real feed access, freshness, outage/error monitoring |
| Persistence/checkpoints | Locally verified | Verified production backup and ledger/log correlation |
| Backup/recovery | Locally verified including active transaction | Operator backup logs, source/transfer hashes, retention and restore drill |
| Duplicate protection | Locally verified within one Windows session | Dedicated account/task; no overlapping instances or separate collectors |
| Logging | 5 MiB rotation, five backups; rollover verified | Writable log path, monitoring ownership and adequate retention |
| Task Scheduler | Instructions reviewed, not actual CASR settings | Startup trigger, account, filesystem permissions, restart-on-failure, non-overlap, command and Start-in directory |
| Power recovery | Not verified | Firmware power restoration, sleep policy, controlled reboot and recovery evidence |
| Production integrity/uptime | Not verified; supplied backup failed | Separately verified source-side snapshot and corresponding logs |
| Static compatibility / release | Unresolved / HOLD | Producer sequence semantics and feed linkage resolved before release approval |

Existing Scheduler guidance includes startup delay, dedicated account, explicit
cmd/BAT path and working directory, restart every five minutes for three attempts,
and no overlapping tasks. These are recommendations, not confirmation of CASR
configuration. Task Scheduler End can terminate abruptly; it is not equivalent
to graceful Ctrl+C. No CASR host settings were accessed or changed.

Logs distinguish successful, failed and skipped cycles; the ledger records only
successful transactions and often uses feed observation time. Missing intervals
or stale/repeated timestamps do not prove process downtime. Correlate logs,
ledger, source freshness and host/task events; unknown periods remain unknown.
Raw protobuf payloads are not intentionally logged, and configured public URLs
contain no credentials. However URL/error logging is not a general redaction
layer: do not put credentials in URLs or log messages; review logging before any
authenticated-feed change. No credential-bearing endpoint was used in testing.

### Handover decision and reproducibility

Local controlled acceptance checks passed. Full CASR operational acceptance is
**pending**, not production-ready. Obtain a source-verified replacement backup,
validate integrity read-only before analysis, then confirm scheduler/reboot,
monitoring ownership and sustained operation using client evidence. Resolve
stop_sequence compatibility before reconsidering v2.1. The failed backup does
not establish the cause or condition of the live CASR database.

No application code, schema, frontend, static matching or deployment configuration
was changed. This report extension is the only repository change. During the
initial local validation, no commit, push, PR, merge, deployment package or
release was made; subsequent documentation delivery does not approve deployment.

External evidence directory for this run: `scrum270-evidence` in the task
workspace, outside the Git worktree. `tests.xml` contains all 117 case names and
outcomes; `tests.txt` records the run; `experiments.json` contains cycle counts,
hash and launcher outputs. `scrum270_experiments.py` beside that directory
reproduces the supplemental tests using fresh temporary data. Run the named
pytest modules above with checkpoint environment value 900; never point tests
at CASR data. All waits/processes are bounded; synthetic experiment files are
removed on completion. The prior regression counts above remain historical.
