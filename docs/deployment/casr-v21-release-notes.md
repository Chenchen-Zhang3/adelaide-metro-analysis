# CASR Windows Deployment v2.1 — release notes

Updated 21 October 2026. A final build uses reviewed main and records its exact
source commit, build time, file hashes and official static feed provenance in
`release-manifest.json`. Candidate builds use `candidate-manifest.json` and
remain subject to review. Build status does not establish client deployment;
delivery requires completed local checks and an agreed handover.

## Changes

- Includes the merged C05 continuous-operation memory-retention fix: only the
  latest successful collection result is retained during an unbounded run.
- Adds operational handover, safe update/rollback and production-evidence
  guidance. Packaging uses an explicit collector-only file allowlist.
- Includes official `stop_times.txt`; review its recorded feed coverage before
  deployment and do not overwrite a newer client feed without agreement.

## Unchanged

- Existing v2 database schema, persistence/state/checkpoint semantics and
  configuration interfaces; no migration or replacement of historical data.
- Default 60-second post-attempt polling delay and 900-second unchanged-state
  checkpoints. Finite runs still retain all successful results.
- Existing BAT interpreter contract and same-session Windows mutex. The
  separate unmerged launcher hotfix is not included.

## Client action

Confirm the actual DB path and configuration, make and verify an online backup,
agree maintenance, stop the existing writer, update application files while
preserving the DB, restart once and inspect completed-cycle logs plus data.
Verify scheduling as the configured account; reboot recovery remains pending
client evidence. See [operations and handover](casr-v2-operations-and-handover.md).

## Limitations

Local compatibility and smoke checks use disposable databases and controlled
inputs, not the CASR machine. No new genuine CASR v2 backup was available for
production measurement. Earlier replay savings are not production growth data.
The finite runner can exit 0 after a handled failed cycle: check logs and ledger.
No new stop-control channel or cross-session mutex guarantee is introduced.

## Suggested handover message (team leader to send after approval)

Hi Jamie and Martin,

We have prepared a v2.1 collector update containing the continuous
collection memory-retention fix and updated operating/backup guidance. The v2
database format is unchanged; the update is intended to preserve your existing
database and settings. Please do not replace or delete the current database.

Before we arrange delivery and a short maintenance window, could you confirm
the current startup method, application version, Python and database paths,
whether the BAT works, and the Task Scheduler configuration? Please also share
a timestamped SQLite online backup and recent collector logs through our agreed
channel. Two dated backups will help us measure actual database growth.

We will confirm the reviewed package hash and safe update steps with you before
deployment. Automatic restart and successful operation of this update at CASR
remain to be verified. No intentional power interruption is needed.

Thank you.
