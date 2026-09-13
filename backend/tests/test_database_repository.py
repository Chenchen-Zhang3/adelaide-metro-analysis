import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import backend.database.connection as database_connection
from backend.database.models import create_tables
from backend.database.repository import (
    insert_route,
    insert_stop,
    insert_trip,
    insert_stop_time,
    insert_trip_update,
    insert_vehicle_position,
    get_stop,
    get_trip_updates,
    get_trip_updates_by_stop,
    get_trip_updates_by_time_range,
    get_trip_updates_filtered,
    get_vehicle_positions_filtered,
)


# Find the project root folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Set the shared fixture folder.
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures"


def load_fixture(filename):
    # Build the fixture file path.
    file_path = FIXTURE_PATH / filename

    # Load the JSON fixture data.
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


@pytest.fixture(autouse=True)
def temporary_database(tmp_path, monkeypatch):
    # Create a temporary database for each test.
    test_database_path = tmp_path / "test_adelaide_metro.db"

    # Replace the normal database path.
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
    # Load the shared stop fixture.
    stops = load_fixture("sample_stops.json")

    # Select the first stop.
    sample_stop = stops[0]

    # Store the stop.
    insert_stop(sample_stop)

    # Retrieve the stop.
    result = get_stop(sample_stop["stop_id"])

    # Check the stored values.
    assert result is not None
    assert result["stop_id"] == sample_stop["stop_id"]
    assert result["stop_name"] == sample_stop["stop_name"]
    assert result["stop_lat"] == sample_stop["stop_lat"]
    assert result["stop_lon"] == sample_stop["stop_lon"]


def test_trip_update_persistence_and_retrieval():
    # Load the shared trip update fixture.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Select the first update.
    sample_update = trip_updates[0]

    # Store the trip update.
    insert_trip_update(sample_update)

    # Retrieve updates for the route.
    results = get_trip_updates(sample_update["route_id"])

    # Check the stored values.
    assert len(results) == 1
    assert results[0]["trip_id"] == sample_update["trip_id"]
    assert results[0]["route_id"] == sample_update["route_id"]
    assert results[0]["stop_id"] == sample_update["stop_id"]
    assert results[0]["delay_seconds"] == sample_update["delay_seconds"]
    assert results[0]["timestamp"] == sample_update["timestamp"]


def test_duplicate_trip_update_is_not_stored_twice():
    # Load the shared trip update fixture.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Select the first update.
    sample_update = trip_updates[0]

    # Insert the same record twice.
    insert_trip_update(sample_update)
    insert_trip_update(sample_update)

    # Retrieve the stored records.
    results = get_trip_updates(sample_update["route_id"])

    # Check that only one copy exists.
    assert len(results) == 1


def test_trip_update_allows_missing_timestamp():
    # Load the shared trip update fixture.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Copy one fixture record.
    sample_update = trip_updates[0].copy()

    # Remove the optional timestamp.
    sample_update["timestamp"] = None

    # Store the record.
    insert_trip_update(sample_update)

    # Retrieve the stored record.
    results = get_trip_updates(sample_update["route_id"])

    # Check the missing timestamp.
    assert len(results) == 1
    assert results[0]["timestamp"] is None


def test_timestamped_records_come_before_missing_timestamp():
    # Load the shared trip update fixture.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Copy a timestamped record.
    timestamped_update = trip_updates[0].copy()

    # Copy a record without a timestamp.
    missing_timestamp_update = trip_updates[0].copy()

    # Give the second record a different ID.
    missing_timestamp_update["trip_id"] += "_NO_TIMESTAMP"

    # Remove the timestamp.
    missing_timestamp_update["timestamp"] = None

    # Insert the missing timestamp record first.
    insert_trip_update(missing_timestamp_update)

    # Insert the timestamped record second.
    insert_trip_update(timestamped_update)

    # Retrieve both records.
    results = get_trip_updates(timestamped_update["route_id"])

    # Check that timestamped data appears first.
    assert len(results) == 2
    assert results[0]["timestamp"] == timestamped_update["timestamp"]
    assert results[1]["timestamp"] is None


