# Windows Historical Collector Deployment

This guide prepares one CASR Windows computer to collect Adelaide Metro
GTFS-Realtime history continuously. The collector stores Vehicle Positions and
Trip Updates in a local SQLite database for later analysis.

## 1. Prerequisites

- A Windows computer that can remain powered on and connected to the internet.
- Python 3.12, including the `py` launcher and `venv` support.
- A local copy of this repository on a drive with enough free space.
- Write permission to the repository's `data` and `logs` directories.
- Outbound HTTPS access to the Adelaide Metro GTFS-Realtime endpoints.

Administrator access is not required when the repository is stored in a folder
owned by the Task Scheduler account. Task Scheduler may request that account's
password when “Run whether user is logged on or not” is selected.

## 2. Recommended directory layout

```text
adelaide-metro-analysis\
  .venv\
  data\
    static_gtfs\
      stop_times.txt
    historical\
      adelaide_metro_history_v2.db
    backups\
  logs\
    historical_collector.log
  scripts\
    start_historical_collector.bat
```

The database, SQLite sidecar files, downloaded static data and runtime logs are
excluded from Git.

## 3. Install the collector runtime

Open PowerShell in the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-collector.txt
```

The collector runtime file installs only:

- `gtfs-realtime-bindings`
- `protobuf`
- `tzdata` for reliable `Australia/Adelaide` timezone support on Windows

SQLite, HTTP access and log rotation use Python's standard library. Flask and
pytest are not required to run the collector.

## 4. Prepare static GTFS

Download and extract the current Adelaide Metro static GTFS feed. Copy its
`stop_times.txt` file to:

```text
data\static_gtfs\stop_times.txt
```

Only `stop_times.txt` is required by this collector. It is loaded once when the
process starts and reused for every realtime cycle.

Static refresh policy:

1. Stop the collector.
2. Replace `data\static_gtfs\stop_times.txt` with the newer file.
3. Start the collector again.
4. Confirm the log reports that the static stop-time index loaded successfully.

There is no automatic static GTFS downloader in this deployment task.

## 5. Launcher configuration

The default launcher is:

```text
scripts\start_historical_collector.bat
```

It resolves all default paths relative to the repository, checks the Python
environment and `stop_times.txt`, creates the historical-data and log
directories, then starts the existing Python collector.

Default environment values:

| Variable | Default |
| --- | --- |
| `ADELAIDE_METRO_PYTHON` | Optional full path; otherwise `.venv`, then `py -3.12`, then PATH `python.exe` |
| `ADELAIDE_METRO_STATIC_GTFS_PATH` | `data\static_gtfs` |
| `ADELAIDE_METRO_DATABASE_PATH` | `data\historical\adelaide_metro_history_v2.db` |
| `ADELAIDE_METRO_LOG_PATH` | `logs\historical_collector.log` |
| `ADELAIDE_METRO_POLLING_INTERVAL_SECONDS` | `60` |
| `ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS` | `900` |
| `ADELAIDE_METRO_PAUSE_ON_ERROR` | Unset; set `1` only for interactive troubleshooting |

Set a variable before launching only when the CASR computer needs a different
location. Do not place credentials in the batch file.

Python selection order is an explicit `ADELAIDE_METRO_PYTHON` executable, the
project's `.venv\Scripts\python.exe`, `py -3.12`, then the first `python.exe` on
PATH. Every selected interpreter must report Python 3.12. An invalid explicit
path or project environment fails visibly; it is not silently replaced. The
launcher checks GTFS bindings, protobuf, tzdata and Adelaide timezone support
before starting, and prints an install command for `requirements-collector.txt`
when the runtime check fails. It never installs packages automatically.

If VS Code works but the batch file does not, run `python -c "import sys;
print(sys.executable)"` in the working VS Code Python environment and configure
that full executable path in PowerShell:

```powershell
$env:ADELAIDE_METRO_PYTHON = 'C:\path\to\environment\Scripts\python.exe'
.\scripts\start_historical_collector.bat --max-cycles 1
```

Run the batch file from an existing Command Prompt to keep its error visible.
For interactive troubleshooting only, set `ADELAIDE_METRO_PAUSE_ON_ERROR=1`;
leave it unset for Task Scheduler. The scheduled account must have the same
interpreter path and environment configuration. Use the selected interpreter
for the health-check and backup commands below if the project `.venv` is absent.

## 6. First smoke run

From Command Prompt or PowerShell, run one bounded cycle:

```powershell
.\scripts\start_historical_collector.bat --max-cycles 1
```

If successful, start continuous collection by omitting the cycle limit:

```powershell
.\scripts\start_historical_collector.bat
```

The batch file returns a non-zero exit code if its prerequisites are missing,
another collector is running, or the Python process fails during startup.

