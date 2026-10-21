# CASR v2 collector operations and handover

Updated 21 October 2026. Application update: **CASR Windows Deployment v2.1**.
The ZIP manifest identifies a candidate or a final main-based build. Local
validation and an agreed client maintenance window are required before delivery
and installation. CASR startup and sustained operation still require evidence.

The collector records Adelaide Metro Vehicle Positions and Trip Updates for
historical analysis. Service Alerts are not persisted by this historical
collection contract. Missed realtime history cannot be recovered from the feed.

## Release and compatibility boundary

The previously delivered v2 package was built from
`7f2bbd6784439142ecdfc1b7b66819477f9fdedb`, ZIP SHA-256
`907ACB86DB823991C6B6131A0E8F683F4A2027969C5B0373C2940EBFF1C250CF`.
Read `release-manifest.json` in a final ZIP, or `candidate-manifest.json` in a
candidate ZIP, for the exact source commit, build time and per-file hashes.
Final builds must use the exact fetched `origin/main` commit. The build label
does not establish that the package has passed validation or reached CASR.

The merged C05 fix retains only the latest successful result during continuous
collection; finite runs still return all successful results. The v2 schema,
database write code and default polling/checkpoint settings are unchanged from
the delivered v2 source. No database migration, reset or VACUUM is part of this
update. Disposable old-code/new-code compatibility and snapshot recovery checks
passed locally; they do not validate the unknown current CASR database.

The separate `feature/windows-launcher-hotfix` commit
`af4910e990c25de7b85a302d1e1f918532a560a7` is **not included**. Its interpreter
discovery and diagnostics may be useful, but the original CASR failure is not
known. Keep that change separate: choosing a global interpreter could select
different dependencies, and v2.1 retains the documented explicit
`.venv`/`ADELAIDE_METRO_PYTHON` contract.

## Runtime and configuration

Follow [Windows setup](windows-historical-collector.md) for Python 3.12,
installation of `requirements-collector.txt`, BAT commands and Task Scheduler
fields. This collector-only package does not include the web application,
Flask, demo databases or analysis artifacts. It includes the small analysis
Python modules imported by the existing pipeline.

Install into a writable local directory, not a synchronised live-DB folder.
Keep enough free disk space for the growing DB and at least one full snapshot.
Use an account with read access to the application/static files and write access
to the production DB, its directory, logs and backup destination. Outbound
HTTPS to the Adelaide Metro feeds is required.

| Variable | BAT default / meaning |
| --- | --- |
| `ADELAIDE_METRO_PYTHON` | Application `.venv\Scripts\python.exe`; explicit absolute executable path supported |
| `ADELAIDE_METRO_STATIC_GTFS_PATH` | Application `data\static_gtfs`; must contain `stop_times.txt` |
| `ADELAIDE_METRO_DATABASE_PATH` | Application `data\historical\adelaide_metro_history_v2.db` |
| `ADELAIDE_METRO_LOG_PATH` | Application `logs\historical_collector.log` |
| `ADELAIDE_METRO_POLLING_INTERVAL_SECONDS` | `60`, delay after each attempt, not a strict wall-clock cadence |
| `ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS` | `900`, unchanged-state checkpoint interval |

Preserve actual client settings. Use **absolute paths** for an existing DB,
static data, interpreter and logs when changing application directories. The
Python module alone has different path defaults; use the BAT or supply every
environment value explicitly. Environment settings in a VS Code terminal are
not automatically inherited by Task Scheduler. Configure them for the task's
actual account/launch context and verify resolved paths in its output.

Before an application update, set the confirmed existing file explicitly in
the same PowerShell process that launches the BAT:

```powershell
# Replace the example with the actual existing CASR path confirmed by its operator.
$database = 'C:\CASR\data\historical\adelaide_metro_history_v2.db'
if (-not (Test-Path -LiteralPath $database -PathType Leaf)) { throw 'Existing database not found' }
$env:ADELAIDE_METRO_DATABASE_PATH = (Resolve-Path -LiteralPath $database).Path
```