def test_route_based_query_returns_only_selected_route():
    # Load the shared trip update fixture.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Copy the target route record.
    first_route_update = trip_updates[0].copy()

    # Copy a record for another route.
    second_route_update = trip_updates[0].copy()

    # Change IDs for the second route.
    second_route_update["trip_id"] += "_OTHER"
    second_route_update["route_id"] += "_OTHER"

    # Insert both route records.
    insert_trip_update(first_route_update)
    insert_trip_update(second_route_update)

    # Query only the first route.
    results = get_trip_updates(first_route_update["route_id"])

    # Check that only the selected route is returned.
    assert len(results) == 1
    assert results[0]["route_id"] == first_route_update["route_id"]


def test_stop_based_query_returns_only_selected_stop():
    # Load the shared trip update fixture.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Copy the target stop record.
    first_stop_update = trip_updates[0].copy()

    # Copy a record for another stop.
    second_stop_update = trip_updates[0].copy()

    # Change IDs for the second stop.
    second_stop_update["trip_id"] += "_OTHER"
    second_stop_update["stop_id"] += "_OTHER"

    # Insert both stop records.
    insert_trip_update(first_stop_update)
    insert_trip_update(second_stop_update)

    # Query only the first stop.
    results = get_trip_updates_by_stop(
        first_stop_update["stop_id"]
    )

    # Check that only the selected stop is returned.
    assert len(results) == 1
    assert results[0]["stop_id"] == first_stop_update["stop_id"]


def test_time_range_query_returns_only_matching_records():
    # Load the shared trip update fixture.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Insert all fixture records.
    for update in trip_updates:
        insert_trip_update(update)

    # Use the first fixture timestamp.
    start_time = trip_updates[0]["timestamp"]
    end_time = trip_updates[0]["timestamp"]

    # Query the selected time range.
    results = get_trip_updates_by_time_range(
        start_time,
        end_time,
    )

    # Check that only the matching record is returned.
    assert len(results) == 1
    assert results[0]["trip_id"] == trip_updates[0]["trip_id"]
    assert results[0]["timestamp"] == trip_updates[0]["timestamp"]


def test_combined_query_filters():
    # Load the shared trip update fixture.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Copy the target record.
    target_update = trip_updates[0].copy()

    # Copy a record for another stop.
    other_update = trip_updates[0].copy()

    # Change the second record IDs.
    other_update["trip_id"] += "_OTHER"
    other_update["stop_id"] += "_OTHER"

    # Insert both records.
    insert_trip_update(target_update)
    insert_trip_update(other_update)

    # Query by route, stop and time.
    results = get_trip_updates_filtered(
        route_id=target_update["route_id"],
        stop_id=target_update["stop_id"],
        start_time=target_update["timestamp"],
        end_time=target_update["timestamp"],
    )

    # Check that only the target record is returned.
    assert len(results) == 1
    assert results[0]["trip_id"] == target_update["trip_id"]
    assert results[0]["route_id"] == target_update["route_id"]
    assert results[0]["stop_id"] == target_update["stop_id"]
    assert results[0]["timestamp"] == target_update["timestamp"]


def test_route_insertion():
    # Load the shared route fixture.
    routes = load_fixture("sample_routes.json")

    # Select the first route.
    sample_route = routes[0]

    # Store the route.
    insert_route(sample_route)

    # Open the database connection.
    connection = database_connection.get_connection()
    cursor = connection.cursor()

    # Retrieve the stored route.
    cursor.execute(
        """
        SELECT *
        FROM routes
        WHERE route_id = ?
        """,
        (sample_route["route_id"],),
    )
    result = cursor.fetchone()

    # Close the database connection.
    connection.close()

    # Check the stored route.
    assert result is not None
    assert result["route_id"] == sample_route["route_id"]
    assert result["route_type"] == sample_route["route_type"]


