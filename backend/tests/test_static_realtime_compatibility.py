"""Characterise exact matching and replay the safe subset through SQLite v2.

No new fallback is introduced: conflicting sequence/stop identities stay out.
"""

from contextlib import closing
from datetime import datetime
import importlib.util
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock

from google.transit import gtfs_realtime_pb2
import pytest

from backend.database import connection as database
from backend.database.models import create_tables
from backend.database.repository import persist_realtime_collection
from backend.realtime.config import GTFSRealtimeCollectionSettings
from backend.realtime.pipeline import GTFSRealtimeProcessingPipeline
from backend.services.gtfs_converter import build_stop_time_index, convert_trip_update


START = datetime.fromisoformat('2026-10-21T23:00:00+10:30')


def row(stop, sequence, arrival='23:00:00', trip='T'):
    return {'trip_id':trip, 'stop_id':stop, 'stop_sequence':sequence,
            'arrival_time':arrival, 'departure_time':arrival}


def entity(updates):
    item = gtfs_realtime_pb2.FeedEntity(id='synthetic-trip')
    item.trip_update.trip.trip_id = 'T'
    item.trip_update.trip.route_id = 'R'
    item.trip_update.trip.start_date = '20261021'
    item.trip_update.timestamp = int(START.timestamp())
    for stop_id, sequence, time in updates:
        update = item.trip_update.stop_time_update.add()
        update.stop_id = stop_id
        update.stop_sequence = sequence
        if time is not None:
            update.arrival.time = time
    return item


@pytest.mark.parametrize('sequence', [1, 10, 30, 999])
def test_exact_nonconsecutive_sequence_is_not_array_index(sequence):
    index = build_stop_time_index([row('A', 1), row('B', 10), row('C', 30), row('D', 999)])
    stop = {1:'A', 10:'B', 30:'C', 999:'D'}[sequence]
    records = convert_trip_update(entity([(stop, sequence, int(START.timestamp())+75)]), index)
    assert records[0]['scheduled_arrival'] == START.isoformat()
    assert records[0]['delay_seconds'] == 75


def test_repeated_stop_visits_require_their_exact_sequence():
    index = build_stop_time_index([row('LOOP', 10), row('LOOP', 30, '23:10:00')])
    item = entity([('LOOP', 10, int(START.timestamp())+60),
                   ('LOOP', 30, int(START.timestamp())+660)])
    records = convert_trip_update(item, index)
    assert [r['scheduled_arrival'] for r in records] == [
        '2026-10-21T23:00:00+10:30', '2026-10-21T23:10:00+10:30']
    assert [r['delay_seconds'] for r in records] == [60, 60]
    # A unique sequence is needed even when stop_id alone exists twice.
    assert convert_trip_update(entity([('LOOP', 20, int(START.timestamp()))]), index) == []


@pytest.mark.parametrize('stop,sequence,time', [
    ('B', 2, int(START.timestamp())),  # Dense ordinal is not static sequence 3.
    ('B', 1, int(START.timestamp())),  # Sequence belongs to a different stop.
    ('MISSING', 3, int(START.timestamp())),
    ('B', 3, None),
    ('', 3, int(START.timestamp())),
])
def test_incorrect_or_incomplete_relationship_is_not_remapped(stop, sequence, time):
    index = build_stop_time_index([row('A', 1), row('B', 3)])
    assert convert_trip_update(entity([(stop, sequence, time)]), index) == []


def test_feed_version_choice_changes_matching_and_schedule_not_a_global_offset():
    item = entity([('B', 2, int(START.timestamp())+360)])
    old = build_stop_time_index([row('B', 2, '23:05:00')])
    current = build_stop_time_index([row('A', 1), row('B', 3, '23:06:00')])
    assert convert_trip_update(item, old)[0]['delay_seconds'] == 60
    assert convert_trip_update(item, current) == []
    item.trip_update.stop_time_update[0].stop_sequence = 3
    assert convert_trip_update(item, current)[0]['delay_seconds'] == 0