The BAT changes its working directory to its own application root. An unset
database variable therefore selects that installation's `data\historical`
file; a relative override is also interpreted from that application root.
Moving the application without the absolute override can select a different
file. The Python connection creates missing parent directories and SQLite
creates a missing DB; startup does not check that an intended old file exists.
The existence check above is mandatory for updates. Schedule the same absolute
configuration for the actual task account; the interactive assignment alone
does not configure Task Scheduler.

Only official `stop_times.txt` is needed. It is loaded once per process.
Record static archive/hash/feed version from the candidate manifest, compare
with the client's current feed, and agree a refresh during maintenance.
Do not silently replace a newer client feed with an older packaged feed.
Refresh from the official static source if it no longer covers deployment:
<https://gtfs.adelaidemetro.com.au/v1/static/latest/google_transit.zip>.
Keep the previous static file for rollback, separately from the live database.

The v2.1 static baseline is official feed 1710 (2026-10-16 to 2027-04-09),
804,594 stop-time rows. September recorded-demo feed 1692 is a separate artifact
and must not be substituted. A static refresh rebuilds the in-memory index at
restart; it does not rewrite old database history or clear persisted state.
Trip Updates match `(trip_id, stop_id, stop_sequence)` exactly. Unmatched keys
are skipped; changed schedule times can produce new state-change observations.
Review realtime/static ID coverage before deployment. Feed validity dates alone
do not prove that a live snapshot uses that feed version. Record capture times
and matched/unmatched counts, investigate widespread mismatch, and withhold
release approval until any compatibility concern is resolved.

## Startup, shutdown and scheduling

From the application root, first run one bounded cycle:

```powershell
.\scripts\start_historical_collector.bat --max-cycles 1
```

Do not run this while the production collector is already active. Check for a
**completed** cycle in logs and a corresponding new `collection_cycles` row.
Exit code 0 is not sufficient: handled feed/SQLite errors skip a cycle and a
bounded run can still exit normally. Then start continuous collection through
the agreed single Task Scheduler task, not a second VS Code process.

Use one dedicated account and the Windows guide's startup trigger, delayed
start, restart-on-failure settings and **Do not start a new instance** option.
Set Program to `cmd.exe`, use the fully quoted BAT path as its `/c` argument,
and set **Start in** to the application root. Confirm credentials, folder
permissions, power/sleep restrictions and any execution-time limit. A retrying
collector may stay alive during feed failures; Task Scheduler's restart on
process failure is not a feed-health monitor.

The Windows mutex protects against duplicate collectors in the **same session**.
Cross-account/cross-session exclusion is not verified and must not be assumed.
Before starting, the client should inspect task status and running Python
command lines across relevant accounts/sessions, not just the current desktop.
Do not terminate an unrelated Python process. Keep only one designated writer
to the production database.

Interactive `Ctrl+C` is handled as a clean shutdown. Disable scheduled triggers
and pending automatic restarts during maintenance. The current unattended
launcher has no dedicated graceful-stop control channel. Task Scheduler **End**
can terminate the process and is not equivalent to `Ctrl+C`. If that is the
only available control, coordinate with the operator, take a verified online
backup first, wait for the between-cycle log, stop the task, confirm process
exit, and verify SQLite integrity before proceeding. Do not hot-swap files.
No deliberate power-off test is requested.

## Data and health checks

Historical storage metadata should report version `2`. Important tables:

- `vehicle_positions`: deduplicated positions; its timestamp remains TEXT.
- `trip_updates`: INTEGER schedule/observation times, derived actual arrival;
  observation kinds `0 initial`, `1 change`, `2 checkpoint`, `3 reappearance`.
- `trip_update_current_state`: durable state used to suppress unchanged
  predictions after restart.
- `collection_cycles`: successful-cycle ledger and received/stored/suppressed
  Trip Update counts. Failed cycles have no successful ledger entry.

Logs rotate at 5 MiB with five backups. Look for startup/static-index loading,
completed cycles, retry exhaustion, SQLite errors and shutdown messages.
Requests default to a 10-second timeout, up to two retries after the initial
attempt and 5-second retry delays for retryable failures. See
[reliability evidence](../architecture/historical-collection-reliability.md).

Unchanged Trip Update history counts do not prove downtime. Repeated/stale
feed timestamps and deduplication can also leave history counts unchanged.
Ledger timestamps may describe feed observations rather than collector
wall-clock execution. Use logs, feed freshness and successful-cycle counts
together; do not convert ledger gaps directly into uptime claims.

