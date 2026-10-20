# CASR v2.1 candidate validation record

Date: 20 October 2026. Jira: SCRUM-236. All results below are local engineering
evidence, not verification of the CASR machine.

## Source and scope

- Fetched `origin`; local main matched remote main
  `8e7e85c4ec0386d599719a6a522158a7ff3d2359`.
- SCRUM-235 is merged via PR #56, merge `2438874`; feature commit `3fe6c8d`
  is an ancestor of main. C05 (`8e39182`, merge `6e558c1`), SCRUM-231,
  SCRUM-232, SCRUM-233 and SCRUM-234 are also present.
- `feature/windows-launcher-hotfix` / `af4910e` remains separate from main;
  its BAT changes have not been incorporated in main and are excluded here.
  Discovery/diagnostics remain potentially useful but require independent
  review and actual client error evidence; fallback interpreter selection
  adds dependency/environment variability. No claim that it solves the
  previously reported CASR issue.
- No collector runtime logic is changed by SCRUM-236. Existing untracked demo
  assets were preserved. Source branch:
  `feature/SCRUM-236-casr-v2-validation-handover`.

## Production evidence

A recursive database/package inventory under the local ICT Capstone project
found the legacy September database, replay benchmark databases, demo datasets
and a local development DB. No genuine new CASR production v2 backup was
identified. These files were not opened for writing or used as production
evidence. Original legacy data and recorded demo data were not modified.

The original delivered v2 ZIP matched the client-history SHA-256
`907ACB86DB823991C6B6131A0E8F683F4A2027969C5B0373C2940EBFF1C250CF`.
Compatibility testing extracts that artifact and uses its code to create
synthetic data. No production database is included in either test or package.
The earlier client “I've got it working now” is historical startup feedback,
not confirmation of today's health, BAT, scheduling, reboot or C05 deployment.
The planned 19 October demonstration is not treated as evidence of a meeting.

## Reproducible checks

Run from the repository root using a test environment with pytest and project
dependencies:

```powershell
python -m pytest backend/tests tests -q -k "not bounded_360_cycle_simulation"
```

The final combined run passed **259 tests, 1 deselected** in 31.04 seconds;
the prior 360-cycle simulation was deliberately deselected. This includes
five additional packaging tests: committed
allowlist/manifest, no overwrite, output outside the repository, invalid static
columns and empty static data rejection.

Build only from an exact reviewed commit. Supply an official static ZIP
downloaded separately, and a new output path outside the repository:

```powershell
python scripts/build_casr_candidate.py --repo . --commit <exact-commit-sha> --static-zip <official-static.zip> --output <outside-repo-candidate.zip>
python scripts/validate_casr_candidate.py --package <outside-repo-candidate.zip> --old-source <verified-old-v2-extracted-root>
```

The validator must run on Windows with `requirements-collector.txt` installed.
The local run uses a fresh Python 3.12.4 venv with only
gtfs-realtime-bindings 2.2.0, protobuf 7.36.0 and tzdata 2026.5 (plus pip).
No Flask/pytest dependency is needed for the candidate validator/runtime.
This is a fresh runtime on the development Windows machine, not a separate
clean Windows installation or the client's scheduler account.

The candidate validator checks:

1. ZIP CRC, exact manifest membership, every file hash and unwanted artifacts.
2. Original delivered v2 code creates a disposable v2 DB with one successful
   cycle. Current code reopens it with identical schema and all nine table
   contents preserved.
3. A fresh current-code process adds a minute-1 cycle: two Vehicle Positions,
   one retained Trip Update, one current state, two ledger rows. Unchanged
   history is suppressed after restart.
4. Another process at minute 15 creates a checkpoint: three positions, two
   observations, one state, three ledger rows. Defaults remain 60/900 seconds.
5. SQLite online backup has `integrity_check=ok` and identical contents in all
   nine application tables. A copied closed snapshot accepts minute 16 with
   four positions, two observations, one state and four ledger rows; originals
   remain unchanged. Existing regression tests additionally cover backup
   during an uncommitted writer transaction.
6. Original v2 code accepts the candidate-written restored copy at minute 17:
   five positions, two observations, one state and five ledger rows. This
   supports temporary code rollback, not deletion/reversion of live data.
7. Extracted real BAT runs from a different working directory with spaces in
   the path. Missing Python/static prerequisites and invalid cycle count give
   visible diagnostics/nonzero exits.
8. A bounded BAT/CLI run loads the actual packaged official static index,
   uses the real loop/SQLite/logging/mutex and persists one controlled cycle.
   A test-only hook substitutes collection results and forbids HTTP; it is
   outside the ZIP and is not shipped.
9. An injected feed failure logs an error and creates no successful ledger,
   although the bounded run exits 0. Handover explicitly requires inspecting
   logs and data, not just the exit code.

The first development run of the new validator exposed quoting of the BAT
command and unclosed read-only SQLite handles in the **test harness**. Both
were corrected and the validator rerun. No production launcher defect or
runtime fix was inferred from these harness errors.

The regression suite covers same-session Windows mutex rejection/release,
continuous payload release, finite result retention, state/checkpoints, retry
recovery, SQLite rollback and backup/restore. No real outage, indefinite
collector, live feed requests or client Windows settings were used.

## Package boundary

The allowlist includes collector backend dependencies, BAT, collector
requirements, operation/setup/release/reliability/storage documentation and
official `stop_times.txt`, plus a hash/source manifest. It excludes API/frontend,
tests, Git metadata, virtual environments, all databases, logs, backup files,
credentials and unrelated generated analysis. Imported analysis helpers are
included because the existing persistence pipeline imports them.

Official feed downloaded 20 October: version **1710**, coverage
2026-10-16 to 2027-04-09, **804,594 stop-time records**. Preserve its archive and
file hashes in the manifest. Feed validity still needs checking at actual
deployment; packaging is not a static-refresh automation.

The final ZIP's source commit/size/SHA-256 are reported separately to avoid a
self-referential package hash. It is a feature-branch candidate, not an
approved main release, and has not been delivered by this task.

## Completion gates

| Item | Classification |
| --- | --- |
| Engineering compatibility, backup/restore, bounded BAT smoke | LOCAL VERIFIED |
| Same-session mutex and memory fix regression | LOCAL VERIFIED |
| Candidate content/integrity and dependency isolation | LOCAL VERIFIED |
| Current CASR running state / BAT / scheduled account setup | AWAITING CASR EVIDENCE |
| Automatic reboot restart | AWAITING CASR EVIDENCE |
| Actual CASR v2 backup, schema/health and sustained growth | AWAITING CASR EVIDENCE |
| C05 installed at CASR | AWAITING CASR EVIDENCE |
| Candidate delivered / accepted / started at CASR | AWAITING CASR EVIDENCE |
| Legacy DB migration in this update | NOT APPLICABLE |

The local work is reviewable after the exact final candidate passes validation.
Full SCRUM-236 production handover remains externally dependent. Required client
evidence and the safe update/backup/rollback sequence are in
[operations and handover](casr-v2-operations-and-handover.md); the English
message in [release notes](casr-v21-release-notes.md) is a draft only.