def test_decode_match_delay_persist_restart_and_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'v2.db')
    monkeypatch.setenv('ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS', '900')
    monkeypatch.setattr('backend.realtime.client.urlopen', Mock(side_effect=AssertionError('Live HTTP forbidden')))
    create_tables()
    sentinel = {'trip_id':'OLD', 'route_id':'R', 'stop_id':'ARCHIVE',
                'scheduled_arrival':START.isoformat(), 'actual_arrival':START.isoformat(),
                'delay_seconds':0, 'timestamp':START.isoformat()}
    persist_realtime_collection([], [sentinel])
    index = build_stop_time_index([
        row('A', 10), row('B', 30, '23:10:00'),
        row('LOOP', 40, '23:20:00'), row('LOOP', 60, '23:30:00')])
    item = entity([('A', 10, int(START.timestamp())+90),
                   ('B', 20, int(START.timestamp())+660),  # Must remain skipped.
                   ('LOOP', 50, int(START.timestamp())+1200),  # Ambiguous stop_id.
                   ('MISSING', 70, int(START.timestamp()))])
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = '2.0'
    feed.entity.add().CopyFrom(item)
    empty = gtfs_realtime_pb2.FeedMessage()
    empty.header.gtfs_realtime_version = '2.0'
    summaries = []
    for delta in (0, 60, 900):
        feed.entity[0].trip_update.timestamp = int(START.timestamp())+delta
        client = SimpleNamespace(settings=GTFSRealtimeCollectionSettings(),
                                 fetch_vehicle_positions=Mock(return_value=empty.SerializeToString()),
                                 fetch_trip_updates=Mock(return_value=feed.SerializeToString()))
        # A fresh pipeline per cycle uses database state, not a collector cache.
        records = GTFSRealtimeProcessingPipeline(client=client, stop_time_index=index).process_once()
        assert len(records['trip_updates']) == 1
        assert records['trip_updates'][0]['delay_seconds'] == 90
        summaries.append(persist_realtime_collection(**records))
    assert [s['trip_updates_inserted'] for s in summaries] == [1, 0, 1]
    assert [s['trip_updates_suppressed'] for s in summaries] == [0, 1, 0]
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute("SELECT COUNT(*) FROM trip_updates WHERE trip_id='OLD'").fetchone()[0] == 1
        assert db.execute("SELECT observation_kind FROM trip_updates WHERE trip_id='T' ORDER BY id").fetchall() == [(0,), (2,)]
        assert db.execute("SELECT stop_id, delay_seconds FROM trip_update_current_state WHERE trip_id='T'").fetchall() == [('A', 90)]
        assert db.execute('SELECT COUNT(*) FROM collection_cycles').fetchone()[0] == 4


def test_offline_audit_separates_mapping_skips_from_raw_invalid_entries(tmp_path):
    import zipfile
    spec = importlib.util.spec_from_file_location('compatibility_audit', Path(__file__).resolve().parents[2] / 'scripts/audit_static_realtime_compatibility.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    static = tmp_path / 'static.zip'
    with zipfile.ZipFile(static, 'w') as archive:
        archive.writestr('stop_times.txt', 'trip_id,stop_id,stop_sequence,arrival_time\nT,A,1,23:00:00\nT,B,3,23:10:00\n')
    item = entity([('A', 1, int(START.timestamp())),
                   ('B', 2, int(START.timestamp())+600),
                   ('B', 3, None)])
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = '2.0'
    feed.entity.add().CopyFrom(item)
    snapshot = tmp_path / 'snapshot.pb'
    snapshot.write_bytes(feed.SerializeToString())
    result = module.audit(static, snapshot)
    assert result['counts']['stop_entries'] == 3
    assert result['counts']['exact'] == 2  # Includes a raw entry without arrival.
    assert result['counts']['eligible_before_lookup'] == 2
    assert result['counts']['valid_mapping_skips'] == 1
    assert result['counts']['collector_database_ready_records'] == 1
    assert result['counts']['mismatch_equals_dense_static_ordinal'] == 1