## Consistent backup and recovery

Use SQLite's online backup, never an ordinary copy of an actively written DB:

```powershell
# Set this to the EXISTING confirmed production path before running.
$database = 'C:\CASR\data\historical\adelaide_metro_history_v2.db'
if (-not (Test-Path -LiteralPath $database -PathType Leaf)) { throw 'Existing database not found' }
.\.venv\Scripts\python.exe -m backend.services.historical_backup --database "$database" --output-dir 'C:\CASR\backups'
```

The command refuses an existing destination, creates a timestamped snapshot and
runs `PRAGMA integrity_check`. Record the completed snapshot path, size, SHA-256,
backup time/timezone and source path. Keep multiple dated snapshots according to
CASR's agreed retention/storage policy; no automated retention job is installed.
Transfer only the completed snapshot and relevant redacted logs to the team.

Before an update, inspect the snapshot read-only and record counts for all four
historical tables and schema metadata. To test restoration, copy the **closed
snapshot** into a separate recovery directory, verify integrity and counts,
and run a bounded test only against that isolated copy. Never overwrite the
live DB or test a second writer against it.

If actual production recovery is necessary, obtain explicit client approval:
stop all writers, preserve the affected original and sidecars for diagnosis,
restore to a **different** path, verify integrity/schema/history, configure that
path deliberately and restart one collector. Restoring an older backup can
lose later history; report the recovery point. Do not delete or routinely
rename the current live database.

## Safe v2 -> v2.1 update checklist

1. Client confirms running process, application version/path, account/session,
   actual DB path, interpreter, static feed, log path and existing task settings.
   Record baseline history/state/ledger counts from a consistent snapshot.
2. Agree maintenance and rollback owner. Create and verify the online backup.
   Retain the prior application and static files; never bundle its live DB.
3. Disable triggers/restarts, stop the current collector using the applicable
   shutdown procedure above, and verify there is no remaining writer.
4. Extract the reviewed candidate to a separate application directory.
   Verify ZIP hash/source and inspect release notes. Create a fresh Python 3.12
   venv there and install `requirements-collector.txt`; do not copy an old venv.
5. Explicitly preserve `ADELAIDE_METRO_DATABASE_PATH` as the existing v2 DB.
   Preserve polling/checkpoint values and other approved configuration.
   Confirm the DB file exists before launch. Never allow a new application's
   default relative path to silently create an empty replacement DB.
6. Check static version/coverage with the operator and preserve or refresh it
   deliberately. Confirm DB/log directory permissions for the task account.
7. Run one bounded cycle with no other writer. Inspect completed-cycle logs,
   integrity, retained old history and new ledger/state data. If startup fails,
   leave automatic restart disabled and collect console/error output.
8. Update the existing scheduled task's application/working directory and
   configuration, then run that task. Verify subsequent completed cycles and
   logs as the scheduled account, including unchanged suppression/checkpoints.
9. Re-enable agreed triggers only after these checks. Request evidence of the
   startup trigger and operation after the next authorised normal reboot;
   local testing does not establish CASR reboot recovery.
10. If rollback is needed, stop the new writer, preserve the current DB and a
    fresh online backup where possible, then restore **application/config/static
    selection**, pointing prior compatible v2 code at the same DB. Do not roll
    the DB back to the pre-update snapshot as an ordinary code rollback.
    The old version still has the continuous memory-retention issue; use this
    only as a monitored temporary fallback pending team assistance.

## When a genuine production backup arrives

The team must first confirm provenance with CASR: source machine/path, collector
version, collection interval, backup command/time/timezone, and associated logs.
A filename alone does not establish that it is production data.

1. Hash and preserve the received original. Copy the closed snapshot to a
   separate validation location; open with SQLite URI `mode=ro`. Do not call
   application `create_tables`, migrate, VACUUM or start collection on it.
2. Run the following read-only SQL (SQLite CLI or a read-only Python connection).
   Save the results with the snapshot hash and validation time:

