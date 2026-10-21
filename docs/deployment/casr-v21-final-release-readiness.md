# CASR v2.1 final release readiness — 21 October 2026

**HOLD — NOT READY TO SEND.** No final approved release ZIP was produced.
The reviewed main runtime passes local checks, but release metadata needs a
reviewed correction and a static/realtime sequence mismatch remains unresolved.
No package was sent, no client settings changed, and no production DB accessed.

## Reviewed source

Fetched main: `b6ae9e7703c5deda62beb2c09205c0287b2c42a3`.
SCRUM-236 is merged through PR #66; SCRUM-235 and C05 are ancestors.
The entire main tree matches prior candidate source `996cafe9115b42446b19fe8a1ee6021310860cc6`.
The separate launcher hotfix `af4910e` is not an ancestor and was not included.
The collector runtime and default polling/checkpoint policy remain unchanged.

## Release metadata blocker and scoped correction

The merged packager unconditionally emits a CANDIDATE release label,
`candidate-manifest.json` and an approval-pending message. The operations and
release documents also identify the current package as an unmerged candidate.
Renaming that output would misrepresent its status.

The correction adds opt-in `--release final`, preserving candidate behavior
by default. Final mode requires both the exact fetched `origin/main` SHA and a
build script matching that source. It writes `release-manifest.json` containing
the release kind, build timestamp in UTC, source SHA, static provenance and
all packaged file hashes. The validator accepts exactly one of the candidate
or release manifests. Runtime/BAT/database code is unchanged.

Regression tests cover final metadata, a non-main commit and an unreviewed
builder. The real final-mode invocation against the old main correctly refused
the unmerged builder and left the intended final ZIP absent. This is an
expected safety check, not a failed collector test.

Review branch: `feature/SCRUM-236-final-release-metadata`.
Do not publish a final build from this unmerged correction.

## Static validation and second approval blocker

The preserved official static archive remains feed **1710**:
2026-10-16 to 2027-04-09; 804,594 records and unique
`(trip_id, stop_id, stop_sequence)` keys. Its `stop_times.txt` bytes exactly
match the prior candidate. September demo feed 1692 was not used.

| Artifact | SHA-256 |
| --- | --- |
| Official archive | `ef06c7e3a8e5d8613505db3c7b66d87328c02bb3bb599ab5d2054eb23b654c55` |
| stop_times.txt | `27a89074977f68a388becff076a7e00b316b786ef3d5a17cf08f66d6580a240f` |

One read-only Trip Updates request was captured at
2026-10-21T12:38:36Z (23:08:36 Australia/Adelaide). Feed timestamp
1792586286 was approximately 30 seconds old; payload SHA-256 was
`7fd07954eaccc047f8c5385e28167a0c2311653260367f8ee81b4bcce0ffb098`.
All 167 trip entities matched static trip IDs and all 3,151 stop updates matched
static stop IDs. Exact tuple matches were **2,908/3,151 (92.29%)**;
243 tuples did not match.

Example: trip `1180165`, stop `417`, realtime sequence 29 versus static
sequence 30. Four further sampled stops on that trip also had realtime
sequences one lower than static (415:30/31, 409:31/32, 398:32/33, 389:33/34).
This establishes a sequence mismatch, not its root cause or a global rule.
The existing converter skips missing exact tuple keys. Do not apply a guessed
sequence offset or change matching semantics in release engineering.

Approval requires investigation of the upstream schedule/sequence alignment
and agreement on a compatible static baseline or a separately reviewed
converter correction. A snapshot cannot prove future coverage or identify
the static feed installed at CASR. No silent static refresh was performed.
Static replacement rebuilds the index at process startup; existing DB history
is retained, but changed schedules can cause new state-change observations.

## Main-based validation artifact (not a final release)

The unmodified merged allowlist builder was run from a clean exported main
snapshot. The artifact is outside Git:

