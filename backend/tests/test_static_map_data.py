"""Static publishing uses temporary ZIPs; no live feed or production database."""
import json
from pathlib import Path
import zipfile

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from backend.api.app import app
from backend.database.models import create_tables
from backend.services import static_map_data as maps
from backend.services.gtfs_id_consistency import fingerprint
from backend.services.recorded_demo import demo_database
from backend.tests.test_recorded_map_data import inputs  # Reuse demo fixture and regression contract.


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.delenv(maps.MAP_DATA_ENV, raising=False)
    monkeypatch.delenv("ADELAIDE_METRO_DEMO_MAP_DATA_PATH", raising=False)
    files = {
        "agency.txt": "agency_id,agency_name\n5,Metro\n9,Regional\n",
        "feed_info.txt": "feed_version,feed_start_date,feed_end_date\nfixture,20261016,20270409\n",
        "routes.txt": "route_id,agency_id,route_short_name,route_long_name,route_type\n001,5,1,First,3\n002,5,2,Second,3\nS,5,S,School,712\nR,9,R,Regional,3\n",
        "trips.txt": "trip_id,route_id,service_id,shape_id,direction_id\nt1,001,W,s1,0\nt2,001,W,s2,1\nt3,002,W,s1,0\n",
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n001,Platform,-34.9,138.6,0,P\n002,Stop,-34.8,138.7,0,\nP,Station,-34.9,138.6,1,\n",
        "stop_times.txt": "trip_id,stop_id,stop_sequence,arrival_time,departure_time\nt1,001,1,09:00:00,09:00:00\nt1,002,3,09:01:00,09:01:00\nt1,001,5,09:02:00,09:02:00\nt2,002,1,09:00:00,09:00:00\nt3,001,1,09:00:00,09:00:00\n",
        "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\ns1,-34.9,138.6,2\ns1,-34.8,138.7,10\ns2,-34.8,138.7,1\ns2,-34.9,138.6,3\n",
        "calendar.txt": "service_id,monday\nW,1\n",
        "calendar_dates.txt": "service_id,date,exception_type\nW,20261020,1\n",
    }
    return files, tmp_path


def publish(source, name="published", **options):
    files, folder = source
    archive = folder / (name + ".zip")
    with zipfile.ZipFile(archive, "w") as z:
        for filename, content in sorted(files.items()):
            z.writestr(filename, content)
    output = folder / name
    kwargs = dict(expected_sha256=fingerprint(archive)["sha256"], version="fixture", agency_ids=["5"])
    kwargs.update(options)
    manifest = maps.build_static_map_data(archive, output, **kwargs)
    return output, manifest


def validator():
    directory = Path(__file__).resolve().parents[2] / "shared/schemas"
    recorded = json.loads((directory / "recorded-route-map.schema.json").read_text(encoding="utf8"))
    registry = Registry().with_resource("recorded-route-map.schema.json", Resource.from_contents(recorded))
    return Draft202012Validator(json.loads((directory / "static-route-map.schema.json").read_text()), registry=registry)


def test_relationships_variants_parent_station_and_schema(source):
    folder, manifest = publish(source)
    assert manifest["counts"] == dict(routes=2, stops=3, referenced_stops=2, parent_stations=1,
                                    trips=3, stop_times=5, shapes=2, route_shape_variants=3, shape_points=4)
    first = maps.load_static_route_map_data("001", folder)
    validator().validate(first)
    assert first["historical_data_status"] == "not_included"
    assert first["observation_window"] is None
    assert {f["properties"]["shape_id"] for f in first["geometry"]["features"]} == {"s1", "s2"}
    assert [s["stop_sequence"] for s in first["trips"][0]["stops"]] == [1, 3, 5]
    parent = next(s for s in maps.load_catalog(folder)["stops"] if s["stop_id"] == "P")
    assert parent["location_type"] == 1 and parent["route_ids"] == ["001", "002"]
    second = maps.load_static_route_map_data("002", folder)
    assert {f["id"] for f in second["stops"]["features"]} == {"001", "P"}
    assert second["geometry"]["features"][0]["properties"]["trip_ids"] == ["t3"]


def test_determinism_provenance_no_overwrite(source):
    folder, first = publish(source)
    _, second = publish(source, "repeat")
    assert first["route_files"] == second["route_files"]
    assert first["catalog"] == second["catalog"]
    assert first["source_files"] == second["source_files"]
    assert first["selection"]["route_ids"] == ["001", "002"]
    with pytest.raises(FileExistsError):
        maps.build_static_map_data(source[1]/"published.zip", folder, expected_sha256="wrong", version="fixture", agency_ids=["5"])


@pytest.mark.parametrize("kwargs", [dict(expected_sha256="wrong"), dict(version="wrong"),
    dict(agency_ids=["absent"]), dict(route_ids=["S"]), dict(route_types=[]), dict(agency_ids=[])])
