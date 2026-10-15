"""Offline recorded-demo fallback: verify a disposable copy, never collect feeds.

Run with python -m backend.services.e2e_demo_check --database DB --map-data DIR.
"""
import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from jsonschema import Draft202012Validator

from backend.api.app import app
from backend.database import repository
from backend.database.connection import get_connection
from backend.services.recorded_demo import demo_database, smoke_demo, LABEL
from backend.services.recorded_map_data import MAP_DATA_ENV


def verify(database, map_data):
    """Reuse the established recorded queries; add map/history boundary checks."""
    database, map_data = Path(database).resolve(), Path(map_data).resolve()
    if not database.is_file() or not map_data.is_dir():
        raise ValueError("Existing demo database and map-data directory required")
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    config = {"route_ids": ["G10", "M44", "506"],
              "start": "2026-09-26T09:00:00+09:30",
              "end_exclusive": "2026-09-26T11:00:00+09:30"}
    schema = json.loads((Path(__file__).resolve().parents[2] /
                         "shared/schemas/recorded-route-map.schema.json").read_text(encoding="utf8"))
    previous = os.environ.get(MAP_DATA_ENV)
    try:
        os.environ[MAP_DATA_ENV] = str(map_data)
        with tempfile.TemporaryDirectory(prefix="adelaide-e2e-") as directory:
            copy = Path(directory) / "demo.db"
            shutil.copy2(database, copy)
            with demo_database(copy):
                with closing(get_connection()) as connection:
                    chosen = {row[0] for row in connection.execute("SELECT trip_id FROM trips")}
                report = smoke_demo(config, chosen)
                client = app.test_client()
                for route, details in report.items():
                    response = client.get(f"/api/routes/{route}/map-data")
                    assert response.status_code == 200
                    data = response.json
                    Draft202012Validator(schema).validate(data)
                    assert data["label"] == LABEL and data["route_id"] == route
                    details["shape_variants"] = len(data["geometry"]["features"])
                    details["geometry_points"] = sum(len(f["geometry"]["coordinates"]) for f in data["geometry"]["features"])
                    args = {"start_time": config["start"], "end_time": config["end_exclusive"], "limit": 200, "offset": 0}
                    positions = []
                    while True:
                        response = client.get(f"/api/routes/{route}/vehicle-positions", query_string=args)
                        assert response.status_code == 200
                        positions.extend(response.json["positions"])
                        following = response.json["next_offset"]
                        if following is None:
                            break
                        args["offset"] = following
                    expected = repository.get_vehicle_positions_filtered(route_id=route, start_time=config["start"], end_time=config["end_exclusive"])
                    assert {row["id"] for row in positions} == {row["id"] for row in expected}
                    assert len(positions) == len(expected)
                    for row in positions:
                        assert -90 <= row["latitude"] <= 90 and -180 <= row["longitude"] <= 180
                        assert datetime.fromisoformat(config["start"]) <= datetime.fromisoformat(row["timestamp"]) < datetime.fromisoformat(config["end_exclusive"])
                    details["vehicle_api_rows"] = len(positions)
                assert client.get("/api/routes/UNKNOWN/map-data").status_code == 404
                os.environ[MAP_DATA_ENV] = str(Path(directory) / "missing-map-data")
                assert client.get("/api/routes/G10/map-data").status_code == 503
    finally:
        if previous is None:
            os.environ.pop(MAP_DATA_ENV, None)
        else:
            os.environ[MAP_DATA_ENV] = previous
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    return {"label": LABEL, "database_sha256_unchanged": before,
            "window": config, "routes": report,
            "negative_map_statuses": {"unknown_route": 404, "missing_files": 503}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--map-data", type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(verify(options.database, options.map_data), indent=2))


if __name__ == "__main__":
    main()
