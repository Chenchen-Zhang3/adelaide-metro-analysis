"""C05 recovery tests: synthetic feeds, disposable v2 SQLite, no live requests."""

import gc
from contextlib import closing
import json
import logging
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
import uuid
import weakref
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from google.transit import gtfs_realtime_pb2

from backend.database import connection as database
from backend.database import repository
from backend.database.models import create_tables
from backend.realtime.client import (
    GTFSRealtimeConnectionError, GTFSRealtimeHTTPError, GTFSRealtimeTimeoutError,
)
from backend.realtime.collector import GTFSRealtimeCollector
from backend.realtime.config import GTFSRealtimeCollectionSettings
from backend.services.historical_backup import create_sqlite_backup
from backend.services.historical_collection import (
    HistoricalCollectionRunner, create_logging_handlers,
)
from backend.services import historical_collection
from backend.services.pipeline import run_collection_and_persist
from backend.services.windows_single_instance import (
    WindowsSingleInstanceGuard,
)


ROOT = Path(__file__).resolve().parents[2]
START = datetime.fromisoformat('2026-10-13T09:00:00+10:30')
TABLES = ('vehicle_positions', 'trip_updates', 'trip_update_current_state', 'collection_cycles')


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'v2.db')
    monkeypatch.setenv('ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS', '900')
    monkeypatch.setattr('backend.realtime.client.urlopen', Mock(side_effect=AssertionError('Live HTTP forbidden')))
    create_tables()


def cycle(minute, delay=60, present=True):
    observed = (START + timedelta(minutes=minute)).isoformat()
    return {
        'vehicle_positions': [{'vehicle_id': 'V', 'latitude': -34.9, 'longitude': 138.6, 'timestamp': observed}],
        'trip_updates': [{
            'trip_id': 'T', 'route_id': 'R', 'stop_id': 'S',
            'scheduled_arrival': START.isoformat(),
            'actual_arrival': (START + timedelta(seconds=delay)).isoformat(),
            'delay_seconds': delay, 'timestamp': observed,
        }] if present else [],
    }


def snapshot(path=None):
    with closing(sqlite3.connect(path or database.DATABASE_PATH)) as db:
        return {table: db.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall() for table in TABLES}


def fake_collector(events):
    iterator = iter(events)
    def collect_once():
        event = next(iterator)
        if isinstance(event, Exception):
            raise event
        return event
    return SimpleNamespace(
        client=SimpleNamespace(settings=GTFSRealtimeCollectionSettings()),
        collect_once=collect_once,
    )


def feed_bytes(kind, minute=0, invalid_entity=False):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = '2.0'
    entity = feed.entity.add()
    entity.id = 'synthetic'
    timestamp = int((START + timedelta(minutes=minute)).timestamp())
    if kind == 'vehicle':
        entity.vehicle.vehicle.id = '' if invalid_entity else 'V'
        entity.vehicle.position.latitude = -34.9
        entity.vehicle.position.longitude = 138.6
        entity.vehicle.timestamp = timestamp
    else:
        update = entity.trip_update
        update.trip.trip_id = '' if invalid_entity else 'T'
        update.trip.route_id = 'R'
        update.trip.start_date = '20261013'
        update.timestamp = timestamp
        stop = update.stop_time_update.add()
        stop.stop_id = 'S'
        stop.stop_sequence = 1
        stop.arrival.time = int(START.timestamp()) + 60
    return feed.SerializeToString()