def test_invalid_provenance_or_policy(source, kwargs):
    with pytest.raises(ValueError):
        publish(source, **kwargs)
    assert not (source[1]/"published").exists()


@pytest.mark.parametrize("filename,old,new", [
    ("stop_times.txt", "t3,001,1", "t3,missing,1"),
    ("stop_times.txt", "t1,002,3", "t1,002,1"),
    ("stop_times.txt", "t1,002,3", "absent,002,3"),
    ("stops.txt", "0,P", "0,absent"),
    ("stops.txt", "-34.9", "NaN"),
    ("trips.txt", "t3,002,W", "t3,absent,W"),
    ("trips.txt", "t3,002,W", "t3,002,absent"),
    ("trips.txt", "W,s2,1", "W,,1"),
    ("shapes.txt", "s2,-34.9", "absent,-34.9"),
    ("shapes.txt", "138.6,3", "181,3"),
    ("routes.txt", "002,5", "001,5"),
])
def test_invalid_selected_relationships_fail_atomically(source, filename, old, new):
    source[0][filename] = source[0][filename].replace(old, new)
    with pytest.raises(ValueError):
        publish(source)
    assert not (source[1]/"published").exists()


def test_api_static_dimensions_geometry_and_empty_history(source, monkeypatch):
    folder, _ = publish(source)
    monkeypatch.setenv(maps.MAP_DATA_ENV, str(folder))
    with demo_database(source[1]/"empty.db"):
        create_tables()
        with app.test_client() as client:
            assert len(client.get("/api/routes").get_json()) == 2
            assert len(client.get("/api/stops").get_json()) == 3
            assert client.get("/api/stops/001").get_json()["parent_station"] == "P"
            assert len(client.get("/api/stops/001/routes").get_json()) == 2
            assert client.get("/api/stops/absent").status_code == 404
            assert client.get("/api/stops/absent/routes").get_json() == []
            for route in ("001", "002"):
                response = client.get(f"/api/routes/{route}/map-data")
                assert response.status_code == 200
                validator().validate(response.get_json())
                assert client.get(f"/api/routes/{route}/performance").status_code == 404
            assert client.get("/api/stops/001/performance").status_code == 404
            assert client.get("/api/routes/absent/map-data").status_code == 404
            assert client.get("/api/routes/001/map-data?source=bad").status_code == 400


def test_missing_corrupt_artifacts_fail_closed(source, monkeypatch):
    folder, manifest = publish(source)
    monkeypatch.setenv(maps.MAP_DATA_ENV, str(folder))
    path = folder/"routes"/manifest["route_files"]["001"]["name"]
    path.write_text("corrupt")
    with app.test_client() as client:
        assert client.get("/api/routes/001/map-data").status_code == 503
        assert client.get("/api/routes/002/map-data").status_code == 200
        (folder/"catalog.json").unlink()
        assert client.get("/api/routes").status_code == 503


def test_demo_precedence_and_explicit_static_source(source, inputs, monkeypatch):
    from backend.services import recorded_map_data as demo
    demo.build_map_data(*inputs)
    # Publish a same-ID static route as well as the other non-demo route.
    for key in ("routes.txt", "trips.txt"):
        source[0][key] = source[0][key].replace("001", "G10")
    folder, _ = publish(source)
    monkeypatch.setenv(maps.MAP_DATA_ENV, str(folder))
    monkeypatch.setenv(demo.MAP_DATA_ENV, str(inputs[-1]))
    with app.test_client() as client:
        for route in ("G10", "M44", "506"):
            assert client.get(f"/api/routes/{route}/map-data").get_json() == demo.load_route_map_data(route, inputs[-1])
        assert client.get("/api/routes/G10/map-data?source=static").get_json()["label"] == maps.LABEL
        assert client.get("/api/routes/002/map-data").status_code == 200
        assert client.get("/api/routes/002/map-data?source=recorded").status_code == 404
        (inputs[-1]/"route-shapes.geojson").write_text("corrupt")
        assert client.get("/api/routes/G10/map-data").status_code == 503


def test_route_request_does_not_read_other_routes_or_source_gtfs(source, monkeypatch):
    folder, manifest = publish(source)
    other = folder/"routes"/manifest["route_files"]["002"]["name"]
    other.unlink()
    (folder/"catalog.json").unlink()
    (source[1]/"published.zip").unlink()
    monkeypatch.setattr(maps, "extract_shapes", lambda *a: pytest.fail("Request parsed GTFS"))
    assert maps.load_static_route_map_data("001", folder)["route_id"] == "001"
    assert maps.load_static_route_map_data("../absent", folder) is None


def test_explicit_static_source_requires_configuration(source):
    with app.test_client() as client:
        response = client.get("/api/routes/001/map-data?source=static")
        assert response.status_code == 503
        assert "Static" in response.get_json()["error"]
