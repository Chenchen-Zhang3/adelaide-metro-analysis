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


def test_get_stop_routes(monkeypatch):
    sample_routes = [
        {
            "route_id": "R1",
            "route_short_name": "R1",
            "route_long_name": "Test Route",
            "route_type": 3,
        }
    ]

    monkeypatch.setattr(
        "backend.api.app.get_routes_by_stop",
        lambda stop_id: sample_routes,
    )

    client = app.test_client()
    response = client.get("/api/stops/STOP_001/routes")

    assert response.status_code == 200
    assert response.get_json() == sample_routes


def test_get_stop_routes_from_database(monkeypatch, tmp_path):
    from backend.database import connection
    from backend.database.models import create_tables
    from backend.database.repository import (
        insert_route,
        insert_trip,
        insert_stop_time,
    )

    test_database = tmp_path / "test_stop_routes_api.db"

    monkeypatch.setattr(
        connection,
        "DATABASE_PATH",
        test_database,
    )

    create_tables()

    sample_route = {
        "route_id": "R1",
        "route_short_name": "R1",
        "route_long_name": "Test Route",
        "route_type": 3,
    }

    sample_trip = {
        "trip_id": "T1",
        "route_id": "R1",
        "service_id": "SVC1",
        "trip_headsign": "City",
        "direction_id": 0,
    }

    sample_stop_time = {
        "trip_id": "T1",
        "arrival_time": "10:00:00",
        "departure_time": "10:00:00",
        "stop_id": "STOP_001",
        "stop_sequence": 1,
    }

    insert_route(sample_route)
    insert_trip(sample_trip)
    insert_stop_time(sample_stop_time)

    client = app.test_client()
    response = client.get("/api/stops/STOP_001/routes")

    assert response.status_code == 200
    assert response.get_json() == [sample_route]



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



def test_get_stop_performance(monkeypatch):
    sample_analysis = {
        "route_performance": {},
        "stop_performance": {
            "S1": {
                "total_services": 2,
                "average_delay": 8.5,
                "early_count": 0,
                "on_time_count": 1,
                "delayed_count": 0,
                "severely_delayed_count": 1,
            }
        },
        "time_period_performance": {},
    }

    monkeypatch.setattr(
        "backend.api.app.query_and_analyse",
        lambda stop_id=None: sample_analysis,
    )

    client = app.test_client()
    response = client.get("/api/stops/S1/performance")

    assert response.status_code == 200
    assert response.get_json() == sample_analysis[
        "stop_performance"
    ]["S1"]


def test_get_stop_performance_not_found(monkeypatch):
    sample_analysis = {
        "route_performance": {},
        "stop_performance": {},
        "time_period_performance": {},
    }

    monkeypatch.setattr(
        "backend.api.app.query_and_analyse",
        lambda stop_id=None: sample_analysis,
    )

    client = app.test_client()
    response = client.get("/api/stops/UNKNOWN/performance")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Stop performance not found"
    }


def test_get_stop_performance_from_database(monkeypatch, tmp_path):
    from backend.database import connection
    from backend.database.models import create_tables
    from backend.database.repository import insert_trip_update

    test_database = tmp_path / "test_stop_performance_api.db"

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
        "route_id": "R2",
        "stop_id": "S1",
        "scheduled_arrival": "2026-09-11T13:48:00",
        "actual_arrival": "2026-09-11T14:00:00",
        "delay_seconds": 720,
        "timestamp": "2026-09-11T14:00:00",
    }

    insert_trip_update(first_update)
    insert_trip_update(second_update)

    client = app.test_client()
    response = client.get("/api/stops/S1/performance")

    result = response.get_json()

    assert response.status_code == 200
    assert result["total_services"] == 2
    assert result["average_delay"] == 8.5


def test_database_error(monkeypatch):
    import sqlite3

    def raise_database_error():
        raise sqlite3.DatabaseError("Test database error")

    monkeypatch.setattr(
        "backend.api.app.get_all_stops",
        raise_database_error,
    )

    client = app.test_client()
    response = client.get("/api/stops")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "Database error"
    }


def test_unknown_endpoint():
    client = app.test_client()
    response = client.get("/api/unknown")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Endpoint not found"
    }

def test_get_delay_hotspots(monkeypatch):
    sample_hotspots = [
        {
            "stop_id": "STOP_001",
            "total_services": 20,
            "average_delay": 8.5,
        }
    ]

    def mock_query_and_analyse(**kwargs):
        assert kwargs["min_services"] == 10
        return {"delay_hotspots": sample_hotspots}

    monkeypatch.setattr(
        "backend.api.app.query_and_analyse",
        mock_query_and_analyse,
    )

    client = app.test_client()
    response = client.get("/api/analysis/hotspots")

    assert response.status_code == 200
    assert response.get_json() == {
        "hotspots": sample_hotspots,
        "total_hotspots": 1,
    }


def test_get_delay_hotspots_invalid_min_services():
    client = app.test_client()

    response = client.get(
        "/api/analysis/hotspots?min_services=0"
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_get_delay_hotspots_filters(monkeypatch):
    captured = {}

    def mock_query_and_analyse(**kwargs):
        captured.update(kwargs)
        return {"delay_hotspots": []}

    monkeypatch.setattr(
        "backend.api.app.query_and_analyse",
        mock_query_and_analyse,
    )

    client = app.test_client()
    response = client.get(
        "/api/analysis/hotspots"
        "?route_id=G10"
        "&stop_id=STOP_001"
        "&min_services=5"
    )

    assert response.status_code == 200
    assert captured["route_id"] == "G10"
    assert captured["stop_id"] == "STOP_001"
    assert captured["min_services"] == 5
    assert response.get_json()["total_hotspots"] == 0