def test_trip_insertion():
    # Load the shared trip fixture.
    trips = load_fixture("sample_trips.json")

    # Select the first trip.
    sample_trip = trips[0]

    # Store the trip.
    insert_trip(sample_trip)

    # Open the database connection.
    connection = database_connection.get_connection()
    cursor = connection.cursor()

    # Retrieve the stored trip.
    cursor.execute(
        """
        SELECT *
        FROM trips
        WHERE trip_id = ?
        """,
        (sample_trip["trip_id"],),
    )
    result = cursor.fetchone()

    # Close the database connection.
    connection.close()

    # Check the stored trip.
    assert result is not None
    assert result["trip_id"] == sample_trip["trip_id"]
    assert result["route_id"] == sample_trip["route_id"]


def test_stop_time_insertion():
    # Load the shared stop time fixture.
    stop_times = load_fixture("sample_stop_times.json")

    # Select the first stop time.
    sample_stop_time = stop_times[0]

    # Store the stop time.
    insert_stop_time(sample_stop_time)

    # Open the database connection.
    connection = database_connection.get_connection()
    cursor = connection.cursor()

    # Retrieve the stored stop time.
    cursor.execute(
        """
        SELECT *
        FROM stop_times
        WHERE trip_id = ?
          AND stop_id = ?
          AND stop_sequence = ?
        """,
        (
            sample_stop_time["trip_id"],
            sample_stop_time["stop_id"],
            sample_stop_time["stop_sequence"],
        ),
    )
    result = cursor.fetchone()

    # Close the database connection.
    connection.close()

    # Check the stored stop time.
    assert result is not None
    assert result["trip_id"] == sample_stop_time["trip_id"]
    assert result["stop_id"] == sample_stop_time["stop_id"]


def test_duplicate_stop_time_is_not_stored_twice():
    # Load the shared stop time fixture.
    stop_times = load_fixture("sample_stop_times.json")

    # Select the first stop time.
    sample_stop_time = stop_times[0]

    # Insert the same record twice.
    insert_stop_time(sample_stop_time)
    insert_stop_time(sample_stop_time)

    # Open the database connection.
    connection = database_connection.get_connection()
    cursor = connection.cursor()

    # Count matching records.
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM stop_times
        WHERE trip_id = ?
          AND stop_id = ?
          AND stop_sequence = ?
        """,
        (
            sample_stop_time["trip_id"],
            sample_stop_time["stop_id"],
            sample_stop_time["stop_sequence"],
        ),
    )
    count = cursor.fetchone()[0]

    # Close the database connection.
    connection.close()

    # Check that only one copy exists.
    assert count == 1


def test_vehicle_position_insertion():
    # Load the shared vehicle fixture.
    vehicles = load_fixture("sample_vehicles.json")

    # Select the first vehicle record.
    sample_vehicle = vehicles[0]

    # Store the vehicle position.
    insert_vehicle_position(sample_vehicle)

    # Open the database connection.
    connection = database_connection.get_connection()
    cursor = connection.cursor()

    # Retrieve the stored vehicle position.
    cursor.execute(
        """
        SELECT *
        FROM vehicle_positions
        WHERE vehicle_id = ?
        """,
        (sample_vehicle["vehicle_id"],),
    )
    result = cursor.fetchone()

    # Close the database connection.
    connection.close()

    # Check the stored vehicle position.
    assert result is not None
    assert result["vehicle_id"] == sample_vehicle["vehicle_id"]
    assert result["latitude"] == sample_vehicle["latitude"]
    assert result["longitude"] == sample_vehicle["longitude"]


def test_duplicate_vehicle_position_is_not_stored_twice():
    # Load the shared vehicle fixture.
    vehicles = load_fixture("sample_vehicles.json")

    # Select the first vehicle record.
    sample_vehicle = vehicles[0]

    # Insert the same record twice.
    insert_vehicle_position(sample_vehicle)
    insert_vehicle_position(sample_vehicle)

    # Open the database connection.
    connection = database_connection.get_connection()
    cursor = connection.cursor()

    # Count matching records.
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM vehicle_positions
        WHERE vehicle_id = ?
        """,
        (sample_vehicle["vehicle_id"],),
    )
    count = cursor.fetchone()[0]

    # Close the database connection.
    connection.close()

    # Check that only one copy exists.
    assert count == 1


