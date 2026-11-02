"""Real SQLite -> prediction aggregation -> HTTP, using disposable data only."""
from datetime import datetime, timedelta, timezone

import pytest

from backend.api.app import app
from backend.database import connection, repository
from backend.database.models import create_tables


@pytest.fixture(params=["2026-09-26T09:00:00+09:30", "2026-10-20T09:00:00+10:30"])
def observations(request, monkeypatch, tmp_path):
    monkeypatch.setattr(connection, "DATABASE_PATH", tmp_path / "performance.db")
    create_tables()
    start = datetime.fromisoformat(request.param)
    for name, route, stop, seconds, delay in [
        ("before", "R1", "S1", -1, 60),
        ("start", "R1", "S1", 0, 120),
        ("middle", "R1", "S2", 300, 240),
        ("end", "R1", "S1", 600, 600),
        ("after", "R1", "S1", 601, 180),
        ("other-route", "R2", "S1", 300, 1200),
        ("undated", "R1", "S1", None, 1800),
    ]:
        repository.insert_trip_update({
            "trip_id": name, "route_id": route, "stop_id": stop,
            # Arrival is deliberately outside the query: filter observations.
            "scheduled_arrival": (start + timedelta(hours=2)).isoformat(),
            "delay_seconds": delay,
            "timestamp": None if seconds is None else (
                start + timedelta(seconds=seconds)
            ).isoformat(),
        })
    return start


@pytest.fixture(params=["routes/R1", "stops/S1"])
def endpoint(request):
    return f"/api/{request.param}/performance"


def window(start):
    return {"start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=10)).isoformat()}


def test_inclusive_range_isolated_route_or_stop(observations, endpoint):
    response = app.test_client().get(endpoint, query_string=window(observations))
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_services"] == 3
    assert data["average_delay"] == (5.33 if "/routes/" in endpoint else 10.67)


def test_equivalent_utc_offsets_select_same_observations(observations, endpoint):
    client = app.test_client()
    local = client.get(endpoint, query_string=window(observations))
    utc = {name: datetime.fromisoformat(value).astimezone(timezone.utc)
           .isoformat().replace("+00:00", "Z")
           for name, value in window(observations).items()}
    response = client.get(endpoint, query_string=utc)
    assert response.status_code == 200
    assert response.get_json() == local.get_json()


def test_future_window_does_not_fall_back_to_history(observations, endpoint):
    response = app.test_client().get(endpoint, query_string={
        "start_time": "2030-01-01T00:00:00Z",
        "end_time": "2030-01-02T00:00:00Z",
    })
    assert response.status_code == 404
    kind = "Route" if "/routes/" in endpoint else "Stop"
    assert response.get_json() == {"error": f"{kind} performance not found"}


def test_equal_bounds_include_exact_end_observation(observations, endpoint):
    end = (observations + timedelta(minutes=10)).isoformat()
    response = app.test_client().get(endpoint, query_string={
        "start_time": end, "end_time": end,
    })
    assert response.status_code == 200
    assert response.get_json()["total_services"] == 1
    assert response.get_json()["average_delay"] == 10.0


def test_fractional_bounds_do_not_include_previous_second(observations, endpoint):
    response = app.test_client().get(endpoint, query_string={
        "start_time": (observations + timedelta(microseconds=100000)).isoformat(),
        "end_time": (observations + timedelta(microseconds=900000)).isoformat(),
    })
    assert response.status_code == 404


@pytest.mark.parametrize("bound,count", [("start_time", 4), ("end_time", 2)])
def test_one_sided_bounds(observations, endpoint, bound, count):
    response = app.test_client().get(endpoint, query_string={
        bound: observations.isoformat(),
    })
    assert response.status_code == 200
    assert response.get_json()["total_services"] == count


def test_no_filters_preserve_all_history_including_undated(observations, endpoint):
    response = app.test_client().get(endpoint)
    assert response.status_code == 200
    assert response.get_json()["total_services"] == 6


@pytest.mark.parametrize("bounds,error_field", [
    ({"start_time": "not-a-date"}, "start_time"),
    ({"end_time": "2026-99-99T00:00:00Z"}, "end_time"),
    ({"start_time": "2026-10-20T09:00:00"}, "start_time"),
    ({"end_time": "2026-10-20"}, "end_time"),
    ({"start_time": ""}, "start_time"),
    ({"end_time": ""}, "end_time"),
    # Lexical order looks valid, but the first actual instant is later.
    ({"start_time": "2026-10-20T09:00:00+09:30",
      "end_time": "2026-10-20T09:30:00+10:30"}, "start_time"),
])
def test_bad_bounds_rejected_before_query(monkeypatch, endpoint, bounds, error_field):
    def unexpected_query(**kwargs):
        pytest.fail("Invalid bounds must not reach the database/analysis")
    monkeypatch.setattr("backend.api.app.query_and_analyse", unexpected_query)
    response = app.test_client().get(endpoint, query_string=bounds)
    assert response.status_code == 400
    assert error_field in response.get_json()["error"]


def test_filtered_performance_matches_hotspot_metrics(observations):
    client = app.test_client()
    params = window(observations)
    # Same stop across routes; both use the same inclusive observation bounds.
    performance = client.get("/api/stops/S1/performance", query_string=params)
    hotspots = client.get("/api/analysis/hotspots", query_string={
        **params, "stop_id": "S1", "min_services": 1,
    })
    assert performance.status_code == hotspots.status_code == 200
    hotspot = hotspots.get_json()["hotspots"][0]
    for key, value in performance.get_json().items():
        assert hotspot[key] == value


def test_latest_prediction_is_selected_within_window(observations, endpoint):
    repository.insert_trip_update({
        "trip_id": "start", "route_id": "R1", "stop_id": "S1",
        "scheduled_arrival": (observations + timedelta(hours=2)).isoformat(),
        "delay_seconds": 1800,
        "timestamp": (observations + timedelta(hours=1)).isoformat(),
    })
    response = app.test_client().get(endpoint, query_string=window(observations))
    assert response.status_code == 200
    assert response.get_json()["total_services"] == 3
    assert response.get_json()["average_delay"] == (
        5.33 if "/routes/" in endpoint else 10.67
    )
