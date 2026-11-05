"""Bulk predictions: real temporary SQLite, API contracts and old-path parity."""
from datetime import datetime, timedelta, timezone

import pytest

from backend.api.app import app
from backend.database import connection, repository, stop_delays
from backend.database.models import create_tables
from backend.services import static_map_data

URL = "/api/analysis/stop-delays"


@pytest.fixture
def dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(connection, "DATABASE_PATH", tmp_path / "bulk.db")
    monkeypatch.delenv("ADELAIDE_METRO_STATIC_MAP_DATA_PATH", raising=False)
    create_tables()
    start = datetime.fromisoformat("2026-10-17T09:00:00+10:30")
    epoch = int(start.timestamp())
    # Same visit: before, start, revision inside, and revision outside window.
    rows = [
        ("rev", "R1", "001", epoch+7200, 1200, epoch-1),
        ("rev", "R1", "001", epoch+7200, 600, epoch),
        ("rev", "R1", "001", epoch+7200, 120, epoch+300),
        ("rev", "R1", "001", epoch+7200, 1800, epoch+601),
        ("early", "R1", "001", epoch+7200, -120, epoch),
        ("end", "R1", "001", epoch+7200, 300, epoch+600),
        ("other", "R2", "001", epoch+7200, 900, epoch+300),
        ("sparse", "R1", "002", epoch+7200, 660, epoch+300),
        ("unknown", "R1", "unknown", epoch+7200, 60, epoch+300),
        ("parent", "R1", "P", epoch+7200, 60, epoch+300),
        ("undated", "R1", "001", epoch+7200, 3600, None),
    ]
    db = connection.get_connection()
    db.executemany("""INSERT INTO trip_updates
        (trip_id,route_id,stop_id,scheduled_arrival,delay_seconds,observed_at,observation_kind)
        VALUES (?,?,?,?,?,?,1)""", rows)
    db.commit(); db.close()
    return {"start_time": start.isoformat(),
            "end_time": (start+timedelta(minutes=10)).isoformat(), "min_samples": "1"}


def request(params):
    return app.test_client().get(URL, query_string=params)


def by_stop(response):
    assert response.status_code == 200, response.get_json()
    return {r["stop_id"]: r for r in response.get_json()["stops"]}


def test_metrics_and_existing_single_stop_parity(dataset):
    result = by_stop(request(dataset))
    assert result["001"]["prediction_sample_count"] == 4
    assert result["001"]["average_predicted_delay_minutes"] == 5
    assert result["001"]["predicted_on_time_percentage"] == 50
    for stop, row in result.items():
        old = app.test_client().get(f"/api/stops/{stop}/performance",
                                   query_string={k:v for k,v in dataset.items() if k != "min_samples"}).get_json()
        assert row["prediction_sample_count"] == old["total_services"]
        assert row["average_predicted_delay_minutes"] == old["average_delay"]
        assert row["predicted_on_time_percentage"] == old["on_time_percentage"]


def test_route_isolation_and_early_value(dataset):
    rows = by_stop(request({**dataset,"route_id":"R1"}))
    assert rows["001"]["prediction_sample_count"] == 3
    assert rows["001"]["average_predicted_delay_minutes"] == 1.67
    assert rows["001"]["predicted_on_time_percentage"] == 66.67


def test_insufficient_retains_count_but_nulls_metrics(dataset):
    row = by_stop(request({**dataset,"min_samples":"5"}))["001"]
    assert row["data_status"] == "insufficient_data"
    assert row["prediction_sample_count"] == 4
    assert row["average_predicted_delay_minutes"] is None
    assert row["predicted_on_time_percentage"] is None


@pytest.mark.parametrize("offset", ["+09:30", "+10:30", "+00:00"])
def test_offsets_are_equivalent_instants(dataset, offset):
    tz = datetime.fromisoformat("2026-01-01T00:00:00"+offset).tzinfo
    transformed = {**dataset, **{k:datetime.fromisoformat(dataset[k]).astimezone(tz).isoformat()
                                for k in ("start_time","end_time")}}
    assert request(transformed).get_json() == request(dataset).get_json()


