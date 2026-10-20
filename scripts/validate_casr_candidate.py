"""Offline, disposable old-v2 -> candidate compatibility and Windows smoke check.

Run with a Python containing requirements-collector.txt. Supply the verified
original v2 package's extracted root, never a production database.
"""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import zipfile


TABLES = ("vehicle_positions", "trip_updates", "trip_update_current_state",
          "collection_cycles", "schema_metadata", "routes", "stops", "trips", "stop_times")
CYCLE_CODE = """
from datetime import datetime, timedelta
from backend.database.models import create_tables
from backend.database.repository import persist_realtime_collection
from backend.realtime.config import DEFAULT_COLLECTION_SETTINGS
from backend.database.historical_storage import configured_trip_update_checkpoint_seconds
assert DEFAULT_COLLECTION_SETTINGS.polling_interval_seconds == 60
assert configured_trip_update_checkpoint_seconds() == 900
create_tables()
start = datetime.fromisoformat('2026-10-20T09:00:00+10:30')
minute = MINUTE
observed = (start + timedelta(minutes=minute)).isoformat()
persist_realtime_collection(
    [{'vehicle_id':'SYNTHETIC-V', 'latitude':-34.9, 'longitude':138.6,
      'timestamp':observed}],
    [{'trip_id':'SYNTHETIC-T', 'route_id':'SYNTHETIC-R', 'stop_id':'SYNTHETIC-S',
      'scheduled_arrival':start.isoformat(), 'delay_seconds':60,
      'actual_arrival':(start + timedelta(seconds=60)).isoformat(),
      'timestamp':observed}])
"""


def environment(database):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("ADELAIDE_METRO_") and k not in ("PYTHONPATH", "PYTHONHOME")}
    env["ADELAIDE_METRO_DATABASE_PATH"] = str(database)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def python(code, root, env):
    result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
                            capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result


