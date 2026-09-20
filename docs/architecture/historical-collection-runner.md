# Continuous Historical GTFS Collection Runner

## Scope

SCRUM-187 turns the existing one-cycle GTFS-Realtime processing and persistence
flow into a controlled historical collector. It reuses the Sprint 2 scheduled
collector and the SCRUM-186 collection-cycle SQLite transaction; it does not
introduce another HTTP client, decoder, scheduler or persistence model.

## Runtime architecture

```text
application startup
  -> parse static stop_times.txt once
  -> build one stop_time_index
  -> create SQLite schema with IF NOT EXISTS
  -> GTFSRealtimeProcessingPipeline(stop_time_index=index)
  -> existing run_collection_and_persist() loop
       -> process one Vehicle Positions + Trip Updates cycle
       -> SCRUM-186 single SQLite transaction
       -> log summary
       -> wait configured polling interval
       -> repeat
```

`backend.services.historical_collection.HistoricalCollectionRunner` owns only
startup lifecycle. Once initialised, it passes the pipeline's existing
collector to `backend.services.pipeline.run_collection_and_persist()`.

## Static GTFS lifecycle

The selected policy is **refresh on application restart**:

1. Download and extract a current static GTFS feed before starting the
   collector.
2. Point `--static-gtfs-dir` at the directory containing `stop_times.txt`.
3. The runner parses that file and builds `stop_time_index` exactly once.
4. Every realtime cycle reuses the same index.
5. To adopt a newer static feed, replace the extracted static directory and
   restart the collector.

This deliberately avoids re-parsing the large `stop_times.txt` file every
polling interval. If static loading fails, the process does not start and the
existing historical SQLite database is left unchanged.

## Database lifecycle

Set `ADELAIDE_METRO_DATABASE_PATH` before Python starts to choose the history
database. Its parent directory is created when needed. `create_tables()` uses
`IF NOT EXISTS`, so restart initialisation preserves existing records and
indexes. The repository's `INSERT OR IGNORE` constraints continue to ignore
duplicate rows.

SQLite history files are ignored by the repository's `.gitignore`. A suitable
local location is `data/historical/adelaide-metro-history.db` under a private
working copy, not a committed project asset.

## Start the collector

From the repository root, install `requirements.txt`, then prepare a new local
static directory. The current static feed URL below was used by the controlled
pilot; use a new empty directory when refreshing the static feed:

```powershell
$staticDirectory = Join-Path $PWD "data\static-gtfs"
$staticArchive = Join-Path $env:TEMP "adelaide-metro-static-gtfs.zip"
New-Item -ItemType Directory -Path $staticDirectory -ErrorAction Stop | Out-Null
Invoke-WebRequest -Uri "https://gtfs.adelaidemetro.com.au/v1/static/latest/google_transit.zip" -OutFile $staticArchive
Expand-Archive -Path $staticArchive -DestinationPath $staticDirectory
```

Then configure the history database and start collection:

```powershell
$env:ADELAIDE_METRO_DATABASE_PATH = "$PWD\data\historical\adelaide-metro-history.db"
$env:ADELAIDE_METRO_POLLING_INTERVAL_SECONDS = "60"
python -m backend.services.historical_collection --static-gtfs-dir $staticDirectory
```

The default polling interval is 60 seconds. Set
`ADELAIDE_METRO_POLLING_INTERVAL_SECONDS` before startup to a positive integer
when a different cadence is needed. The existing collection settings still
provide the feed URLs, 10-second request timeout, two retry attempts and
five-second retry delay.

For a short controlled pilot, add `--max-cycles 3`. The runner logs startup,
each cycle's received/inserted record counts, failures and the next wait.

The official [Adelaide Metro developer information](https://www.adelaidemetro.com.au/developer-info)
page describes the static GTFS and GTFS-Realtime feeds. Use its current static
GTFS source rather than committing a downloaded feed to this repository.

## Failure, shutdown and restart behaviour

| Situation | Behaviour |
| --- | --- |
| Temporary feed failure | Existing bounded retry policy runs. A retry-exhausted cycle is logged, skipped and the runner waits before the next cycle. |
| Non-retryable feed or processing failure | The failed cycle is logged; later cycles continue after the normal polling wait. |
| SQLite persistence failure | SCRUM-186 rolls back the whole cycle transaction and logs its stage. The runner logs the failed cycle, waits, then tries the next cycle. |
| `Ctrl+C` | `KeyboardInterrupt` stops the loop cleanly and logs shutdown. Repository connections are per-cycle and closed by the persistence layer. |
| Restart | Static data is reloaded once, schema is initialised idempotently, and new rows accumulate in the same configured database. |

To stop a normal Windows run, press `Ctrl+C` in the terminal. Do not force-kill
the process unless normal interruption is unavailable.

## Verify accumulation

With the database environment variable still set, run:

```powershell
python -c "import os, sqlite3; db = sqlite3.connect(os.environ['ADELAIDE_METRO_DATABASE_PATH']); print(db.execute('SELECT COUNT(*) FROM vehicle_positions').fetchone()[0]); print(db.execute('SELECT COUNT(*) FROM trip_updates').fetchone()[0]); db.close()"
```

The counts should increase after successful cycles. If the same feed snapshot
is collected again, `INSERT OR IGNORE` may keep counts unchanged; that is
expected duplicate protection rather than a failed collector.

## Hosting limitation

This runner is ready for a persistent host but does not provide one. When it
runs on a developer Windows PC, PC shutdown, sleep, network loss or restart
stops collection and leaves a gap in historical data. Restarting later resumes
from the existing SQLite file but cannot backfill missed realtime history. A
future always-on deployment and monitoring solution is recommended; cloud
infrastructure is out of SCRUM-187 scope.

## Remaining work

SCRUM-187 provides reliable collection and accumulation only. Later work can
use the growing history for the next agreed analysis, querying and deployment
requirements; it does not add a replay UI, new delay algorithms or cloud
orchestration.
