"""Focused geometry/stop contract tests with small synthetic GTFS fixtures."""
from contextlib import closing
import csv
import json
from pathlib import Path
import sqlite3
import zipfile

import pytest
from jsonschema import Draft202012Validator, ValidationError

from backend.api.app import app
from backend.database import repository
from backend.database.models import create_tables
from backend.services import recorded_map_data as maps
from backend.services.gtfs_id_consistency import fingerprint
from backend.services.recorded_demo import LABEL, demo_database


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.realtime.client.urlopen', lambda *a,**k: pytest.fail('Live HTTP forbidden'))
    static = tmp_path/'static'
    static.mkdir()
    def write(name, fields, rows):
        with (static/name).open('w',encoding='utf-8-sig',newline='') as file:
            writer = csv.writer(file)
            writer.writerow(fields)
            writer.writerows(rows)
    route_rows = [['G10','G10','Fixture G10',3],['M44','M44','Fixture M44',3],['506','506','Fixture 506',3]]
    trip_rows = [['G10','W','001','S1',0],['G10','W','002','S2',1],['M44','W','003','S1',0],['506','W','004','S3',1]]
    stop_rows = [['001','First',-34.9,138.6],['002','Second',-34.8,138.7]]
    stop_times = [['001','09:00:00','09:00:00','001',1],['001','09:01:00','09:01:00','002',2],
                  ['001','09:02:00','09:02:00','001',3],['002','09:00:00','09:00:00','002',1],
                  ['003','09:00:00','09:00:00','001',1],['004','09:00:00','09:00:00','002',1]]
    write('routes.txt',['route_id','route_short_name','route_long_name','route_type'],route_rows)
    write('trips.txt',['route_id','service_id','trip_id','shape_id','direction_id'],trip_rows)
    write('stops.txt',['stop_id','stop_name','stop_lat','stop_lon'],stop_rows)
    write('stop_times.txt',['trip_id','arrival_time','departure_time','stop_id','stop_sequence'],stop_times)
    write('feed_info.txt',['feed_version','feed_start_date','feed_end_date'],[['1692','20260820','20261011']])
    write('shapes.txt',['shape_id','shape_pt_lat','shape_pt_lon','shape_pt_sequence'],[
        [shape,-34.8,138.7,10] for shape in ('S1','S2','S3')]+[
        [shape,-34.9,138.6,2] for shape in ('S1','S2','S3')]+[['irrelevant',999,999,'invalid']])
    archive = tmp_path/'feed.zip'
    with zipfile.ZipFile(archive,'w') as zipped:
        for path in sorted(static.iterdir()):
            zipped.write(path,path.name)
    demo = tmp_path/'demo.db'
    with demo_database(demo):
        create_tables()
        for route,short,long,type_ in route_rows:
            repository.insert_route({'route_id':route,'route_short_name':short,'route_long_name':long,'route_type':type_})
        for route,service,trip,shape,direction in trip_rows:
            repository.insert_trip({'route_id':route,'service_id':service,'trip_id':trip,'direction_id':direction})
        for stop,name,lat,lon in stop_rows:
            repository.insert_stop({'stop_id':stop,'stop_name':name,'stop_lat':lat,'stop_lon':lon})
        for trip,arrival,departure,stop,sequence in stop_times:
            repository.insert_stop_time({'trip_id':trip,'arrival_time':arrival,'departure_time':departure,'stop_id':stop,'stop_sequence':sequence})
        repository.persist_realtime_collection([], [
            {'trip_id':trip,'route_id':route,'stop_id':stop_times_for_trip[0][3],
             'scheduled_arrival':'2026-09-26T09:00:00+09:30','delay_seconds':60,'timestamp':'2026-09-26T09:01:00+09:30'}
            for route,service,trip,shape,direction in trip_rows
            for stop_times_for_trip in [[row for row in stop_times if row[0]==trip]]
        ])
    config = {'label':LABEL,'route_ids':['G10','M44','506'],'static_feed_version':'1692',
              'start':'2026-09-26T09:00:00+09:30','end_exclusive':'2026-09-26T11:00:00+09:30',
              'static_archive_sha256':fingerprint(archive)['sha256']}
    manifest = tmp_path/'demo.manifest.json'
    payload = {'label':LABEL,'config':config,'selected_trip_ids':['001','002','003','004'],
               'selected_stop_ids':['001','002'],'output_database':fingerprint(demo)}
    manifest.write_text(json.dumps(payload),encoding='utf8')
    return demo,manifest,static,archive,tmp_path/'map-data'


def schema():
    path = Path(__file__).resolve().parents[2]/'shared/schemas/recorded-route-map.schema.json'
    return json.loads(path.read_text(encoding='utf8'))


def test_official_geometry_order_variants_and_geojson_coordinate_order(inputs):
    before = fingerprint(inputs[0])['sha256']
    report = maps.build_map_data(*inputs)
    assert fingerprint(inputs[0])['sha256'] == before
    assert report['shape_count'] == 3 and report['feature_count'] == 4
    assert report['route_shapes']['G10'] == ['S1','S2']
    assert report['route_shapes']['M44'] == ['S1']
    data = maps.load_route_map_data('G10',inputs[-1])
    assert data['geometry']['features'][0]['properties']['shape_pt_sequences'] == [2,10]
    assert data['geometry']['features'][0]['geometry']['coordinates'] == [[138.6,-34.9],[138.7,-34.8]]
    assert len(data['geometry']['features']) == 2
    assert {trip['trip_id'] for trip in data['trips']} == {'001','002'}
    assert maps.load_route_map_data('M44',inputs[-1])['geometry']['features'][0]['properties']['trip_ids'] == ['003']
    Draft202012Validator(schema()).validate(data)


