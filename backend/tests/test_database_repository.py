from pathlib import Path

import pytest

import backend.database.connection as database_connection
from backend.database.models import create_tables
from backend.database.repository import (
    insert_stop,
    get_stop,
    insert_trip_update,
    get_trip_updates,
)


@pytest.fixture(autouse=True)
def temporary_database(tmp_path, monkeypatch):
    """
    Use a temporary SQLite database for every test.
    This prevents automated tests from changing the normal
    development database.
    """
    test_database_path = Path(tmp_path) / "test_adelaide_metro.db"

    monkeypatch.setattr(
        database_connection,
        "DATABASE_PATH",
        test_database_path,
    )

    create_tables()

    yield


def test_stop_persistence_and_retrieval():
    sample_stop = {
        "stop_id": "STOP_001",
        "stop_name": "Sample Adelaide Stop",
        "stop_lat": -34.9285,
        "stop_lon": 138.6007,
    }

    insert_stop(sample_stop)

    result = get_stop("STOP_001")

    assert result is not None
    assert result["stop_id"] == "STOP_001"
    assert result["stop_name"] == "Sample Adelaide Stop"
    assert result["stop_lat"] == -34.9285
    assert result["stop_lon"] == 138.6007


def test_trip_update_persistence_and_retrieval():
    sample_trip_update = {
        "trip_id": "TRIP_001",
        "route_id": "ROUTE_001",
        "stop_id": "STOP_001",
        "scheduled_arrival": "2026-08-30T10:00:00",
        "actual_arrival": "2026-08-30T10:05:00",
        "delay_seconds": 300,
        "timestamp": "2026-08-30T10:05:00",
    }

    insert_trip_update(sample_trip_update)

    results = get_trip_updates("ROUTE_001")

    assert len(results) == 1
    assert results[0]["trip_id"] == "TRIP_001"
    assert results[0]["route_id"] == "ROUTE_001"
    assert results[0]["stop_id"] == "STOP_001"
    assert results[0]["delay_seconds"] == 300


def test_duplicate_trip_update_is_not_stored_twice():
    sample_trip_update = {
        "trip_id": "TRIP_001",
        "route_id": "ROUTE_001",
        "stop_id": "STOP_001",
        "scheduled_arrival": "2026-08-30T10:00:00",
        "actual_arrival": "2026-08-30T10:05:00",
        "delay_seconds": 300,
        "timestamp": "2026-08-30T10:05:00",
    }

    insert_trip_update(sample_trip_update)
    insert_trip_update(sample_trip_update)

    results = get_trip_updates("ROUTE_001")

    assert len(results) == 1


def test_trip_updates_are_returned_in_timestamp_order():
    later_update = {
        "trip_id": "TRIP_002",
        "route_id": "ROUTE_001",
        "stop_id": "STOP_002",
        "scheduled_arrival": "2026-08-30T11:00:00",
        "actual_arrival": "2026-08-30T11:03:00",
        "delay_seconds": 180,
        "timestamp": "2026-08-30T11:03:00",
    }

    earlier_update = {
        "trip_id": "TRIP_001",
        "route_id": "ROUTE_001",
        "stop_id": "STOP_001",
        "scheduled_arrival": "2026-08-30T10:00:00",
        "actual_arrival": "2026-08-30T10:05:00",
        "delay_seconds": 300,
        "timestamp": "2026-08-30T10:05:00",
    }

    # Insert in the wrong order on purpose
    insert_trip_update(later_update)
    insert_trip_update(earlier_update)

    results = get_trip_updates("ROUTE_001")

    assert len(results) == 2
    assert results[0]["timestamp"] == "2026-08-30T10:05:00"
    assert results[1]["timestamp"] == "2026-08-30T11:03:00"