## 7. Logging and health checks

Logs appear in the terminal and in:

```text
logs\historical_collector.log
```

The log rotates at 5 MB and retains five older files. It records startup,
static-index loading, collection summaries, feed failures, persistence
failures, waits and shutdown.

To confirm data is accumulating:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; db=sqlite3.connect(r'data\historical\adelaide_metro_history_v2.db'); print('vehicles:', db.execute('SELECT COUNT(*) FROM vehicle_positions').fetchone()[0]); print('trip updates:', db.execute('SELECT COUNT(*) FROM trip_updates').fetchone()[0]); db.close()"
```

Vehicle counts normally increase after successful cycles. Trip Update history
stores state changes immediately and unchanged-state checkpoints every 15
minutes, so its count is not expected to increase on every poll. The
`collection_cycles` table records every successful cycle even when all Trip
Updates were unchanged.

## 8. Stop and restart

For an interactive run, press `Ctrl+C`. The collector logs the shutdown and
returns exit code 0. Starting the same batch file again reuses the persisted
`trip_update_current_state` table, so unchanged predictions are not duplicated
after restart.

The optimised collector must start with a new database. It deliberately refuses
to modify a legacy database containing the old TEXT/`actual_arrival` schema.
Keep the old database as a read-only archive and configure a new path before the
first optimised run.

For a scheduled run, first disable its startup trigger. If maintenance is
required, wait until the log shows the collector is waiting between cycles,
then end the task. Re-enable and run the task after maintenance.

The Python entry point uses a Windows named mutex. A second collector launched
in the same Windows session exits with code 2 instead of writing concurrently.
Use one dedicated Task Scheduler account and also configure Task Scheduler not
to start a second instance.

## 9. Configure Windows Task Scheduler

The client or project team must perform these steps on the CASR computer:

1. Open **Task Scheduler** and select **Create Task**.
2. Name it `Adelaide Metro Historical Collector`.
3. Select the dedicated Windows account that owns the repository files.
4. Optionally select **Run whether user is logged on or not**. Do not select
   **Run with highest privileges** unless the chosen folders require it.
5. Add trigger **At startup** with a one-minute delay.
6. Add an action:
   - Program: `C:\Windows\System32\cmd.exe`
   - Arguments: `/c ""C:\path\to\adelaide-metro-analysis\scripts\start_historical_collector.bat""`
   - Start in: `C:\path\to\adelaide-metro-analysis`
7. In **Settings**, enable restart after failure, for example every five
   minutes for three attempts.
8. Set **If the task is already running** to **Do not start a new instance**.
9. Do not set a short maximum execution time; the collector is intended to run
   continuously.
10. Save the task, run it manually once, then confirm the log and database
    counts before relying on the startup trigger.

These instructions do not modify Task Scheduler automatically and do not
assume administrator permissions.

## 10. Create a safe database backup

Do not copy the actively written `.db` file directly. Use SQLite's online
backup mechanism while the collector continues running:

```powershell
.\.venv\Scripts\python.exe -m backend.services.historical_backup --database ".\data\historical\adelaide_metro_history_v2.db" --output-dir ".\data\backups"
```

The command creates a timestamped snapshot and runs `PRAGMA integrity_check`.
Copy the completed snapshot—not the live database—to the analysis team. Keep
the live database on the CASR collector computer unless the client agrees to a
different access method.

## 11. Troubleshooting

| Symptom | Check |
| --- | --- |
| Python not found or wrong version | Check the printed interpreter; install Python 3.12 or set `ADELAIDE_METRO_PYTHON` to its full executable path. |
| Runtime dependency check failed | Run the printed `requirements-collector.txt` install command with the selected interpreter. |
| `stop_times.txt` not found | Confirm it is directly inside `data\static_gtfs`, or set `ADELAIDE_METRO_STATIC_GTFS_PATH`. |
| Exit code 2 | Launcher Python selection failure, or collector single-instance rejection; the printed error identifies the stage. |
| No new rows | Check the log for feed errors; repeated feed snapshots may also be ignored as duplicates. |
| Legacy historical database detected | Preserve the old file, set `ADELAIDE_METRO_DATABASE_PATH` to a new filename, then restart. |
| Database locked | Confirm only one Task Scheduler account/session is running the collector. |
| No log file | Confirm the Task Scheduler account can write to the `logs` directory. |
| Collector does not restart after power loss | Confirm the startup trigger, account credentials, failure restart settings and “Do not start a new instance” option. |

If the computer is powered off, asleep or disconnected from the network, no
realtime data is collected. Missed GTFS-Realtime history cannot be downloaded
or reconstructed later. Restarting the task resumes collection only from that
point forward.