@pytest.mark.parametrize('failure', [
    GTFSRealtimeConnectionError('network down'), GTFSRealtimeTimeoutError('timeout'),
    *[GTFSRealtimeHTTPError('mock://feed', status) for status in (429, 500, 502, 503)],
])
def test_exhausted_feed_retries_skip_ledger_and_recover(failure, caplog):
    client = Mock(settings=GTFSRealtimeCollectionSettings())
    client.fetch_vehicle_positions.side_effect = [failure, failure, failure, feed_bytes('vehicle', 1)]
    client.fetch_trip_updates.return_value = feed_bytes('trip', 1)
    retry_waits, poll_waits = [], []
    collector = GTFSRealtimeCollector(client, {('T', 'S', 1): {'arrival_time': '09:00:00'}}, retry_waits.append)
    with caplog.at_level(logging.INFO):
        result = run_collection_and_persist(collector, max_cycles=2, sleep_function=poll_waits.append)
    assert len(result) == 1
    assert retry_waits == [5, 5]
    assert poll_waits == [60]
    assert client.fetch_vehicle_positions.call_count == 4
    assert client.fetch_trip_updates.call_count == 1
    state = snapshot()
    assert len(state['collection_cycles']) == len(state['trip_updates']) == 1
    assert state['collection_cycles'][0][1] == int((START + timedelta(minutes=1)).timestamp())
    assert 'Temporary failure' in caplog.text and 'retries were exhausted' in caplog.text


@pytest.mark.parametrize('bad_payload', [b'', b'\xff\xff'])
def test_empty_response_or_invalid_protobuf_recovers_without_false_success(bad_payload, caplog):
    client = Mock(settings=GTFSRealtimeCollectionSettings())
    client.fetch_vehicle_positions.return_value = feed_bytes('vehicle')
    client.fetch_trip_updates.side_effect = [bad_payload, feed_bytes('trip', 1)]
    collector = GTFSRealtimeCollector(client, {('T', 'S', 1): {'arrival_time': '09:00:00'}})
    waits = []
    with caplog.at_level(logging.ERROR):
        result = run_collection_and_persist(collector, max_cycles=2, sleep_function=waits.append)
    assert len(result) == 1 and waits == [60]
    assert len(snapshot()['collection_cycles']) == 1
    assert len(snapshot()['vehicle_positions']) == 1
    assert 'failed while processing feed data' in caplog.text


def test_valid_empty_feed_records_success_not_prediction_change():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = '2.0'
    client = Mock(settings=GTFSRealtimeCollectionSettings())
    client.fetch_vehicle_positions.return_value = feed.SerializeToString()
    client.fetch_trip_updates.return_value = feed.SerializeToString()
    with patch('backend.database.repository.time', return_value=int(START.timestamp())):
        run_collection_and_persist(GTFSRealtimeCollector(client), max_cycles=1)
    state = snapshot()
    assert len(state['collection_cycles']) == 1
    assert state['collection_cycles'][0][1:] == (int(START.timestamp()), 0, 0, 0, 0)
    assert not state['trip_updates']


def test_invalid_entities_are_visible_but_decoded_cycle_is_success(caplog):
    client = Mock(settings=GTFSRealtimeCollectionSettings())
    client.fetch_vehicle_positions.return_value = feed_bytes('vehicle', invalid_entity=True)
    client.fetch_trip_updates.return_value = feed_bytes('trip', invalid_entity=True)
    with caplog.at_level(logging.WARNING):
        run_collection_and_persist(GTFSRealtimeCollector(client), max_cycles=1)
    assert len(snapshot()['collection_cycles']) == 1
    assert not snapshot()['trip_updates']
    assert 'Skipped 1 invalid vehicle' in caplog.text and 'Skipped 1 invalid trip' in caplog.text