def test_equal_inclusive_bounds_and_fractional_bounds(dataset):
    rows = by_stop(request({**dataset,"end_time":dataset["start_time"]}))
    assert rows["001"]["prediction_sample_count"] == 2
    fractional = datetime.fromisoformat(dataset["start_time"])+timedelta(microseconds=1)
    rows = by_stop(request({**dataset,"start_time":fractional.isoformat()}))
    assert rows["001"]["prediction_sample_count"] == 3


def test_future_empty_is_explicit_no_data(dataset):
    response = request({**dataset,"start_time":"2030-01-01T00:00:00Z","end_time":"2030-01-01T00:15:00Z"})
    assert by_stop(response) == {}
    body = response.get_json()
    assert "no_data" in body["missing_stop_policy"]
    assert body["coverage"]["prediction_sample_count"] == 0
    assert body["coverage"]["no_data_stop_count"] is None


@pytest.mark.parametrize("params", [
    {}, {"start_time":""}, {"end_time":"bad"},
    {"start_time":"2026-10-17T09:00:00"},
    {"end_time":"2026-10-17T08:00:00+10:30"},
    {"end_time":"2026-10-17T10:00:01+10:30"},
    {"min_samples":"0"}, {"min_samples":"-1"}, {"min_samples":"1.5"},
    {"min_samples":"abc"}, {"min_samples":"100001"},
    {"scope":"wrong"}, {"route_id":""}, {"route_id":"x"*129},
    {"start":"2026-10-17"},
])
def test_invalid_requests_do_not_query(dataset, params, monkeypatch):
    def forbidden(*a,**k):raise AssertionError("must not query")
    monkeypatch.setattr(repository,"get_connection",forbidden)
    actual = {**dataset, **params} if params else {}
    assert request(actual).status_code == 400


def test_duplicate_parameters_rejected(dataset):
    assert request(list(dataset.items())+[("min_samples","2")]).status_code == 400


@pytest.fixture
def catalog(monkeypatch):
    monkeypatch.setattr(static_map_data,"_manifest",lambda _: (None,{
        "static_feed_version":"1710", "feed_info":{"feed_start_date":"20261016","feed_end_date":"20270409"}}))
    monkeypatch.setattr(static_map_data,"load_catalog",lambda: {
        "routes":[{"route_id":"R1"},{"route_id":"R2"}],
        "stops":[{"stop_id":s,"location_type":"0","route_ids":["R1"]} for s in ("001","002","003")]
                +[{"stop_id":"P","location_type":"1","route_ids":["R1"]}]})


def test_static_matching_no_rollup_or_completeness_claim(dataset,catalog):
    response=request({**dataset,"scope":"static","min_samples":"3"})
    assert set(by_stop(response)) == {"001","002"}
    data=response.get_json()
    assert data["excluded_observed_stop_ids"] == ["P","unknown"]
    assert data["static_catalog"]["eligible_stop_count"] == 3
    assert data["coverage"]["no_data_stop_count"] == 1
    assert "percentage" not in str(data["coverage"])
    assert data["static_catalog"]["parent_station_rollup"] is False


@pytest.mark.parametrize("params",[
    {"start_time":"2026-10-15T09:00:00+10:30","end_time":"2026-10-15T09:15:00+10:30"},
    {"start_time":"2027-04-10T09:00:00+09:30","end_time":"2027-04-10T09:15:00+09:30"},
    {"route_id":"missing"},
])
def test_static_invalid_date_or_route(dataset,catalog,params):
    assert request({**dataset,"scope":"static",**params}).status_code == 400


def test_unconfigured_static_is_503(dataset):
    assert request({**dataset,"scope":"static"}).status_code == 503


def test_row_guard_before_aggregation_including_other_routes(dataset,monkeypatch):
    monkeypatch.setattr(stop_delays,"MAX_ROWS",2)
    response=request({**dataset,"route_id":"missing"})
    assert response.status_code == 422
    assert response.get_json()["code"] == "analysis_limit_exceeded"


