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


def test_get_routes(monkeypatch):
    sample_routes = [
        {
            "route_id": "100E",
            "route_short_name": "100E",
            "route_long_name": "Test Route",
            "route_type": 3,
        },
        {
            "route_id": "BEL",
            "route_short_name": "BEL",
            "route_long_name": "Belair Line",
            "route_type": 2,
        },
    ]

    monkeypatch.setattr(
        "backend.api.app.get_all_routes",
        lambda: sample_routes,
    )

    client = app.test_client()
    response = client.get("/api/routes")

    assert response.status_code == 200
    assert response.get_json() == sample_routes


def test_get_routes_from_database(monkeypatch, tmp_path):
    from backend.database import connection
    from backend.database.models import create_tables
    from backend.database.repository import insert_route

    test_database = tmp_path / "test_routes_api.db"

    monkeypatch.setattr(
        connection,
        "DATABASE_PATH",
        test_database,
    )

    create_tables()

    sample_route = {
        "route_id": "100E",
        "route_short_name": "100E",
        "route_long_name": "Test Route",
        "route_type": 3,
    }

    insert_route(sample_route)

    client = app.test_client()
    response = client.get("/api/routes")

    assert response.status_code == 200
    assert response.get_json() == [sample_route]