@pytest.mark.parametrize('stage', ['connect', 'begin', 'vehicle', 'state', 'ledger', 'commit'])
def test_database_failures_leave_all_tables_unchanged_and_next_cycle_resumes(stage, caplog):
    repository.persist_realtime_collection(**cycle(0))
    before = snapshot()
    opened = []
    class FaultConnection(sqlite3.Connection):
        rolled_back = False
        closed = False
        def cursor(self, *args, **kwargs):
            cursor = super().cursor(*args, **kwargs)
            if stage in ('begin', 'vehicle', 'state', 'ledger'):
                target = {'begin': 'BEGIN', 'vehicle': 'vehicle_positions',
                          'state': 'trip_update_current_state', 'ledger': 'collection_cycles'}[stage]
                def authorizer(action, name, *rest):
                    if stage == 'begin' and action == sqlite3.SQLITE_TRANSACTION and name == 'BEGIN':
                        return sqlite3.SQLITE_DENY
                    if stage != 'begin' and action == sqlite3.SQLITE_INSERT and name == target:
                        return sqlite3.SQLITE_DENY
                    return sqlite3.SQLITE_OK
                self.set_authorizer(authorizer)
            return cursor
        def commit(self):
            if stage == 'commit':
                raise sqlite3.OperationalError('injected commit failure')
            return super().commit()
        def rollback(self):
            self.rolled_back = True
            return super().rollback()
        def close(self):
            self.closed = True
            return super().close()
    real_get_connection = repository.get_connection
    attempts = 0
    def injected_connection():
        nonlocal attempts
        attempts += 1
        if attempts > 1:
            return real_get_connection()
        if stage == 'connect':
            raise sqlite3.OperationalError('injected connection failure')
        conn = sqlite3.connect(database.DATABASE_PATH, factory=FaultConnection)
        conn.row_factory = sqlite3.Row
        opened.append(conn)
        return conn
    checkpoints = []
    def wait(seconds):
        assert seconds == 60
        checkpoints.append(snapshot())
    with patch.object(repository, 'get_connection', side_effect=injected_connection), caplog.at_level(logging.ERROR):
        result = run_collection_and_persist(fake_collector([cycle(1, 120), cycle(2, 180)]), max_cycles=2, sleep_function=wait)
    assert checkpoints == [before]
    assert len(result) == 1
    if opened:
        assert opened[0].closed
        if stage not in ('begin', 'connect'):
            assert opened[0].rolled_back
    after = snapshot()
    assert len(after['collection_cycles']) == 2
    assert after['trip_update_current_state'][0][4] == 180
    assert 'failed while persisting' in caplog.text


def test_actual_sqlite_write_lock_releases_and_runner_resumes(caplog):
    blocker = sqlite3.connect(database.DATABASE_PATH)
    blocker.execute('BEGIN IMMEDIATE')
    waits = []
    def fast_connection():
        db = sqlite3.connect(database.DATABASE_PATH, timeout=0)
        db.row_factory = sqlite3.Row
        return db
    def unlock(seconds):
        waits.append(seconds)
        assert not snapshot()['collection_cycles']
        blocker.rollback()
    try:
        with patch.object(repository, 'get_connection', side_effect=fast_connection), caplog.at_level(logging.ERROR):
            results = run_collection_and_persist(fake_collector([cycle(0), cycle(1)]), max_cycles=2, sleep_function=unlock)
        assert len(results) == 1 and waits == [60]
        assert 'database is locked' in caplog.text
        assert len(snapshot()['collection_cycles']) == 1
    finally:
        blocker.close()


def test_successful_cycles_close_every_repository_connection():
    opened = []
    class TrackedConnection(sqlite3.Connection):
        closed = False
        def close(self):
            self.closed = True
            return super().close()
    def tracked_connection():
        conn = sqlite3.connect(database.DATABASE_PATH, factory=TrackedConnection)
        conn.row_factory = sqlite3.Row
        opened.append(conn)
        return conn
    with patch.object(repository, 'get_connection', side_effect=tracked_connection):
        results = run_collection_and_persist(fake_collector(cycle(m) for m in range(30)),
                                             max_cycles=30, sleep_function=lambda seconds: None)
    assert len(results) == len(opened) == 30
    assert all(conn.closed for conn in opened)


def test_short_absence_is_suppressed_and_long_absence_is_reappearance():
    records = [cycle(m, present=(m in (0, 7, 23))) for m in range(24)]
    results = run_collection_and_persist(fake_collector(records), max_cycles=24, sleep_function=lambda seconds: None)
    assert results[7]['persistence_result']['trip_updates_inserted'] == 0
    assert results[23]['persistence_result']['trip_updates_reappeared'] == 1
    state = snapshot()
    assert [row[-1] for row in state['trip_updates']] == [0, 3]
    assert len(state['collection_cycles']) == 24


def test_stale_feed_records_cycles_but_ledger_time_is_observation_not_wall_clock():
    run_collection_and_persist(fake_collector([cycle(0), cycle(0)]), max_cycles=2,
                               sleep_function=lambda seconds: None)
    state = snapshot()
    assert len(state['trip_updates']) == 1 and len(state['collection_cycles']) == 2
    assert state['collection_cycles'][0][1] == state['collection_cycles'][1][1] == int(START.timestamp())


