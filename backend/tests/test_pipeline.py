import json
from pathlib import Path

from backend.services import pipeline


# Find the project root folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Set the shared fixture folder.
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures"


def load_fixture(filename):
    # Build the fixture file path.
    file_path = FIXTURE_PATH / filename

    # Load the shared JSON fixture.
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def test_persist_collection_result(monkeypatch):
    # Track the collection sent to the repository transaction.
    persisted_collections = []

    def fake_persist_realtime_collection(vehicle_positions, trip_updates):
        persisted_collections.append((vehicle_positions, trip_updates))
        return {
            "vehicle_positions_received": len(vehicle_positions),
            "vehicle_positions_inserted": len(vehicle_positions),
            "trip_updates_received": len(trip_updates),
            "trip_updates_inserted": len(trip_updates),
        }

    # Replace the repository transaction for this unit test.
    monkeypatch.setattr(
        pipeline,
        "persist_realtime_collection",
        fake_persist_realtime_collection,
    )

    # Create a sample collection result.
    collection_result = {
        "vehicle_positions": [
            {
                "vehicle_id": "V1",
                "latitude": -34.9285,
                "longitude": 138.6007,
            }
        ],
        "trip_updates": [
            {
                "trip_id": "T1",
                "route_id": "R1",
                "stop_id": "S1",
                "delay_seconds": 300,
            }
        ],
    }

    # Persist the sample collection.
    result = pipeline.persist_collection_result(
        collection_result
    )

    # Check the transaction received both record groups.
    assert len(persisted_collections) == 1
    assert len(persisted_collections[0][0]) == 1
    assert len(persisted_collections[0][1]) == 1

    # Check returned processing counts.
    assert result["vehicle_positions_processed"] == 1
    assert result["trip_updates_processed"] == 1
    assert result["vehicle_positions_inserted"] == 1
    assert result["trip_updates_inserted"] == 1


def test_query_and_analyse(monkeypatch):
    # Create sample database records.
    sample_records = [
        {
            "route_id": "R1",
            "stop_id": "S1",
            "delay_seconds": 300,
            "timestamp": "2026-09-11T09:00:00",
        },
        {
            "route_id": "R1",
            "stop_id": "S1",
            "delay_seconds": 720,
            "timestamp": "2026-09-11T14:00:00",
        },
    ]

    def fake_get_trip_updates_filtered(
        route_id=None,
        stop_id=None,
        start_time=None,
        end_time=None,
    ):
        # Return sample query records.
        return sample_records

    # Replace the database query for the test.
    monkeypatch.setattr(
        pipeline,
        "get_trip_updates_filtered",
        fake_get_trip_updates_filtered,
    )

    # Run the analysis integration.
    result = pipeline.query_and_analyse(
        route_id="R1"
    )

    # Read the route analysis result.
    route_result = result["route_performance"]["R1"]

    # Check route performance values.
    assert route_result["total_services"] == 2
    assert route_result["average_delay"] == 8.5
    assert route_result["on_time_count"] == 1
    assert route_result["severely_delayed_count"] == 1

    # Check morning records.
    assert result["time_period_performance"]["Morning"][
        "total_services"
    ] == 1

    # Check afternoon records.
    assert result["time_period_performance"]["Afternoon"][
        "total_services"
    ] == 1


def test_pipeline_with_database(monkeypatch, tmp_path):
    # Import database components for integration testing.
    from backend.database import connection
    from backend.database.models import create_tables

    # Use a temporary database.
    test_database = tmp_path / "test_pipeline.db"

    # Replace the normal database path.
    monkeypatch.setattr(
        connection,
        "DATABASE_PATH",
        test_database,
    )

    # Create fresh database tables.
    create_tables()

    # Create sample realtime records.
    collection_result = {
        "vehicle_positions": [
            {
                "vehicle_id": "V1",
                "trip_id": "T1",
                "route_id": "R1",
                "latitude": -34.9285,
                "longitude": 138.6007,
                "timestamp": "2026-09-11T09:00:00",
            }
        ],
        "trip_updates": [
            {
                "trip_id": "T1",
                "route_id": "R1",
                "stop_id": "S1",
                "scheduled_arrival": "2026-09-11T08:55:00",
                "actual_arrival": "2026-09-11T09:00:00",
                "delay_seconds": 300,
                "timestamp": "2026-09-11T09:00:00",
            },
            {
                "trip_id": "T2",
                "route_id": "R1",
                "stop_id": "S1",
                "scheduled_arrival": "2026-09-11T13:48:00",
                "actual_arrival": "2026-09-11T14:00:00",
                "delay_seconds": 720,
                "timestamp": "2026-09-11T14:00:00",
            },
        ],
    }

    # Persist realtime records.
    persistence_result = pipeline.persist_collection_result(
        collection_result
    )

    # Check persistence counts.
    assert persistence_result["vehicle_positions_processed"] == 1
    assert persistence_result["trip_updates_processed"] == 2

    # Query and analyse stored records.
    analysis_result = pipeline.query_and_analyse(
        route_id="R1"
    )

    # Read the route result.
    route_result = analysis_result["route_performance"]["R1"]

    # Check database-to-analysis integration.
    assert route_result["total_services"] == 2
    assert route_result["average_delay"] == 8.5


