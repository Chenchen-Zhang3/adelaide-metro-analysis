"""Build an allowlisted collector candidate from an explicit Git commit.

No working-tree files or historical databases are read into the package.
The official static archive is supplied separately; provenance is recorded.
"""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile


FILES = (
    "backend/analysis/__init__.py",
    "backend/analysis/aggregation.py",
    "backend/analysis/metrics.py",
    "backend/analysis/punctuality.py",
    "backend/database/__init__.py",
    "backend/database/connection.py",
    "backend/database/historical_storage.py",
    "backend/database/models.py",
    "backend/database/repository.py",
    "backend/parsers/static_gtfs.py",
    "backend/realtime/client.py",
    "backend/realtime/collector.py",
    "backend/realtime/config.py",
    "backend/realtime/decoder.py",
    "backend/realtime/pipeline.py",
    "backend/realtime/validation.py",
    "backend/services/gtfs_converter.py",
    "backend/services/historical_backup.py",
    "backend/services/historical_collection.py",
    "backend/services/historical_records.py",
    "backend/services/pipeline.py",
    "backend/services/windows_single_instance.py",
    "scripts/start_historical_collector.bat",
    "requirements-collector.txt",
    "docs/deployment/windows-historical-collector.md",
    "docs/deployment/casr-v2-operations-and-handover.md",
    "docs/deployment/casr-v21-release-notes.md",
    "docs/architecture/historical-collection-reliability.md",
    "docs/architecture/historical-storage-optimisation.md",
)
STATIC_URL = "https://gtfs.adelaidemetro.com.au/v1/static/latest/google_transit.zip"


def build(repo, commit, static_zip, output):
    repo, static_zip, output = map(Path, (repo, static_zip, output))
    if output.exists():
        raise FileExistsError(output)
    if output.resolve().is_relative_to(repo.resolve()):
        raise ValueError("Candidate ZIP must be outside the repository")
    sha = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"], cwd=repo,
        text=True,
    ).strip()
    contents = {
        name: subprocess.check_output(["git", "show", f"{sha}:{name}"], cwd=repo)
        for name in FILES
    }
    with zipfile.ZipFile(static_zip) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Corrupt official static ZIP member: {bad}")
        stop_times = archive.read("stop_times.txt")
        reader = csv.DictReader(io.StringIO(stop_times.decode("utf-8-sig")))
        required = {"trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Static stop_times.txt is missing required columns")
        rows = sum(1 for _ in reader)
        if not rows:
            raise ValueError("Static stop_times.txt has no records")
        feed_info = archive.read("feed_info.txt").decode("utf-8-sig") if "feed_info.txt" in archive.namelist() else None
    contents["data/static_gtfs/stop_times.txt"] = stop_times
    manifest = {
        "release": "CASR Windows Deployment v2.1 CANDIDATE",
        "source_commit": sha,
        "approval": "Not an approved main release; review and client deployment pending",
        "static_source_url": STATIC_URL,
        "static_archive_sha256": hashlib.sha256(static_zip.read_bytes()).hexdigest(),
        "static_feed_info": feed_info,
        "stop_time_rows": rows,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    contents["candidate-manifest.json"] = json.dumps(manifest, indent=2).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(contents)
    print(json.dumps({
        "path": str(output.resolve()), "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "source_commit": sha, "entries": len(contents), "stop_time_rows": rows,
        "static_feed_info": feed_info,
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--static-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.repo, args.commit, args.static_zip, args.output)
