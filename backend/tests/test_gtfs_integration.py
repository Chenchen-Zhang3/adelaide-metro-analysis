"""SCRUM-268 integration regressions using synthetic GTFS and temporary SQLite.

The scope is exact identity handling; no producer sequence fallback is allowed.
"""

from contextlib import closing
import csv
from datetime import datetime
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock

from google.transit import gtfs_realtime_pb2
import pytest

from backend.database import connection as database
from backend.database.models import create_tables
from backend.parsers.static_gtfs import parse_routes, parse_stops, parse_trips, parse_stop_times
from backend.realtime.config import GTFSRealtimeCollectionSettings
from backend.realtime.pipeline import GTFSRealtimeProcessingPipeline
from backend.services.gtfs_converter import (
    build_stop_time_index, convert_route, convert_stop, convert_trip,
    convert_stop_time, convert_trip_update,
)
from backend.services.historical_collection import HistoricalCollectionRunner
from backend.services.pipeline import persist_collection_result


START = datetime.fromisoformat('2026-10-21T08:00:00+10:30')


def stop_time(trip='T', stop='S', sequence=10, arrival='08:00:00'):
    return {'trip_id': trip, 'stop_id': stop, 'stop_sequence': sequence,
            'arrival_time': arrival, 'departure_time': arrival}


def trip_entity(trip='T', route='BEL', stop='S', sequence=10, delay=60):
    entity = gtfs_realtime_pb2.FeedEntity(id=trip)
    update = entity.trip_update
    update.trip.trip_id = trip
    update.trip.route_id = route
    update.trip.start_date = '20261021'
    update.timestamp = int(START.timestamp())
    visit = update.stop_time_update.add()
    visit.stop_id = stop
    visit.stop_sequence = sequence
    visit.arrival.time = int(START.timestamp()) + delay
    return entity


@pytest.mark.parametrize('arrival,sequence', [
    ('09:00:00', 10),       # Conflicting schedule.
    ('08:00:00', 10),       # Identical duplicate is still a duplicate identity.
    ('09:00:00', '010'),    # Keys must be checked after sequence normalisation.
])
def test_duplicate_exact_keys_fail_instead_of_selecting_a_timetable(arrival, sequence):
    first = stop_time()
    second = stop_time(sequence=sequence, arrival=arrival)
    for records in ([first, second], [second, first]):
        with pytest.raises(ValueError, match='Duplicate static stop-time key'):
            build_stop_time_index(iter(records))


def test_duplicate_timetable_stops_initialisation_before_database_or_pipeline(tmp_path):
    path = tmp_path / 'stop_times.txt'
    path.write_text(
        'trip_id,stop_id,stop_sequence,arrival_time,departure_time\n'
        'T,S,10,08:00:00,08:00:00\nT,S,10,09:00:00,09:00:00\n',
        encoding='utf-8',
    )
    create_schema, pipeline_factory = Mock(), Mock()
    runner = HistoricalCollectionRunner(
        tmp_path, pipeline_factory=pipeline_factory,
        create_tables_function=create_schema,
    )
    with pytest.raises(ValueError, match='Duplicate static stop-time key'):
        runner.initialise()
    create_schema.assert_not_called()
    pipeline_factory.assert_not_called()
    assert runner.pipeline is None


def test_repeated_visits_and_terminal_keys_remain_distinct():
    index = build_stop_time_index([
        stop_time(sequence=1), stop_time(sequence=30, arrival='08:05:00'),
        stop_time(sequence=999, arrival='08:10:00'),
        stop_time(trip='OTHER', sequence=1),
    ])
    assert len(index) == 4
    for sequence, expected in [(1, 60), (30, -240), (999, -540)]:
        records = convert_trip_update(trip_entity(sequence=sequence), index)
        assert records[0]['delay_seconds'] == expected
    assert convert_trip_update(trip_entity(sequence=2), index) == []


@pytest.mark.parametrize('trip,stop,sequence', [
    ('UNKNOWN', 'S', 10), ('T', 'UNKNOWN', 10), ('T', 'S', 11),
    ('T', 'OTHER_TRIP_STOP', 20),
])
def test_missing_trip_stop_and_exact_visit_are_not_remapped(trip, stop, sequence):
    index = build_stop_time_index([stop_time(), stop_time(trip='OTHER', stop='OTHER_TRIP_STOP', sequence=20)])
    assert convert_trip_update(trip_entity(trip=trip, stop=stop, sequence=sequence), index) == []