def test_run_collection_and_persist_repeats_cycles():
    # Store polling waits.
    waits = []

    class FakeSettings:
        # Use a short test polling interval.
        polling_interval_seconds = 15

    class FakeClient:
        # Provide collector settings.
        settings = FakeSettings()

    class FakeCollector:
        def __init__(self):
            # Attach the fake client.
            self.client = FakeClient()

            # Track collection calls.
            self.calls = 0

        def collect_once(self):
            # Count each collection cycle.
            self.calls += 1

            # Return an empty valid cycle.
            return {
                "vehicle_positions": [],
                "trip_updates": [],
            }

    # Create the fake collector.
    collector = FakeCollector()

    # Run two collection cycles.
    results = pipeline.run_collection_and_persist(
        collector,
        max_cycles=2,
        sleep_function=waits.append,
    )

    # Check that two cycles were executed.
    assert collector.calls == 2
    assert len(results) == 2

    # Check that one polling wait occurred.
    assert waits == [15]


def test_run_collection_and_persist_continues_after_retry_failure():
    # Store polling waits.
    waits = []

    class FakeSettings:
        # Use a short test polling interval.
        polling_interval_seconds = 20

    class FakeClient:
        # Provide collector settings.
        settings = FakeSettings()

    class FakeCollector:
        def __init__(self):
            # Attach the fake client.
            self.client = FakeClient()

            # Track collection calls.
            self.calls = 0

        def collect_once(self):
            # Count each collection cycle.
            self.calls += 1

            # Fail the first collection cycle.
            if self.calls == 1:
                raise pipeline.GTFSRealtimeRetryExhaustedError(
                    "Temporary feed failure"
                )

            # Return a valid second cycle.
            return {
                "vehicle_positions": [],
                "trip_updates": [],
            }

    # Create the fake collector.
    collector = FakeCollector()

    # Run two collection cycles.
    results = pipeline.run_collection_and_persist(
        collector,
        max_cycles=2,
        sleep_function=waits.append,
    )

    # Check that both cycles were attempted.
    assert collector.calls == 2

    # Check that the successful cycle was kept.
    assert len(results) == 1

    # Check that polling continued after failure.
    assert waits == [20]


def test_run_collection_and_persist_keeps_historical_records(
    monkeypatch,
    tmp_path,
):
    # Import database components.
    from backend.database import connection
    from backend.database.models import create_tables
    from backend.database.repository import (
        get_trip_updates_filtered,
        get_vehicle_positions_filtered,
    )

    # Use a temporary database.
    test_database = tmp_path / "test_history.db"

    # Replace the normal database path.
    monkeypatch.setattr(
        connection,
        "DATABASE_PATH",
        test_database,
    )

    # Create fresh database tables.
    create_tables()

    # Load shared realtime fixtures.
    vehicles = load_fixture("sample_vehicles.json")
    trip_updates = load_fixture("sample_trip_updates.json")

    class FakeSettings:
        # Use a short test polling interval.
        polling_interval_seconds = 1

    class FakeClient:
        # Provide collector settings.
        settings = FakeSettings()

    class FakeCollector:
        def __init__(self):
            # Attach the fake client.
            self.client = FakeClient()

            # Prepare two historical cycles.
            self.cycles = [
                {
                    "vehicle_positions": [vehicles[0]],
                    "trip_updates": [trip_updates[0]],
                },
                {
                    "vehicle_positions": [vehicles[1]],
                    "trip_updates": [trip_updates[1]],
                },
            ]

        def collect_once(self):
            # Return the next historical cycle.
            return self.cycles.pop(0)

    # Create the fake collector.
    collector = FakeCollector()

    # Run and persist two cycles.
    pipeline.run_collection_and_persist(
        collector,
        max_cycles=2,
        sleep_function=lambda seconds: None,
    )

    # Query all stored trip updates.
    stored_updates = get_trip_updates_filtered()

    # Query all stored vehicle positions.
    stored_vehicles = get_vehicle_positions_filtered()

    # Check that both historical cycles remain stored.
    assert len(stored_updates) == 2
    assert len(stored_vehicles) == 2

    # Check historical timestamps.
    assert stored_updates[0]["timestamp"] == trip_updates[0]["timestamp"]
    assert stored_updates[1]["timestamp"] == trip_updates[1]["timestamp"]

    # Check vehicle history timestamps.
    assert stored_vehicles[0]["timestamp"] == vehicles[0]["timestamp"]
    assert stored_vehicles[1]["timestamp"] == vehicles[1]["timestamp"]
