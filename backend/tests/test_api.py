from backend.api.app import app


def test_get_stops(monkeypatch):
    sample_stops = [
        {
            "stop_id": "STOP_001",
            "stop_name": "Victoria Square",
            "stop_lat": -34.9296,
            "stop_lon": 138.5999,
        },
        {
            "stop_id": "STOP_002",
            "stop_name": "Rundle Mall",
            "stop_lat": -34.9227,
            "stop_lon": 138.6023,
        },
    ]

    monkeypatch.setattr(
        "backend.api.app.get_all_stops",
        lambda: sample_stops,
    )

    client = app.test_client()
    response = client.get("/api/stops")

    assert response.status_code == 200
    assert response.get_json() == sample_stops


def test_get_stops_from_database(monkeypatch, tmp_path):
    from backend.database import connection
    from backend.database.models import create_tables
    from backend.database.repository import insert_stop

    test_database = tmp_path / "test_api.db"

    monkeypatch.setattr(
        connection,
        "DATABASE_PATH",
        test_database,
    )

    create_tables()

    sample_stop = {
        "stop_id": "STOP_001",
        "stop_name": "Victoria Square",
        "stop_lat": -34.9296,
        "stop_lon": 138.5999,
    }

    insert_stop(sample_stop)

    client = app.test_client()
    response = client.get("/api/stops")

    assert response.status_code == 200
    assert response.get_json() == [sample_stop]