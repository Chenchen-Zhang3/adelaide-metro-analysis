"""Recorded demo preparation tests use synthetic fixtures, never client data."""
from contextlib import closing
import csv
from datetime import datetime, timedelta
import json
import sqlite3
import zipfile

import pytest

from backend.database import connection as database
from backend.database import repository
from backend.services import recorded_demo as demo
from backend.services.gtfs_id_consistency import fingerprint


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.realtime.client.urlopen', lambda *a,**k: pytest.fail('Live HTTP forbidden'))
    static = tmp_path / 'static'
    static.mkdir()
    def write(name, fields, rows):
        with (static / name).open('w',encoding='utf-8-sig',newline='') as file:
            writer = csv.writer(file)
            writer.writerow(fields)
            writer.writerows(rows)
    write('routes.txt',['route_id','route_short_name','route_long_name','route_type'],[['001A','1A','Fixture route',3]])
    write('trips.txt',['route_id','service_id','trip_id','shape_id'],[['001A','W','0007','shape-fixture']])
    write('stops.txt',['stop_id','stop_name','stop_lat','stop_lon'],[['0009','Fixture stop',-34.9,138.6]])
    write('stop_times.txt',['trip_id','arrival_time','departure_time','stop_id','stop_sequence'],[['0007','09:00:00','09:00:00','0009',1]])
    write('feed_info.txt',['feed_version','feed_start_date','feed_end_date'],[['1692','20260820','20261011']])
    archive = tmp_path / 'static.zip'
    with zipfile.ZipFile(archive,'w') as zipped:
        for path in sorted(static.iterdir()):
            zipped.write(path,path.name)
    source = tmp_path / 'legacy.db'
    with closing(sqlite3.connect(source)) as db:
        db.executescript('''
        CREATE TABLE vehicle_positions(id INTEGER PRIMARY KEY, vehicle_id TEXT, trip_id TEXT,route_id TEXT,latitude REAL,longitude REAL,timestamp TEXT);
        CREATE TABLE trip_updates(id INTEGER PRIMARY KEY,trip_id TEXT,route_id TEXT,stop_id TEXT,scheduled_arrival TEXT,actual_arrival TEXT,delay_seconds INTEGER,timestamp TEXT);
        CREATE INDEX vehicle_time ON vehicle_positions(timestamp);
        CREATE INDEX trip_time ON trip_updates(timestamp);
        ''')
        base = datetime.fromisoformat('2026-09-26T09:00:00+09:30')
        for minute, delay in [(0,60),(1,60),(15,60),(16,120),(17,120),(120,180)]:
            timestamp = (base+timedelta(minutes=minute)).isoformat()
            db.execute('INSERT INTO vehicle_positions(vehicle_id,trip_id,route_id,latitude,longitude,timestamp) VALUES (?,?,?,?,?,?)',('V','0007','001A',-34.9,138.6,timestamp))
            db.execute('INSERT INTO trip_updates(trip_id,route_id,stop_id,scheduled_arrival,actual_arrival,delay_seconds,timestamp) VALUES (?,?,?,?,?,?,?)',('0007','001A','0009',base.isoformat(),(base+timedelta(seconds=delay)).isoformat(),delay,timestamp))
        db.commit()
    config = {'label':demo.LABEL,'route_ids':['001A'],'start':'2026-09-26T09:00:00+09:30',
              'end_exclusive':'2026-09-26T11:00:00+09:30','static_feed_version':'1692',
              'static_archive_sha256':fingerprint(archive)['sha256'],'checkpoint_seconds':900}
    return source,static,tmp_path/'demo.db',config,archive


def generate(inputs):
    return demo.generate_demo(*inputs)