def test_invalid_time_range_raises_error():
    # Load the shared trip update fixture.
    trip_updates = load_fixture("sample_trip_updates.json")

    # Read the fixture timestamp.
    end_time = trip_updates[0]["timestamp"]

    # Convert the timestamp to a datetime.
    end_datetime = datetime.fromisoformat(end_time)

    # Create a later start timestamp.
    start_datetime = end_datetime + timedelta(hours=1)

    # Convert the start timestamp back to ISO format.
    start_time = start_datetime.isoformat()

    # Check that an invalid range raises an error.
    with pytest.raises(ValueError):
        get_trip_updates_by_time_range(
            start_time,
            end_time,
        )
        
def test_vehicle_position_query_by_vehicle():
    # Load the shared vehicle fixture.
    vehicles = load_fixture("sample_vehicles.json")

    # Insert all vehicle records.
    for vehicle in vehicles:
        insert_vehicle_position(vehicle)

    # Query the first vehicle.
    results = get_vehicle_positions_filtered(
        vehicle_id=vehicles[0]["vehicle_id"]
    )

    # Check that only the selected vehicle is returned.
    assert len(results) == 1
    assert results[0]["vehicle_id"] == vehicles[0]["vehicle_id"]


def test_vehicle_position_query_by_route():
    # Load the shared vehicle fixture.
    vehicles = load_fixture("sample_vehicles.json")

    # Insert all vehicle records.
    for vehicle in vehicles:
        insert_vehicle_position(vehicle)

    # Query the first vehicle route.
    results = get_vehicle_positions_filtered(
        route_id=vehicles[0]["route_id"]
    )

    # Check that only the selected route is returned.
    assert len(results) == 1
    assert results[0]["route_id"] == vehicles[0]["route_id"]


def test_vehicle_position_query_by_time_range():
    # Load the shared vehicle fixture.
    vehicles = load_fixture("sample_vehicles.json")

    # Insert all vehicle records.
    for vehicle in vehicles:
        insert_vehicle_position(vehicle)

    # Use the first vehicle timestamp.
    timestamp = vehicles[0]["timestamp"]

    # Query the selected time.
    results = get_vehicle_positions_filtered(
        start_time=timestamp,
        end_time=timestamp,
    )

    # Check that only the matching record is returned.
    assert len(results) == 1
    assert results[0]["vehicle_id"] == vehicles[0]["vehicle_id"]
    assert results[0]["timestamp"] == timestamp


def test_vehicle_position_combined_filters():
    # Load the shared vehicle fixture.
    vehicles = load_fixture("sample_vehicles.json")

    # Insert all vehicle records.
    for vehicle in vehicles:
        insert_vehicle_position(vehicle)

    # Select the first vehicle record.
    target_vehicle = vehicles[0]

    # Query vehicle, route and time together.
    results = get_vehicle_positions_filtered(
        vehicle_id=target_vehicle["vehicle_id"],
        route_id=target_vehicle["route_id"],
        start_time=target_vehicle["timestamp"],
        end_time=target_vehicle["timestamp"],
    )

    # Check that only the target record is returned.
    assert len(results) == 1
    assert results[0]["vehicle_id"] == target_vehicle["vehicle_id"]
    assert results[0]["route_id"] == target_vehicle["route_id"]
    assert results[0]["latitude"] == target_vehicle["latitude"]
    assert results[0]["longitude"] == target_vehicle["longitude"]