def test_query_plan_uses_time_index_and_constant_query_count(dataset,monkeypatch):
    real=repository.get_connection; statements=[]
    def traced():
        db=real();db.set_trace_callback(statements.append);return db
    monkeypatch.setattr(repository,"get_connection",traced)
    assert request(dataset).status_code == 200
    queries=[s for s in statements if s.strip().upper().startswith(("SELECT","WITH"))]
    assert len(queries)==2
    db=real()
    db.create_function("is_on_time",1,lambda _: 1)
    for sql in queries:
        plans=[row[3] for row in db.execute("EXPLAIN QUERY PLAN "+sql)]
        assert any("SEARCH trip_updates USING INDEX idx_trip_updates_observed" in p or
                   "SEARCH trip_updates USING COVERING INDEX idx_trip_updates_observed" in p for p in plans)
    db.close()


def test_latest_tie_uses_id_and_negative_average(dataset):
    db=connection.get_connection();epoch=int(datetime.fromisoformat(dataset["start_time"]).timestamp())
    for delay in (60,-60):
        db.execute("INSERT INTO trip_updates(trip_id,route_id,stop_id,scheduled_arrival,delay_seconds,observed_at,observation_kind) VALUES ('tie','R1','tie',?,?,?,1)",(epoch,delay,epoch))
    db.commit();db.close()
    row=by_stop(request(dataset))["tie"]
    assert row["prediction_sample_count"]==1
    assert row["average_predicted_delay_minutes"]==-1
    assert row["predicted_on_time_percentage"]==0


def test_deadline_aborts_without_partial_response(dataset,monkeypatch):
    monkeypatch.setattr(stop_delays,"QUERY_SECONDS",-1)
    db=connection.get_connection();epoch=int(datetime.fromisoformat(dataset["start_time"]).timestamp())
    db.executemany("INSERT INTO trip_updates(trip_id,route_id,stop_id,scheduled_arrival,delay_seconds,observed_at,observation_kind) VALUES (?,'R','S',?,0,?,1)",[(str(i),epoch,epoch) for i in range(1000)])
    db.commit();db.close()
    assert request(dataset).status_code==422


@pytest.mark.parametrize("seconds,percentage",[(-1,0),(0,100),(300,100),(301,0),(600,0),(601,0)])
def test_existing_classification_boundaries(dataset,seconds,percentage):
    db=connection.get_connection();epoch=int(datetime.fromisoformat(dataset["start_time"]).timestamp())
    db.execute("INSERT INTO trip_updates(trip_id,route_id,stop_id,scheduled_arrival,delay_seconds,observed_at,observation_kind) VALUES ('boundary','R','boundary',?,?,?,1)",(epoch,seconds,epoch))
    db.commit();db.close()
    row=by_stop(request(dataset))["boundary"]
    assert row["predicted_on_time_percentage"]==percentage
    assert row["average_predicted_delay_minutes"]==round(seconds/60,2)


def test_real_september_window(dataset):
    old=datetime.fromisoformat(dataset["start_time"])
    new=datetime.fromisoformat("2026-09-26T09:00:00+09:30")
    delta=int((new-old).total_seconds())
    db=connection.get_connection()
    db.execute("UPDATE trip_updates SET observed_at=observed_at+?, scheduled_arrival=scheduled_arrival+?",(delta,delta))
    db.commit();db.close()
    rows=by_stop(request({**dataset,"start_time":new.isoformat(),"end_time":(new+timedelta(minutes=10)).isoformat()}))
    assert rows["001"]["prediction_sample_count"]==4
    assert rows["001"]["average_predicted_delay_minutes"]==5


def test_distinct_scheduled_visits_are_not_combined(dataset):
    db=connection.get_connection();epoch=int(datetime.fromisoformat(dataset["start_time"]).timestamp())
    for arrival in (epoch+3600,epoch+7200):
        db.execute("INSERT INTO trip_updates(trip_id,route_id,stop_id,scheduled_arrival,delay_seconds,observed_at,observation_kind) VALUES ('loop','R','loop',?,60,?,1)",(arrival,epoch))
    db.commit();db.close()
    assert by_stop(request(dataset))["loop"]["prediction_sample_count"]==2