def child(code, path=None):
    environment = dict(os.environ, ADELAIDE_METRO_DATABASE_PATH=str(path or database.DATABASE_PATH), PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=environment,
                          capture_output=True, text=True, timeout=30)


CHILD_CYCLE = """
from datetime import datetime, timedelta
from backend.database.models import create_tables
from backend.database.repository import persist_realtime_collection
base = datetime.fromisoformat('2026-10-13T09:00:00+10:30')
def write(minute, delay=60):
    return persist_realtime_collection([], [{'trip_id':'T','route_id':'R','stop_id':'S',
        'scheduled_arrival':base.isoformat(), 'delay_seconds':delay,
        'timestamp':(base+timedelta(minutes=minute)).isoformat()}])
"""


def test_clean_process_restart_preserves_state_and_checkpoint():
    first = child(CHILD_CYCLE + 'create_tables()\nwrite(0)\nwrite(1)\nwrite(2)\n')
    assert first.returncode == 0, first.stderr
    initial = snapshot()
    second = child(CHILD_CYCLE + "create_tables()\nassert write(3)['trip_updates_inserted'] == 0\nwrite(4, 120)\nfor minute in range(5,20): write(minute,120)\n")
    assert second.returncode == 0, second.stderr
    state = snapshot()
    assert state['trip_updates'][0] == initial['trip_updates'][0]
    assert [row[-1] for row in state['trip_updates']] == [0, 1, 2]
    assert len(state['collection_cycles']) == 20
    current = state['trip_update_current_state'][0]
    assert current[4] == 120
    assert current[5] == current[6] == int((START + timedelta(minutes=19)).timestamp())


def test_abrupt_process_exit_before_commit_recovers_journal_and_preserves_history():
    repository.persist_realtime_collection(**cycle(0))
    before = snapshot()
    crash = child(CHILD_CYCLE + """
import os, sqlite3
from backend.database import repository, connection
class CrashConnection(sqlite3.Connection):
    def commit(self): os._exit(23)
def open_connection():
    db = sqlite3.connect(connection.DATABASE_PATH, factory=CrashConnection)
    db.row_factory = sqlite3.Row
    return db
repository.get_connection = open_connection
write(1, 120)
""")
    assert crash.returncode == 23, crash.stderr
    assert snapshot() == before
    recovery = child(CHILD_CYCLE + 'create_tables()\nwrite(2, 180)\n')
    assert recovery.returncode == 0, recovery.stderr
    assert len(snapshot()['collection_cycles']) == 2
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_v2_online_backup_restore_and_continue_without_overwriting_source(tmp_path):
    repository.persist_realtime_collection(**cycle(0))
    repository.persist_realtime_collection(**cycle(1))
    before = snapshot()
    source = database.DATABASE_PATH
    destination = tmp_path / 'snapshot.db'
    with closing(sqlite3.connect(source)) as live:
        live.execute('BEGIN IMMEDIATE')
        live.execute("UPDATE trip_update_current_state SET delay_seconds=999")
        create_sqlite_backup(source, destination)
        live.rollback()
    assert snapshot(destination) == before
    restored = tmp_path / 'restored' / 'v2.db'
    create_sqlite_backup(destination, restored)
    result = child(CHILD_CYCLE + "create_tables()\nassert write(2)['trip_updates_inserted'] == 0\nwrite(3,120)\n", restored)
    assert result.returncode == 0, result.stderr
    assert snapshot(source) == before == snapshot(destination)
    assert len(snapshot(restored)['collection_cycles']) == 4
    assert len(snapshot(restored)['trip_updates']) == 2
    for path in (source, destination, restored):
        with closing(sqlite3.connect(path)) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert db.execute("SELECT value FROM schema_metadata WHERE name='historical_storage_version'").fetchone()[0] == '2'