```text
D:\Adelaide study\2026\ICT Capstone Project\adelaide-metro-analysis-CASR-windows-v2.1-main-validation-b6ae9e7.zip
```

- 6,531,005 bytes, 31 files.
- SHA-256: `86d498a17c7e36c2b9722da4c48f1709bdfbaaa36611b113025effcf38b0e174`.
- Manifest source: `b6ae9e7703c5deda62beb2c09205c0287b2c42a3`.
- The existing candidate manifest format has no build timestamp; this build
  was performed 21 October 2026. The proposed correction records it explicitly.
- Every packaged source/static file is identical to the prior candidate; only
  its manifest source SHA and ZIP metadata differ. This artifact deliberately
  retains its candidate manifest and is not ready for delivery.

The allowlist includes necessary collector backend modules, BAT, collector
requirements, setup/operations/release/reliability/storage documentation,
official stop_times and the manifest. It excludes all databases, API/frontend,
Git/venv/cache files, logs, credentials and unrelated generated analysis.

## Local checks completed

- **66 passed, 1 deselected**: focused reliability, deployment, v2 storage,
  runner and persistence tests on clean exported main; 360-cycle test omitted.
- **8 passed**: packager safeguards including the three new final-mode tests.
- ZIP CRC, exact manifest membership, all content hashes and exclusions passed.
- Fresh Python 3.12.4 venv installed only collector requirements
  (gtfs-realtime-bindings 2.2.0, protobuf 7.36.0, tzdata 2026.5).
- Fresh extraction with spaces in the path; real BAT from another directory;
  imports, actual packaged static-index parsing, controlled bounded persistence
  and logs passed. No live requests were used by the collector smoke tests.
- Delivered old v2 code created disposable data; reviewed main preserved schema,
  history/state/ledger, committed new cycles and suppressed unchanged predictions
  after restart; 900-second checkpoint and integrity checks passed.
- Online backup retained all nine tables; the restored copy continued writing;
  original v2 code could also continue after a temporary code rollback.
- Missing interpreter/static files, invalid cycle count and injected feed
  failure diagnostics passed. A handled feed failure can still return exit 0;
  completed-cycle logs and ledger evidence remain required.
- Path probes confirmed absolute DB configuration survives working-directory
  changes; relative paths select different files; a missing path creates a DB.
  BAT defaults resolve inside its installation, so a new installation requires
  the explicit existing absolute DB path and pre-launch file-existence check.

These are local Windows checks; CASR interpreter, permissions, sessions,
scheduling, automatic power-on and reboot behavior remain unverified.

## Completion and next build

1. Review/merge the scoped metadata correction.
2. Resolve the static/realtime sequence concern and document the approved
   baseline; do not change feed versions implicitly.
3. Fetch origin, export the exact new main and use its own builder:

```powershell
python scripts/build_casr_candidate.py --repo . --commit <exact-fetched-main-sha> --static-zip <approved-official-static.zip> --output <outside-repo-final.zip> --release final
python scripts/validate_casr_candidate.py --package <outside-repo-final.zip> --old-source <verified-delivered-v2-extracted-root>
```

4. Verify source/manifest agreement, package contents, CRC, hashes, fresh-runtime
   checks, static compatibility, size, date and ZIP SHA-256; only then declare
   READY TO SEND. Keep the final name
   `adelaide-metro-analysis-CASR-windows-deployment-v2.1.zip` reserved until then.
5. Agree CASR handover: confirm current startup/Python, actual absolute DB path,
   healthy collection and consistent verified online backup; arrange maintenance.
   Stop one writer, install code with existing DB/config preserved, then check
   history, successful cycles, updated source, scheduling and subsequent cycles.
6. If rollback is needed, stop the new writer and restore application code
   while retaining the current DB. Assess data loss before any snapshot restore.

No new CASR production backup or Windows configuration evidence was supplied.
Task Scheduler starts a task after Windows starts; it cannot guarantee that
the hardware powers back on after an outage. Client deployment remains pending.
