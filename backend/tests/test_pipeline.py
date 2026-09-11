from backend.services import pipeline


def test_persist_collection_result(monkeypatch):
    stored_vehicles = []
    stored_updates = []

    def fake_insert_vehicle_position(record):
        stored_vehicles.append(record)

    def fake_insert_trip_update(record):
        stored_updates.append(record)

    monkeypatch.setattr(
        pipeline,
        "insert_vehicle_position",
        fake_insert_vehicle_position,
    )

    monkeypatch.setattr(
        pipeline,
        "insert_trip_update",
        fake_insert_trip_update,
    )

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

    result = pipeline.persist_collection_result(
        collection_result
    )

    assert len(stored_vehicles) == 1
    assert len(stored_updates) == 1

    assert result["vehicle_positions_processed"] == 1
    assert result["trip_updates_processed"] == 1


def test_query_and_analyse(monkeypatch):
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
        return sample_records

    monkeypatch.setattr(
        pipeline,
        "get_trip_updates_filtered",
        fake_get_trip_updates_filtered,
    )

    result = pipeline.query_and_analyse(
        route_id="R1"
    )

    route_result = result["route_performance"]["R1"]

    assert route_result["total_services"] == 2
    assert route_result["average_delay"] == 8.5
    assert route_result["on_time_count"] == 1
    assert route_result["severely_delayed_count"] == 1

    assert result["time_period_performance"]["Morning"][
        "total_services"
    ] == 1

    assert result["time_period_performance"]["Afternoon"][
        "total_services"
    ] == 1

def test_pipeline_with_database(monkeypatch, tmp_path):
    from backend.database import connection
    from backend.database.models import create_tables

    # Use a temporary database for this test.
    test_database = tmp_path / "test_pipeline.db"

    monkeypatch.setattr(
        connection,
        "DATABASE_PATH",
        test_database,
    )

    create_tables()

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

    persistence_result = pipeline.persist_collection_result(
        collection_result
    )

    assert persistence_result["vehicle_positions_processed"] == 1
    assert persistence_result["trip_updates_processed"] == 2

    analysis_result = pipeline.query_and_analyse(
        route_id="R1"
    )

    route_result = analysis_result["route_performance"]["R1"]

    assert route_result["total_services"] == 2
    assert route_result["average_delay"] == 8.5