```sql
PRAGMA integrity_check;
SELECT * FROM schema_metadata;
SELECT name, sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name;
SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM vehicle_positions;
SELECT COUNT(*), MIN(observed_at), MAX(observed_at) FROM trip_updates;
SELECT observation_kind, COUNT(*) FROM trip_updates GROUP BY observation_kind;
SELECT COUNT(*) FROM trip_update_current_state;
SELECT COUNT(*), MIN(observed_at), MAX(observed_at) FROM collection_cycles;
SELECT COUNT(*) AS inconsistent_ledger FROM collection_cycles
 WHERE trip_updates_received != trip_updates_stored + trip_updates_suppressed;
SELECT COUNT(*) AS invalid_state_times FROM trip_update_current_state
 WHERE last_stored_at > last_seen_at;
SELECT * FROM (
 SELECT id, observed_at,
 observed_at-LAG(observed_at) OVER (ORDER BY id) AS feed_gap_seconds
 FROM collection_cycles
) WHERE feed_gap_seconds > 180 OR feed_gap_seconds <= 0;
SELECT trip_id, route_id, stop_id, scheduled_arrival, delay_seconds,
 IFNULL(observed_at,-1), COUNT(*) FROM trip_updates
 GROUP BY trip_id,route_id,stop_id,scheduled_arrival,delay_seconds,IFNULL(observed_at,-1)
 HAVING COUNT(*) > 1;
SELECT vehicle_id, IFNULL(trip_id,''), IFNULL(route_id,''), latitude, longitude,
 IFNULL(timestamp,''), COUNT(*) FROM vehicle_positions
 GROUP BY vehicle_id,IFNULL(trip_id,''),IFNULL(route_id,''),latitude,longitude,IFNULL(timestamp,'')
 HAVING COUNT(*) > 1;
```

3. Investigate any non-`ok` integrity result or non-v2 schema before other work.
   Cross-check state rows against each key's latest retained observation;
   investigate missing/inconsistent states, while allowing legitimate aged-out
   states and subsequent reappearance. Trace sample keys through observation
   kinds and checkpoint intervals. Query plans/large scans may take time.
4. Correlate gaps/repeated timestamps with logs and feed freshness, treating
   negative/repeated timestamps as investigation signals, not proven outages.
5. Record DB bytes and timestamp span. A single snapshot gives an endpoint
   size, not sustained growth. Request two or more timestamped consistent
   snapshots plus runtime logs/settings; compare bytes and row deltas per
   elapsed wall-clock day, allowing free pages and variable traffic.
6. Report actual production measurements separately from synthetic/local tests.
   The historical 81.62% reduction (5.590 to 1.028 GiB) is a controlled replay
   benchmark only, not measured CASR production savings.

## Responsibilities and outstanding evidence

CASR owns machine access, account permissions, Task Scheduler, backups/retention,
maintenance approval and the actual deployment. The team owns candidate review,
hash/source provenance, compatibility tests, backup analysis and support.
The team must not publish this candidate or change the client's machine without
the agreed handover.

| Item | Status as of this handover |
| --- | --- |
| Current collector running now | AWAITING CASR EVIDENCE; earlier “I've got it working now” did not identify version/method or current health |
| BAT launch at CASR | AWAITING CASR EVIDENCE |
| Task Scheduler and reboot recovery | AWAITING CASR EVIDENCE |
| Existing-v2 update compatibility | LOCAL VERIFIED on an old-code-created disposable DB; actual CASR file still pending |
| Genuine new v2 backup / production validation | AWAITING CASR EVIDENCE; no genuine backup identified in local project directories |
| Sustained production growth | AWAITING CASR EVIDENCE |
| C05 deployed at CASR | AWAITING CASR EVIDENCE; delivered old v2 predates the fix |
| Candidate delivery and CASR startup | AWAITING CASR EVIDENCE; not sent by this task |
| Legacy database migration | NOT APPLICABLE to this v2-to-v2.1 update |

Request: current startup command/method and resolved paths, process/version and
account/session, BAT output, task settings/export and last-run result, relevant
redacted logs, verified online backup(s) with timestamps/hash, measured disk
growth, and approval of maintenance/delivery. Do not request passwords or secrets.

Local engineering readiness, reviewed package readiness, delivery, and verified
production operation are separate milestones. Do not mark the full production
handover complete solely because local tests pass.
