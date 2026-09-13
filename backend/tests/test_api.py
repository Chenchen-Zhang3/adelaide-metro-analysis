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


def test_get_stop_detail(monkeypatch):
    sample_stop = {
        "stop_id": "STOP_001",
        "stop_name": "Victoria Square",
        "stop_lat": -34.9296,
        "stop_lon": 138.5999,
    }

    monkeypatch.setattr(
        "backend.api.app.get_stop",
        lambda stop_id: sample_stop,
    )

    client = app.test_client()
    response = client.get("/api/stops/STOP_001")

    assert response.status_code == 200
    assert response.get_json() == sample_stop


def test_get_stop_detail_not_found(monkeypatch):
    monkeypatch.setattr(
        "backend.api.app.get_stop",
        lambda stop_id: None,
    )

    client = app.test_client()
    response = client.get("/api/stops/UNKNOWN")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Stop not found"
    }


def test_get_stop_detail_from_database(monkeypatch, tmp_path):
    from backend.database import connection
    from backend.database.models import create_tables
    from backend.database.repository import insert_stop

    test_database = tmp_path / "test_stop_detail_api.db"

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
    response = client.get("/api/stops/STOP_001")

    assert response.status_code == 200
    assert response.get_json() == sample_stop


def test_get_route_performance(monkeypatch):
    sample_analysis = {
        "route_performance": {
            "R1": {
                "total_services": 2,
                "average_delay": 8.5,
                "early_count": 0,
                "on_time_count": 1,
                "delayed_count": 0,
                "severely_delayed_count": 1,
            }
        },
        "stop_performance": {},
        "time_period_performance": {},
    }

    monkeypatch.setattr(
        "backend.api.app.query_and_analyse",
        lambda route_id=None: sample_analysis,
    )

    client = app.test_client()
    response = client.get("/api/routes/R1/performance")

    assert response.status_code == 200
    assert response.get_json() == sample_analysis[
        "route_performance"
    ]["R1"]


def test_get_route_performance_not_found(monkeypatch):
    sample_analysis = {
        "route_performance": {},
        "stop_performance": {},
        "time_period_performance": {},
    }

    monkeypatch.setattr(
        "backend.api.app.query_and_analyse",
        lambda route_id=None: sample_analysis,
    )

    client = app.test_client()
    response = client.get("/api/routes/UNKNOWN/performance")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Route performance not found"
    }



def test_get_route_performance_from_database(monkeypatch, tmp_path):
    from backend.database import connection
    from backend.database.models import create_tables
    from backend.database.repository import insert_trip_update

    test_database = tmp_path / "test_route_performance_api.db"

    monkeypatch.setattr(
        connection,
        "DATABASE_PATH",
        test_database,
    )

    create_tables()

    first_update = {
        "trip_id": "T1",
        "route_id": "R1",
        "stop_id": "S1",
        "scheduled_arrival": "2026-09-11T08:55:00",
        "actual_arrival": "2026-09-11T09:00:00",
        "delay_seconds": 300,
        "timestamp": "2026-09-11T09:00:00",
    }

    second_update = {
        "trip_id": "T2",
        "route_id": "R1",
        "stop_id": "S2",
        "scheduled_arrival": "2026-09-11T13:48:00",
        "actual_arrival": "2026-09-11T14:00:00",
        "delay_seconds": 720,
        "timestamp": "2026-09-11T14:00:00",
    }

    insert_trip_update(first_update)
    insert_trip_update(second_update)

    client = app.test_client()
    response = client.get("/api/routes/R1/performance")

    result = response.get_json()

    assert response.status_code == 200
    assert result["total_services"] == 2
    assert result["average_delay"] == 8.5
    assert result["on_time_count"] == 1
    assert result["severely_delayed_count"] == 1