def test_actual_rotating_log_rollover_is_bounded(tmp_path):
    path = tmp_path / 'logs' / 'collector.log'
    handlers = create_logging_handlers(path)
    handler = handlers[1]
    assert handler.maxBytes == 5 * 1024 * 1024 and handler.backupCount == 5
    handler.maxBytes = 128  # Exercise real rollover quickly; production policy unchanged.
    logger = logging.getLogger(f'c05-rotation-{uuid.uuid4()}')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    try:
        for index in range(30):
            logger.info('cycle %02d completed successfully with suppressed unchanged states', index)
        handler.flush()
    finally:
        logger.removeHandler(handler)
        for item in handlers:
            item.close()
    assert len(list(path.parent.glob('collector.log*'))) == 6
    assert 'cycle 29' in path.read_text(encoding='utf8')


@pytest.mark.skipif(os.name != 'nt', reason='Actual Windows mutex needs Windows')
def test_windows_mutex_rejects_second_process_then_allows_restart():
    name = f'C05-{uuid.uuid4()}'
    code = f"""
from backend.services.windows_single_instance import WindowsSingleInstanceGuard, HistoricalCollectorAlreadyRunningError
try:
    with WindowsSingleInstanceGuard({name!r}): pass
except HistoricalCollectorAlreadyRunningError:
    raise SystemExit(2)
"""
    with WindowsSingleInstanceGuard(name):
        duplicate = child(code)
        assert duplicate.returncode == 2, duplicate.stderr
    restarted = child(code)
    assert restarted.returncode == 0, restarted.stderr


@pytest.mark.skipif(os.name != 'nt', reason='Actual Windows mutex needs Windows')
def test_windows_mutex_is_released_after_abrupt_process_exit():
    name = f'C05-crash-{uuid.uuid4()}'
    prefix = 'from backend.services.windows_single_instance import WindowsSingleInstanceGuard\n'
    crashed = child(prefix + f'import os\nwith WindowsSingleInstanceGuard({name!r}): os._exit(23)\n')
    assert crashed.returncode == 23, crashed.stderr
    recovered = child(prefix + f'with WindowsSingleInstanceGuard({name!r}): pass\n')
    assert recovered.returncode == 0, recovered.stderr


@pytest.mark.parametrize('failure,exit_code,message', [
    (None, 0, 'stopped normally'), (KeyboardInterrupt(), 0, 'stopped by user'),
    (RuntimeError('injected fatal error'), 1, 'stopped after a fatal error'),
])
def test_cli_start_and_shutdown_logs(failure, exit_code, message, caplog):
    runner = Mock()
    runner.run.side_effect = failure
    with patch.object(historical_collection, 'HistoricalCollectionRunner', return_value=runner), \
         patch.object(historical_collection, 'WindowsSingleInstanceGuard'), \
         patch.object(historical_collection, 'configured_log_path', return_value=None), \
         patch.object(historical_collection.logging, 'basicConfig') as configure, \
         caplog.at_level(logging.INFO):
        result = historical_collection.main(['--static-gtfs-dir', 'synthetic', '--max-cycles', '1'])
    for handler in configure.call_args.kwargs['handlers']:
        handler.close()
    assert result == exit_code
    assert 'Historical GTFS collector starting' in caplog.text and message in caplog.text
    runner.run.assert_called_once_with(max_cycles=1)


def test_continuous_run_releases_old_cycle_payloads():
    references = []
    class Payload:
        pass
    count = 0
    def collect():
        nonlocal count
        count += 1
        payload = Payload()
        references.append(weakref.ref(payload))
        return {'collection_result': payload, 'persistence_result': {
            'vehicle_positions_inserted':0, 'vehicle_positions_received':0,
            'trip_updates_inserted':0, 'trip_updates_received':0,
        }}
    event = SimpleNamespace(is_set=lambda: count >= 100, wait=lambda seconds: count >= 100)
    with patch('backend.services.pipeline.collect_and_persist', side_effect=lambda collector: collect()):
        results = run_collection_and_persist(fake_collector([]), stop_event=event)
    gc.collect()
    assert count == 100
    assert sum(reference() is not None for reference in references) == 1
    assert len(results) == 1


