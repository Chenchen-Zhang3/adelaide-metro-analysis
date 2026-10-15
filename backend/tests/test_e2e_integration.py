"""Missing cross-boundary tests: mock HTTP only, real decoding and SQLite."""
from contextlib import closing
from datetime import datetime
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import Mock

import pytest
from google.transit import gtfs_realtime_pb2 as pb

from backend.api.app import app
from backend.database import connection as database, repository
from backend.database.models import create_tables
from backend.realtime.client import GTFSRealtimeClient, GTFSRealtimeHTTPError
from backend.realtime.pipeline import GTFSRealtimeProcessingPipeline
from backend.services.pipeline import collect_and_persist


@pytest.fixture
def temporary_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "e2e.db")
    create_tables()
    repository.insert_route({"route_id": "G10", "route_short_name": "G10",
                             "route_long_name": "Fixture", "route_type": 3})


def feeds():
    vehicle, trip = pb.FeedMessage(), pb.FeedMessage()
    for feed in (vehicle, trip):
        feed.header.gtfs_realtime_version = "2.0"
    good = vehicle.entity.add()
    good.id = "valid"
    good.vehicle.vehicle.id = "001"
    good.vehicle.trip.trip_id = "0007"
    good.vehicle.trip.route_id = "G10"
    good.vehicle.position.latitude = -34.9
    good.vehicle.position.longitude = 138.6
    epoch = int(datetime.fromisoformat("2026-09-26T09:01:00+09:30").timestamp())
    good.vehicle.timestamp = epoch
    invalid = vehicle.entity.add()
    invalid.id = "missing-vehicle-id"
    invalid.vehicle.position.latitude = -34.9
    invalid.vehicle.position.longitude = 138.6
    entity = trip.entity.add()
    entity.id = "prediction"
    entity.trip_update.trip.trip_id = "0007"
    entity.trip_update.trip.route_id = "G10"
    entity.trip_update.trip.start_date = "20260926"
    entity.trip_update.timestamp = epoch
    stop = entity.trip_update.stop_time_update.add()
    stop.stop_id = "0009"
    stop.stop_sequence = 1
    stop.arrival.time = epoch
    return vehicle.SerializeToString(), trip.SerializeToString()


def test_http_decode_validation_delay_v2_query_and_api(temporary_db, monkeypatch):
    payloads = feeds()
    http = Mock(side_effect=[BytesIO(payload) for payload in payloads * 2])
    monkeypatch.setattr("backend.realtime.client.urlopen", http)
    pipeline = GTFSRealtimeProcessingPipeline(
        client=GTFSRealtimeClient(),
        stop_time_index={("0007", "0009", 1): {"arrival_time": "09:00:00"}},
        sleep_function=lambda _: pytest.fail("Unexpected wait"))
    first = collect_and_persist(pipeline.collector)
    second = collect_and_persist(pipeline.collector)
    assert len(first["collection_result"]["vehicle_positions"]) == 1
    assert first["persistence_result"]["trip_updates_inserted"] == 1
    assert second["persistence_result"]["trip_updates_suppressed"] == 1
    assert second["persistence_result"]["vehicle_positions_inserted"] == 0
    updates = repository.get_trip_updates_filtered(route_id="G10")
    assert len(updates) == 1
    update = updates[0]
    assert update["delay_seconds"] == 60
    assert update["scheduled_arrival"] == "2026-09-26T09:00:00+09:30"
    assert update["actual_arrival"] == "2026-09-26T09:01:00+09:30"
    assert update["timestamp"] == "2026-09-26T09:01:00+09:30"
    with closing(database.get_connection()) as connection:
        assert connection.execute("SELECT count(*) FROM collection_cycles").fetchone()[0] == 2
    assert http.call_count == 4
    assert [call.args[0].full_url.rsplit("/", 1)[-1] for call in http.call_args_list] == [
        "vehicle_positions", "trip_updates"] * 2
    response = app.test_client().get("/api/routes/G10/vehicle-positions", query_string={
        "start_time": "2026-09-25T23:30:00Z", "end_time": "2026-09-26T00:30:00Z"})
    assert response.status_code == 200
    assert response.json["positions"][0]["vehicle_id"] == "001"


@pytest.mark.parametrize("failure", [b"not protobuf", HTTPError("http://fixture", 403, "forbidden", {}, None)])
def test_bad_http_or_decode_never_partially_persists(temporary_db, monkeypatch, failure):
    def fetch(*args, **kwargs):
        if isinstance(failure, Exception):
            raise failure
        return BytesIO(failure)
    monkeypatch.setattr("backend.realtime.client.urlopen", fetch)
    pipeline = GTFSRealtimeProcessingPipeline(sleep_function=lambda _: pytest.fail("No retry expected"))
    with pytest.raises((ValueError, GTFSRealtimeHTTPError)):
        collect_and_persist(pipeline.collector)
    with closing(database.get_connection()) as connection:
        for table in ("vehicle_positions", "trip_updates", "collection_cycles"):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


@pytest.mark.parametrize("changes", [{}, {"start_time": "bad"}, {"limit": "0"},
    {"limit": "1001"}, {"offset": "-1"}, {"offset": str(2**63)}, {"limit": "1.5"},
    {"start_time": "2026-09-26T09:00:00"}, {"end_time": "2026-09-26T08:00:00+09:30"},
    {"extra": "unsupported"}])
def test_history_rejects_invalid_filters(temporary_db, changes):
    args = {"start_time": "2026-09-26T09:00:00+09:30", "end_time": "2026-09-26T11:00:00+09:30"}
    if not changes:
        args = {}
    args.update(changes)
    assert app.test_client().get("/api/routes/G10/vehicle-positions", query_string=args).status_code == 400


def test_history_half_open_pagination_empty_and_unknown_route(temporary_db):
    for minute in range(3):
        repository.insert_vehicle_position({"vehicle_id": "001", "trip_id": "0007", "route_id": "G10",
            "latitude": -34.9, "longitude": 138.6, "timestamp": f"2026-09-26T09:0{minute}:00+09:30"})
    args = {"start_time": "2026-09-25T23:30:00Z", "end_time": "2026-09-25T23:32:00Z", "limit": 1}
    client = app.test_client()
    first = client.get("/api/routes/G10/vehicle-positions", query_string=args).json
    assert len(first["positions"]) == 1 and first["next_offset"] == 1
    args["offset"] = first["next_offset"]
    second = client.get("/api/routes/G10/vehicle-positions", query_string=args).json
    assert second["next_offset"] is None
    assert first["positions"][0]["id"] != second["positions"][0]["id"]
    args["offset"] = 2
    assert client.get("/api/routes/G10/vehicle-positions", query_string=args).json["positions"] == []
    assert client.get("/api/routes/UNKNOWN/vehicle-positions", query_string=args).status_code == 404
