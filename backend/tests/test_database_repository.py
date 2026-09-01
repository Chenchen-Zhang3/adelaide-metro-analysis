import json
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


# Find the project root folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Set the path to the shared fixture data.
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures"


def load_fixture(filename):
    # Load JSON test data from the shared fixtures.
    file_path = FIXTURE_PATH / filename

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


@pytest.fixture(autouse=True)
def temporary_database(tmp_path, monkeypatch):
    # Create a temporary database for each test.
    test_database_path = tmp_path / "test_adelaide_metro.db"

    # Replace the normal database path during testing.
    monkeypatch.setattr(
        database_connection,
        "DATABASE_PATH",
        test_database_path,
    )

    # Create fresh database tables.
    create_tables()

    # Run the test.
    yield


def test_stop_persistence_and_retrieval():
    # Load the shared stop fixture data.
    stops = load_fixture("sample_stops.json")

    # Use the first stop from the shared fixture.
    sample_stop = stops[0]

    # Store the stop in the database.
    insert_stop(sample_stop)

    # Retrieve the stop by its ID.
    result = get_stop(sample_stop["stop_id"])

    # Check that the stop was retrieved correctly.
    assert result is not None
    assert result["stop_id"] == sample_stop["stop_id"]
    assert result["stop_name"] == sample_stop["stop_name"]
    assert result["stop_lat"] == sample_stop["stop_lat"]
    assert result["stop_lon"] == sample_stop["stop_lon"]


def test_trip_update_persistence_and_retrieval():
    # Load the shared trip update fixture data.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Use the first trip update from the shared fixture.
    sample_update = trip_updates[0]

    # Store the trip update in the database.
    insert_trip_update(sample_update)

    # Retrieve updates for the same route.
    results = get_trip_updates(sample_update["route_id"])

    # Check that the trip update was stored correctly.
    assert len(results) == 1
    assert results[0]["trip_id"] == sample_update["trip_id"]
    assert results[0]["route_id"] == sample_update["route_id"]
    assert results[0]["stop_id"] == sample_update["stop_id"]
    assert results[0]["delay_seconds"] == sample_update["delay_seconds"]
    assert results[0]["timestamp"] == sample_update["timestamp"]


def test_duplicate_trip_update_is_not_stored_twice():
    # Load the shared trip update fixture data.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Use the first trip update from the shared fixture.
    sample_update = trip_updates[0]

    # Insert the same record twice.
    insert_trip_update(sample_update)
    insert_trip_update(sample_update)

    # Retrieve the stored records.
    results = get_trip_updates(sample_update["route_id"])

    # Check that only one copy was stored.
    assert len(results) == 1


def test_trip_update_allows_missing_timestamp():
    # Load the shared trip update fixture data.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Copy a fixture record for this test.
    sample_update = trip_updates[0].copy()

    # Remove the optional timestamp value.
    sample_update["timestamp"] = None

    # Store the record without a timestamp.
    insert_trip_update(sample_update)

    # Retrieve the stored record.
    results = get_trip_updates(sample_update["route_id"])

    # Check that the nullable timestamp is supported.
    assert len(results) == 1
    assert results[0]["timestamp"] is None