def test_stop_relationships_preserve_many_to_many_and_repeated_trip_visits(inputs):
    report = maps.build_map_data(*inputs)
    assert report['stop_count'] == 2
    g10 = maps.load_route_map_data('G10',inputs[-1])
    m44 = maps.load_route_map_data('M44',inputs[-1])
    route506 = maps.load_route_map_data('506',inputs[-1])
    assert {item['id'] for item in m44['stops']['features']} == {'001'}
    assert {item['id'] for item in route506['stops']['features']} == {'002'}
    shared = next(item for item in g10['stops']['features'] if item['id']=='001')
    assert shared['properties']['route_ids'] == ['G10','M44']
    assert next(trip for trip in g10['trips'] if trip['trip_id']=='001')['stops'] == [
        {'stop_id':'001','stop_sequence':1},{'stop_id':'002','stop_sequence':2},{'stop_id':'001','stop_sequence':3}]


def test_reproducible_outputs_and_no_overwrite(inputs):
    first = maps.build_map_data(*inputs)
    second = maps.build_map_data(*inputs[:-1],inputs[-1].with_name('repeat'))
    assert first['files'] == second['files']
    with pytest.raises(FileExistsError):
        maps.build_map_data(*inputs)


@pytest.mark.parametrize('shape,lat,lon,seq',[
    ('S1',91,138.6,3),('S1',-34.9,181,3),('S1','NaN',138.6,3),('S1',-34.9,138.6,-1),
])
def test_invalid_selected_shape_coordinate_or_sequence(inputs,shape,lat,lon,seq):
    path = inputs[2]/'shapes.txt'
    with path.open('a',encoding='utf8') as file:
        file.write(f'{shape},{lat},{lon},{seq}\n')
    with pytest.raises(ValueError):
        maps.extract_shapes(path,{'S1'})


def test_missing_shape_and_duplicate_sequence_fail_instead_of_fabricating(inputs):
    path = inputs[2]/'shapes.txt'
    with pytest.raises(ValueError,match='Missing'):
        maps.extract_shapes(path,{'missing'})
    with path.open('a',encoding='utf8') as file:
        file.write('S1,-34.7,138.8,2\n')
    with pytest.raises(ValueError,match='duplicated'):
        maps.extract_shapes(path,{'S1'})


def test_repeated_points_are_reported_and_preserved(inputs):
    path = inputs[2]/'shapes.txt'
    with path.open('a',encoding='utf8') as file:
        file.write('S1,-34.9,138.6,3\n')
    points,diagnostics = maps.extract_shapes(path,{'S1'})
    assert len(points['S1']['coordinates']) == 3
    assert diagnostics['S1']['adjacent_duplicate_count'] == 1


def test_changed_shapes_archive_or_demo_hash_rejected(inputs):
    with (inputs[2]/'shapes.txt').open('a',encoding='utf8') as file:
        file.write('\n')
    with pytest.raises(ValueError,match='shapes.txt differs'):
        maps.build_map_data(*inputs)
    with closing(sqlite3.connect(inputs[0])) as db:
        db.execute("UPDATE trips SET route_id='other' WHERE trip_id='001'")
        db.commit()
    with pytest.raises(ValueError,match='database hash'):
        maps.build_map_data(*inputs)
    assert not inputs[-1].exists()


def test_wrong_demo_stop_relationship_rejected(inputs):
    with closing(sqlite3.connect(inputs[0])) as db:
        db.execute("UPDATE stop_times SET stop_id='absent' WHERE trip_id='001'")
        db.commit()
    payload = json.loads(inputs[1].read_text(encoding='utf8'))
    payload['output_database'] = fingerprint(inputs[0])
    inputs[1].write_text(json.dumps(payload),encoding='utf8')
    with pytest.raises(ValueError,match='Orphan'):
        maps.build_map_data(*inputs)


def test_map_api_all_routes_404_and_existing_endpoints_unchanged(inputs,monkeypatch):
    maps.build_map_data(*inputs)
    monkeypatch.setenv(maps.MAP_DATA_ENV,str(inputs[-1]))
    with app.test_client() as client, demo_database(inputs[0]):
        for route in ('G10','M44','506'):
            response = client.get(f'/api/routes/{route}/map-data')
            assert response.status_code == 200
            Draft202012Validator(schema()).validate(response.get_json())
        assert client.get('/api/routes/unknown/map-data').status_code == 404
        assert len(client.get('/api/routes').get_json()) == 3
        assert len(client.get('/api/stops').get_json()) == 2
        assert {row['route_id'] for row in client.get('/api/stops/001/routes').get_json()} == {'G10','M44'}


def test_missing_or_corrupted_artifacts_return_503(inputs,monkeypatch):
    monkeypatch.delenv(maps.MAP_DATA_ENV,raising=False)
    with app.test_client() as client:
        assert client.get('/api/routes/G10/map-data').status_code == 503
    maps.build_map_data(*inputs)
    monkeypatch.setenv(maps.MAP_DATA_ENV,str(inputs[-1]))
    with (inputs[-1]/'route-shapes.geojson').open('a',encoding='utf8') as file:
        file.write('corrupted')
    with app.test_client() as client:
        response = client.get('/api/routes/G10/map-data')
        assert response.status_code == 503
        assert str(inputs[-1]) not in response.get_data(as_text=True)


def test_contract_rejects_geojson_axis_reversal(inputs):
    maps.build_map_data(*inputs)
    data = maps.load_route_map_data('G10',inputs[-1])
    data['geometry']['features'][0]['geometry']['coordinates'][0] = [-34.9,138.6]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(data)