def test_matching_a_key_does_not_validate_route_or_service_calendar():
    """Characterise the existing boundary; index has no trips/calendar metadata."""
    index = build_stop_time_index([stop_time()])
    item = trip_entity(route='UNVERIFIED_ROUTE')
    item.trip_update.trip.start_date = '20260901'
    records = convert_trip_update(item, index)
    assert records[0]['route_id'] == 'UNVERIFIED_ROUTE'
    assert records[0]['scheduled_arrival'].startswith('2026-09-01T08:00:00')


def write_csv(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_multiple_non_demo_routes_parse_convert_persist_and_query(tmp_path, monkeypatch):
    """Synthetic BEL/J1G/regional data, not evidence of live/historical coverage."""
    from backend.api.app import app

    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'integration.db')
    monkeypatch.setenv('ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS', '900')
    monkeypatch.setattr('backend.realtime.client.urlopen', Mock(side_effect=AssertionError('Live HTTP forbidden')))
    ids = [('001', 'BEL', 'S01', 2), ('002', 'J1G', 'S02', 3), ('003', 'REGIONAL', 'S03', 701)]
    routes = [{'route_id': route, 'route_short_name': route, 'route_long_name': 'Synthetic fixture', 'route_type': kind} for _, route, _, kind in ids]
    stops = [{'stop_id': stop, 'stop_name': 'Synthetic stop', 'stop_lat': -34.9, 'stop_lon': 138.6} for _, _, stop, _ in ids]
    trips = [{'trip_id': trip, 'route_id': route, 'service_id': 'synthetic-october'} for trip, route, _, _ in ids]
    times = [stop_time(trip=trip, stop=stop) for trip, _, stop, _ in ids]
    for name, data in [('routes', routes), ('stops', stops), ('trips', trips), ('stop_times', times)]:
        write_csv(tmp_path / (name + '.txt'), list(data[0]), data)
    parsed_routes = parse_routes(tmp_path / 'routes.txt')
    parsed_stops = parse_stops(tmp_path / 'stops.txt')
    parsed_trips = parse_trips(tmp_path / 'trips.txt')
    parsed_times = parse_stop_times(tmp_path / 'stop_times.txt')
    index = build_stop_time_index(parsed_times)
    create_tables()
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db, db:
        for table, data, convert, fields in [
            ('routes', parsed_routes, convert_route, ['route_id', 'route_short_name', 'route_long_name', 'route_type']),
            ('stops', parsed_stops, convert_stop, ['stop_id', 'stop_name', 'stop_lat', 'stop_lon']),
            ('trips', parsed_trips, convert_trip, ['trip_id', 'route_id', 'service_id', 'trip_headsign', 'direction_id']),
            ('stop_times', parsed_times, convert_stop_time, ['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence']),
        ]:
            db.executemany(
                f'INSERT INTO {table} ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})',
                ([convert(row).get(field) for field in fields] for row in data),
            )
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = '2.0'
    for trip, route, stop, _ in ids:
        feed.entity.add().CopyFrom(trip_entity(trip=trip, route=route, stop=stop))
    feed.entity.add().CopyFrom(trip_entity(trip='UNKNOWN'))
    missing_route = feed.entity.add()
    missing_route.CopyFrom(trip_entity(trip='001', stop='S01'))
    missing_route.trip_update.trip.ClearField('route_id')
    empty = gtfs_realtime_pb2.FeedMessage()
    empty.header.gtfs_realtime_version = '2.0'
    client = SimpleNamespace(
        settings=GTFSRealtimeCollectionSettings(),
        fetch_vehicle_positions=Mock(return_value=empty.SerializeToString()),
        fetch_trip_updates=Mock(return_value=feed.SerializeToString()),
    )
    records = GTFSRealtimeProcessingPipeline(client=client, stop_time_index=index).process_once()
    assert [(r['trip_id'], r['route_id'], r['stop_id']) for r in records['trip_updates']] == [x[:3] for x in ids]
    first, second = persist_collection_result(records), persist_collection_result(records)
    assert first['trip_updates_inserted'] == 3
    assert second['trip_updates_inserted'] == 0
    assert second['trip_updates_suppressed'] == 3
    api = app.test_client()
    assert {r['route_id'] for r in api.get('/api/routes').get_json()} == {x[1] for x in ids}
    assert len(api.get('/api/stops').get_json()) == 3
    for trip, route, stop, _ in ids:
        assert [r['route_id'] for r in api.get(f'/api/stops/{stop}/routes').get_json()] == [route]
        assert api.get(f'/api/routes/{route}/performance').status_code == 200
    assert api.get('/api/stops/UNKNOWN').status_code == 404
    assert api.get('/api/stops/UNKNOWN/routes').get_json() == []
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT COUNT(*) FROM trip_updates').fetchone()[0] == 3
        assert db.execute('SELECT COUNT(*) FROM collection_cycles').fetchone()[0] == 2
