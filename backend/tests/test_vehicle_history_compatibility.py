"""CASR empty-dimension playback regression, using immutable synthetic SQLite."""
import hashlib
import sqlite3
from datetime import datetime

import pytest

from backend.api.app import app
from backend.database import connection, repository
from backend.database.models import create_tables
from backend.services import vehicle_history, static_map_data


@pytest.fixture
def history(tmp_path, monkeypatch):
    path = tmp_path / 'history.db'
    monkeypatch.setattr(connection, 'DATABASE_PATH', path)
    monkeypatch.delenv('ADELAIDE_METRO_STATIC_MAP_DATA_PATH', raising=False)
    create_tables()
    for route in ['100', 'J1', 'G10', 'M44', '506']:
        month, offset = ('09', '+09:30') if route in ['G10', 'M44', '506'] else ('10', '+10:30')
        for minute in ['00', '05', '15']:
            repository.insert_vehicle_position(dict(vehicle_id='001', trip_id='007', route_id=route,
                latitude=-34.9, longitude=138.6, timestamp=f'2026-{month}-17T09:{minute}:00{offset}'))
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    def readonly():
        db = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        return db
    monkeypatch.setattr(vehicle_history, 'get_connection', readonly)
    yield app.test_client(), path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert not list(tmp_path.glob('*-wal'))


def query(client, route='100', **changes):
    args = dict(start_time='2026-10-17T09:00:00+10:30', end_time='2026-10-17T09:15:00+10:30')
    args.update(changes)
    return client.get(f'/api/routes/{route}/vehicle-positions', query_string=args)


@pytest.mark.parametrize('route', ['100', 'J1', 'G10', 'M44', '506'])
def test_empty_dimensions_history_and_offsets(history, route):
    client, path = history
    month, offset = ('09', '+09:30') if route in ['G10', 'M44', '506'] else ('10', '+10:30')
    response = query(client, route, start_time=f'2026-{month}-17T09:00:00{offset}',
                     end_time=f'2026-{month}-17T09:15:00{offset}')
    assert response.status_code == 200
    rows = response.json['positions']
    assert len(rows) == 2  # End is exclusive.
    assert {r['route_id'] for r in rows} == {route}
    assert all((r['latitude'], r['longitude'], r['vehicle_id']) == (-34.9, 138.6, '001') for r in rows)
    assert [datetime.fromisoformat(r['timestamp']) for r in rows] == sorted(datetime.fromisoformat(r['timestamp']) for r in rows)
    assert response.json['next_offset'] is None
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        for table in ['routes', 'stops', 'trips', 'stop_times']:
            assert db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0


def test_utc_pagination_empty_unknown(history):
    client, _ = history
    assert query(client).json['positions'] == query(client, start_time='2026-10-16T22:30:00Z', end_time='2026-10-16T22:45:00Z').json['positions']
    first = query(client, limit=1).json
    second = query(client, limit=1, offset=first['next_offset']).json
    assert first['positions'][0]['id'] != second['positions'][0]['id']
    assert second['next_offset'] is None
    assert query(client, start_time='2030-01-01T00:00:00Z', end_time='2030-01-01T01:00:00Z').json['positions'] == []
    assert query(client, 'UNKNOWN').status_code == 404


def test_static_known_empty_and_unknown(history, monkeypatch):
    client, _ = history
    monkeypatch.setenv('ADELAIDE_METRO_STATIC_MAP_DATA_PATH', 'fixture')
    monkeypatch.setattr(static_map_data, 'load_catalog', lambda: {'routes': [{'route_id': 'CATALOG'}]})
    assert query(client, 'CATALOG').json['positions'] == []
    assert query(client, 'UNKNOWN').status_code == 404


def test_invalid_catalog_only_blocks_unresolved_identity(history, monkeypatch):
    client, _ = history
    monkeypatch.setenv('ADELAIDE_METRO_STATIC_MAP_DATA_PATH', 'does-not-exist')
    assert query(client).status_code == 200
    assert query(client, 'UNKNOWN').status_code == 503


@pytest.mark.parametrize('changes', [{'start_time':'bad'}, {'start_time':'2026-10-17T09:00:00'},
    {'end_time':'2026-10-17T08:00:00+10:30'}, {'limit':'0'}, {'offset':'-1'}, {'source':'static'}])
def test_invalid_requests(history, changes):
    assert query(history[0], **changes).status_code == 400