def test_reproducible_v2_extract_and_existing_queries(inputs):
    source,static,output,config,archive = inputs
    source_hash = fingerprint(source)['sha256']
    original_path = database.DATABASE_PATH
    first = generate(inputs)
    second_output = output.with_name('repeat.db')
    second = demo.generate_demo(source,static,second_output,config,archive)
    assert first['output_database']['sha256'] == second['output_database']['sha256']
    assert fingerprint(source)['sha256'] == source_hash
    assert database.DATABASE_PATH == original_path
    assert first['source_selected_counts'] == {'vehicle_positions':5,'trip_updates':5,'trip_updates_suppressed':2,'import_transactions':5}
    assert first['output_counts'] == {'routes':1,'trips':1,'stops':1,'stop_times':1,'vehicle_positions':5,'trip_updates':3,'trip_update_current_state':1,'collection_cycles':5}
    assert first['selected_trip_ids'] == ['0007'] and first['selected_stop_ids'] == ['0009']
    assert first['route_profiles']['001A']['shape_ids'] == ['shape-fixture']
    assert all(status == 200 for status in first['validation']['001A']['api_statuses'].values())
    assert output.with_suffix('.manifest.json').is_file()
    with demo.demo_database(output):
        rows = repository.get_trip_updates('001A')
        assert [row['observation_kind'] for row in rows] == ['initial','checkpoint','change']
        assert rows[0]['timestamp'] == config['start']
        assert all(row['timestamp'] < config['end_exclusive'] for row in rows)
        assert repository.get_trip_updates_filtered(start_time=config['end_exclusive']) == []
        assert repository.get_trip_updates('missing-route') == []
    with closing(sqlite3.connect(output)) as db:
        assert db.execute("SELECT value FROM schema_metadata WHERE name='historical_storage_version'").fetchone()[0] == '2'
        assert 'NOT original CASR' in db.execute("SELECT value FROM schema_metadata WHERE name='ledger_provenance'").fetchone()[0]
        times = [row[0] for row in db.execute('SELECT observed_at FROM collection_cycles ORDER BY id')]
        assert times[0] == int(datetime.fromisoformat(config['start']).timestamp())


@pytest.mark.parametrize('column,value,error', [
    ('actual_arrival','2026-09-26T10:00:00+09:30','arrival/delay'),
    ('stop_id','missing','trip/stop'),
])
def test_invalid_source_fails_without_publishing_or_leaking_database_path(inputs,column,value,error):
    source,static,output,config,archive = inputs
    with closing(sqlite3.connect(source)) as db:
        db.execute(f'UPDATE trip_updates SET {column}=? WHERE id=1',(value,))
        db.commit()
    previous = database.DATABASE_PATH
    with pytest.raises(ValueError,match=error):
        generate(inputs)
    assert database.DATABASE_PATH == previous
    assert not output.exists() and not output.with_suffix('.manifest.json').exists()


def test_invalid_vehicle_coordinates_rejected(inputs):
    source,static,output,config,archive = inputs
    with closing(sqlite3.connect(source)) as db:
        db.execute('UPDATE vehicle_positions SET latitude=91 WHERE id=1')
        db.commit()
    with pytest.raises(ValueError,match='coordinates'):
        generate(inputs)
    assert not output.exists()


def test_missing_vehicle_update_overlap_is_clear_error(inputs):
    source,static,output,config,archive = inputs
    with closing(sqlite3.connect(source)) as db:
        db.execute('DELETE FROM vehicle_positions')
        db.commit()
    with pytest.raises(ValueError,match='overlapping'):
        generate(inputs)
    assert not output.exists()


def test_unknown_route_rejected(inputs):
    source,static,output,config,archive = inputs
    config['route_ids'] = ['unknown']
    with pytest.raises(ValueError,match='route missing'):
        generate(inputs)


def test_static_version_or_archive_mismatch_rejected(inputs):
    source,static,output,config,archive = inputs
    config['static_feed_version'] = '9999'
    with pytest.raises(ValueError,match='version'):
        generate(inputs)
    config['static_feed_version'] = '1692'
    config['static_archive_sha256'] = 'wrong'
    with pytest.raises(ValueError,match='SHA-256'):
        generate(inputs)


def test_edited_static_files_rejected(inputs):
    source,static,output,config,archive = inputs
    with (static/'trips.txt').open('a',encoding='utf8') as file:
        file.write('\n')
    with pytest.raises(ValueError,match='differs from archive'):
        generate(inputs)


def test_missing_static_file_rejected(inputs):
    source,static,output,config,archive = inputs
    (static/'stops.txt').unlink()
    with pytest.raises(FileNotFoundError):
        generate(inputs)
    assert not output.exists()


def test_source_and_existing_output_never_overwritten(inputs):
    source,static,output,config,archive = inputs
    with pytest.raises(FileExistsError):
        demo.generate_demo(source,static,source,config,archive)
    output.write_bytes(b'keep existing')
    with pytest.raises(FileExistsError):
        generate(inputs)
    assert output.read_bytes() == b'keep existing'


@pytest.mark.parametrize('start,end',[
    ('2026-09-26T09:00:00','2026-09-26T11:00:00'),
    ('2026-09-26T11:00:00+09:30','2026-09-26T09:00:00+09:30'),
    ('2026-09-26T09:00:00+00:00','2026-09-26T11:00:00+00:00'),
    ('2026-10-20T09:00:00+10:30','2026-10-20T11:00:00+10:30'),
])
def test_invalid_observation_windows_rejected(inputs,start,end):
    source,static,output,config,archive = inputs
    config.update(start=start,end_exclusive=end)
    with pytest.raises(ValueError):
        generate(inputs)
    assert not output.exists()