def snapshot(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return {t: db.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall() for t in TABLES}


def schema(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        return db.execute("SELECT type,name,sql FROM sqlite_master ORDER BY type,name").fetchall()


def validate(package, old_source):
    package, old_source = Path(package).resolve(), Path(old_source).resolve()
    checks = []
    with tempfile.TemporaryDirectory(prefix="CASR candidate with spaces ") as temporary:
        root = Path(temporary)
        candidate = root / "candidate"
        with zipfile.ZipFile(package) as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            assert len(names) == len(set(names))
            assert all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in names)
            manifest = json.loads(archive.read("candidate-manifest.json"))
            assert set(names) == set(manifest["files"]) | {"candidate-manifest.json"}
            for name, digest in manifest["files"].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
                assert not name.endswith((".db", ".sqlite", ".log", ".pyc"))
                assert not any(p in name.split("/") for p in (".git", ".venv", "__pycache__"))
            archive.extractall(candidate)
        checks.append("ZIP CRC, manifest hashes and artifact exclusions")
        database = root / "upgrade.db"
        env = environment(database)
        python(CYCLE_CODE.replace("MINUTE", "0"), old_source, env)
        before, old_schema = snapshot(database), schema(database)
        assert [len(before[t]) for t in TABLES[:4]] == [1, 1, 1, 1]
        python("from backend.database.models import create_tables; create_tables()", candidate, env)
        assert snapshot(database) == before
        assert schema(database) == old_schema
        python(CYCLE_CODE.replace("MINUTE", "1"), candidate, env)
        after = snapshot(database)
        assert [len(after[t]) for t in TABLES[:4]] == [2, 1, 1, 2]
        assert after["trip_updates"] == before["trip_updates"]
        assert after["vehicle_positions"][:1] == before["vehicle_positions"]
        assert after["collection_cycles"][:1] == before["collection_cycles"]
        # A separate interpreter proves state recovery, not an in-memory cache.
        python(CYCLE_CODE.replace("MINUTE", "15"), candidate, env)
        checkpoint = snapshot(database)
        assert [len(checkpoint[t]) for t in TABLES[:4]] == [3, 2, 1, 3]
        assert checkpoint["trip_updates"][-1][-1] == 2
        assert schema(database) == old_schema
        checks.append("Delivered-v2-created DB: exact schema/history preserved; restart suppression; 900s checkpoint")
        backup = root / "backup.db"
        python(
            "from backend.services.historical_backup import create_sqlite_backup; "
            f"create_sqlite_backup({str(database)!r}, {str(backup)!r})", candidate, env)
        assert snapshot(backup) == checkpoint
        restored = root / "restored.db"
        restored.write_bytes(backup.read_bytes())  # Closed, verified snapshot, never a live DB.
        python(CYCLE_CODE.replace("MINUTE", "16"), candidate, environment(restored))
        resumed = snapshot(restored)
        assert [len(resumed[t]) for t in TABLES[:4]] == [4, 2, 1, 4]
        assert snapshot(database) == checkpoint
        assert snapshot(backup) == checkpoint
        checks.append("Online backup: all nine tables identical; restored snapshot accepts next cycle")
        python(CYCLE_CODE.replace("MINUTE", "17"), old_source, environment(restored))
        rollback = snapshot(restored)
        assert [len(rollback[t]) for t in TABLES[:4]] == [5, 2, 1, 5]
        assert rollback["trip_updates"] == resumed["trip_updates"]
        assert rollback["collection_cycles"][:4] == resumed["collection_cycles"]
        checks.append("Code rollback: original v2 continues on candidate-written disposable DB without reset")
        if os.name != "nt":
            raise RuntimeError("Windows BAT validation must run on Windows")
        launcher = candidate / "scripts/start_historical_collector.bat"

        def bat(arguments, settings, expected):
            # A fixed, quoted known path; no shell-composed filesystem operations.
            result = subprocess.run(
                f'cmd.exe /d /s /c ""{launcher}" {arguments}"',
                cwd=root, env=settings, capture_output=True, text=True, timeout=90)
            assert result.returncode == expected, result.stdout + result.stderr
            return result.stdout + result.stderr

        missing = environment(root / "unused.db")
        missing["ADELAIDE_METRO_PYTHON"] = str(root / "missing.exe")
        assert "Python was not found" in bat("--max-cycles 1", missing, 2)
        missing["ADELAIDE_METRO_PYTHON"] = sys.executable
        missing["ADELAIDE_METRO_STATIC_GTFS_PATH"] = str(root / "missing-static")
        assert "stop_times.txt was not found" in bat("--max-cycles 1", missing, 3)
        smoke = environment(root / "smoke.db")
        smoke["ADELAIDE_METRO_PYTHON"] = sys.executable
        assert "max cycles must be greater than zero" in bat("--max-cycles 0", smoke, 2)
        checks.append("BAT from unrelated working directory: missing Python/static and invalid cycles diagnostics")
        # Test-only startup hook outside package; all networking forbidden.
        # Real CLI, static parsing, mutex, loop, persistence and logs remain active.
        hook = root / "offline-hook"
        hook.mkdir()
        (hook / "sitecustomize.py").write_text("""
import urllib.request
def forbidden(*args, **kwargs):
    raise AssertionError('Live HTTP forbidden during offline package validation')
urllib.request.urlopen = forbidden
from backend.realtime.collector import GTFSRealtimeCollector
def collect(self):
    return {
        'vehicle_positions':[{'vehicle_id':'PACKAGE-SYNTHETIC', 'latitude':-34.9,
          'longitude':138.6, 'timestamp':'2026-10-20T09:00:00+10:30'}],
        'trip_updates':[{'trip_id':'PACKAGE-T', 'route_id':'PACKAGE-R',
          'stop_id':'PACKAGE-S', 'scheduled_arrival':'2026-10-20T09:00:00+10:30',
          'delay_seconds':60, 'actual_arrival':'2026-10-20T09:01:00+10:30',
          'timestamp':'2026-10-20T09:00:00+10:30'}]}
GTFSRealtimeCollector.collect_once = collect
""", encoding="utf-8")
        smoke["PYTHONPATH"] = os.pathsep.join((str(hook), str(candidate)))
        smoke["ADELAIDE_METRO_LOG_PATH"] = str(root / "smoke.log")
        output = bat("--max-cycles 1", smoke, 0)
        assert "Completed historical GTFS collection cycle 1" in output
        assert "Loaded " in output and "static stop-time records" in output
        assert [len(snapshot(root / "smoke.db")[t]) for t in TABLES[:4]] == [1, 1, 1, 1]
        assert "stopped normally" in (root / "smoke.log").read_text()
        checks.append("Bounded real BAT/CLI/static/mutex/log/persistence smoke with controlled collection input; no HTTP")
        # Confirm failed feeds can return exit 0 after a bounded run; logs are mandatory.
        (hook / "sitecustomize.py").write_text("""
import urllib.request
def forbidden(*args, **kwargs): raise AssertionError('HTTP forbidden')
urllib.request.urlopen = forbidden
from backend.realtime.collector import GTFSRealtimeCollector
from backend.realtime.client import GTFSRealtimeConnectionError
def collect(self): raise GTFSRealtimeConnectionError('Synthetic network failure')
GTFSRealtimeCollector.collect_once = collect
""", encoding="utf-8")
        failed = root / "failed.db"
        smoke["ADELAIDE_METRO_DATABASE_PATH"] = str(failed)
        output = bat("--max-cycles 1", smoke, 0)
        assert "failed while retrieving a feed" in output
        assert len(snapshot(failed)["collection_cycles"]) == 0
        checks.append("Failed collection: visible error, zero ledger rows despite bounded exit 0")
    print(json.dumps({"package": str(package), "source": manifest["source_commit"],
                      "checks_passed": checks, "production_verified": False}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--old-source", type=Path, required=True)
    args = parser.parse_args()
    validate(args.package, args.old_source)