def test_bounded_360_cycle_simulation_with_restart_faults_and_reappearance(caplog):
    network_minutes = set(range(37, 360, 37))
    database_minutes = set(range(53, 360, 53))
    decode_minutes = set(range(71, 360, 71))
    failed = network_minutes | database_minutes | decode_minutes
    attempts, poll_waits, summaries = [], [], []
    def next_cycle(minute):
        attempts.append(minute)
        if minute in network_minutes:
            raise GTFSRealtimeTimeoutError('synthetic network timeout')
        if minute in database_minutes:
            record = cycle(minute, (minute // 40) * 60 + 60)
            record['trip_updates'][0]['actual_arrival'] = START.isoformat()
            return record  # Real transaction validation failure, not a fake success.
        if minute in decode_minutes:
            raise ValueError('synthetic invalid feed')
        return cycle(minute, (minute // 40) * 60 + 60, present=not 125 <= minute < 145)
    init_calls = []
    for start, end in ((0, 180), (180, 360)):
        def events(start=start, end=end):
            for minute in range(start, end):
                try:
                    yield next_cycle(minute)
                except Exception as error:
                    yield error
        collector = fake_collector(events())
        loader = Mock(return_value={})
        factory = Mock(return_value=SimpleNamespace(collector=collector))
        def initialise_schema():
            init_calls.append(1)
            create_tables()
        runner = HistoricalCollectionRunner('synthetic', pipeline_factory=factory,
                                            create_tables_function=initialise_schema, index_loader=loader)
        with caplog.at_level(logging.INFO):
            results = runner.run(max_cycles=end-start, sleep_function=poll_waits.append)
        summaries.extend(result['persistence_result'] for result in results)
        runner.initialise()
        loader.assert_called_once()
        factory.assert_called_once()
    state = snapshot()
    expected_success = 360 - len(failed)
    assert len(attempts) == 360 and len(summaries) == expected_success
    assert poll_waits == [60] * 358 and len(init_calls) == 2
    assert len(state['collection_cycles']) == expected_success
    assert len(state['vehicle_positions']) == expected_success
    assert len(state['trip_update_current_state']) == 1
    assert len(state['trip_updates']) == sum(item['trip_updates_inserted'] for item in summaries)
    kinds = [row[-1] for row in state['trip_updates']]
    assert all(kind in kinds for kind in (0, 1, 2, 3))
    assert kinds.count(3) == 1
    expected_times = [int((START + timedelta(minutes=m)).timestamp()) for m in range(360) if m not in failed]
    assert [row[1] for row in state['collection_cycles']] == expected_times
    assert sum(row[4] for row in state['collection_cycles']) == len(state['trip_updates'])
    assert all(row[3] == row[4] + row[5] for row in state['collection_cycles'])
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db:
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
        assert integrity == 'ok'
        largest_gap = db.execute('''
            SELECT MAX(gap_seconds) FROM (
                SELECT observed_at - LAG(observed_at) OVER (ORDER BY id) AS gap_seconds
                FROM collection_cycles
            )
        ''').fetchone()[0]
        assert largest_gap == max(b-a for a,b in zip(expected_times, expected_times[1:]))
        assert db.execute('SELECT observed_at FROM collection_cycles ORDER BY id DESC LIMIT 1').fetchone()[0] == expected_times[-1]
        db.execute('BEGIN EXCLUSIVE')  # No leaked reader/writer transaction remains.
        db.rollback()
    assert 'failed while retrieving a feed' in caplog.text
    assert 'failed while processing feed data' in caplog.text
    assert 'transaction rolled back' in caplog.text
    print('C05_SIMULATION=' + json.dumps({
        'attempted_cycles':360, 'successful_cycles':expected_success,
        'failed_cycles':len(failed), 'trip_history_rows':len(state['trip_updates']),
        'cycle_ledger_rows':len(state['collection_cycles']), 'current_state_rows':1,
        'vehicle_rows':len(state['vehicle_positions']), 'poll_waits':len(poll_waits),
        'kinds':{str(kind):kinds.count(kind) for kind in (0,1,2,3)},
        'integrity':integrity, 'largest_ledger_gap_seconds':largest_gap,
    }, sort_keys=True))
