"""Build a recorded demo using the existing v2 schema and persistence boundary.

Run this offline preparation utility in its own process, not inside the Flask
server: existing repository helpers use the module-level DATABASE_PATH.
"""

import argparse
from collections import defaultdict
from contextlib import closing, contextmanager
import csv
from datetime import datetime
from heapq import merge
from itertools import groupby
import json
import math
from pathlib import Path
import shutil
import sqlite3
import tempfile

from backend.database import connection as database
from backend.database import repository
from backend.database.historical_storage import iso_timestamp_to_epoch
from backend.database.models import create_tables
from backend.parsers.static_gtfs import parse_routes, parse_stops, parse_trips
from backend.services.gtfs_converter import (
    build_stop_time_index, convert_route, convert_stop, convert_stop_time, convert_trip,
)
from backend.services.gtfs_id_consistency import fingerprint


LABEL = 'Recorded Historical Data — September 2026'


@contextmanager
def demo_database(path):
    previous = database.DATABASE_PATH
    database.DATABASE_PATH = Path(path)
    try:
        yield
    finally:
        database.DATABASE_PATH = previous


def load_inputs(static, config):
    static = Path(static)
    with (static / 'feed_info.txt').open(encoding='utf-8-sig', newline='') as file:
        feed_info = list(csv.DictReader(file))
    if len(feed_info) != 1 or feed_info[0]['feed_version'] != config['static_feed_version']:
        raise ValueError('Static feed version differs from the pinned demo configuration')
    for key in ('start', 'end_exclusive'):
        day = datetime.fromisoformat(config[key]).strftime('%Y%m%d')
        if not feed_info[0]['feed_start_date'] <= day <= feed_info[0]['feed_end_date']:
            raise ValueError('Recorded observation window falls outside static feed coverage')
    files = {name: fingerprint(static / name) for name in ('routes.txt','trips.txt','stops.txt','stop_times.txt','feed_info.txt')}
    routes = {row['route_id']: row for row in parse_routes(static / 'routes.txt') if row['route_id'] in config['route_ids']}
    if set(routes) != set(config['route_ids']):
        raise ValueError('Selected route missing from static feed')
    trips = {row['trip_id']: row for row in parse_trips(static / 'trips.txt') if row['route_id'] in routes}
    stops = {row['stop_id']: row for row in parse_stops(static / 'stops.txt')}
    return routes, trips, stops, {'feed_info': feed_info, 'files': files}


def validate_config(config):
    if config.get('label') != LABEL:
        raise ValueError('Demo must explicitly use the recorded historical data label')
    if not config['route_ids'] or len(set(config['route_ids'])) != len(config['route_ids']):
        raise ValueError('Choose unique route IDs')
    start, end = (datetime.fromisoformat(config[key]) for key in ('start','end_exclusive'))
    if start.utcoffset() is None or end.utcoffset() is None or start >= end:
        raise ValueError('Use an increasing timezone-aware observation window')
    if start.utcoffset() != end.utcoffset():
        raise ValueError('Use one Adelaide UTC offset per extraction window')
    from zoneinfo import ZoneInfo
    for instant in (start, end):
        if instant.utcoffset() != instant.astimezone(ZoneInfo('Australia/Adelaide')).utcoffset():
            raise ValueError('Window offset must match Australia/Adelaide')
    if int(config.get('checkpoint_seconds', 900)) != 900:
        raise ValueError('Recorded demo preserves the existing 900-second checkpoint policy')


def verify_archive(static, archive, config, metadata):
    import hashlib
    import zipfile
    details = fingerprint(Path(archive))
    if details['sha256'] != config['static_archive_sha256']:
        raise ValueError('Static archive differs from the pinned SHA-256')
    with zipfile.ZipFile(archive) as zipped:
        for name, details_file in metadata['files'].items():
            with zipped.open(name) as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != details_file['sha256']:
                    raise ValueError(f'Extracted static file differs from archive: {name}')
    metadata['archive'] = details
    if (Path(static) / 'shapes.txt').is_file():
        metadata['shapes_file'] = fingerprint(Path(static) / 'shapes.txt')


def generate_demo(source, static, output, config, archive):
    """Never overwrite source/output. Publish only after validation succeeds."""
    validate_config(config)
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    manifest_path = output.with_suffix('.manifest.json')
    if output == source or output.exists() or manifest_path.exists():
        raise FileExistsError('Use a new demo output and manifest; never overwrite source or evidence')
    if output.suffix != '.db':
        raise ValueError('Demo output must use .db')
    routes, static_trips, stops, metadata = load_inputs(static, config)
    verify_archive(static, archive, config, metadata)
    before = (source.stat().st_size, source.stat().st_mtime_ns)
    placeholders = ','.join('?' for _ in routes)
    where = f'route_id IN ({placeholders}) AND timestamp>=? AND timestamp<?'
    parameters = (*routes, config['start'], config['end_exclusive'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro&immutable=1', uri=True)) as history:
        history.row_factory = sqlite3.Row
        history.execute('PRAGMA query_only=ON')
        columns = {row[1] for row in history.execute('PRAGMA table_info(trip_updates)')}
        if not {'timestamp','actual_arrival','scheduled_arrival'}.issubset(columns):
            raise ValueError('This extractor expects the archived legacy source, not v2')
        profiles, chosen_trips = {}, set()
        for table in ('vehicle_positions','trip_updates'):
            rows = history.execute(f'SELECT trip_id, route_id, COUNT(*) AS n, MIN(timestamp) AS first, MAX(timestamp) AS last FROM {table} WHERE {where} GROUP BY trip_id,route_id', parameters)
            profiles[table] = [dict(row) for row in rows]
            for row in profiles[table]:
                if row['trip_id'] not in static_trips or static_trips[row['trip_id']]['route_id'] != row['route_id']:
                    raise ValueError('Selected historical trip has an invalid static route mapping')
                chosen_trips.add(row['trip_id'])
        for route in routes:
            vehicle_trips = {row['trip_id'] for row in profiles['vehicle_positions'] if row['route_id'] == route}
            update_trips = {row['trip_id'] for row in profiles['trip_updates'] if row['route_id'] == route}
            if not vehicle_trips & update_trips:
                raise ValueError(f'No overlapping vehicle/update trip coverage for {route}')
        selected_stop_times = []
        with (Path(static) / 'stop_times.txt').open(encoding='utf-8-sig', newline='') as file:
            for row in csv.DictReader(file):
                if row['trip_id'] in chosen_trips:
                    selected_stop_times.append(convert_stop_time(row))
        selected_stop_times.sort(key=lambda row: (row['trip_id'], row['stop_sequence'], row['stop_id']))
        index = build_stop_time_index(selected_stop_times)
        pairs = {(trip, stop) for trip, stop, sequence in index}
        selected_stops = {row['stop_id'] for row in selected_stop_times}
        if not selected_stops.issubset(stops):
            raise ValueError('Selected stop_times reference a missing static stop')
        if not chosen_trips.issubset({row['trip_id'] for row in selected_stop_times}):
            raise ValueError('Selected trip has no static stop times')
        with tempfile.TemporaryDirectory(prefix='recorded-demo-build-', dir=output.parent) as temporary:
            staging = Path(temporary) / 'demo.db'
            with demo_database(staging):
                create_tables()
                for row in routes.values():
                    repository.insert_route(convert_route(row))
                for trip in sorted(chosen_trips):
                    repository.insert_trip(convert_trip(static_trips[trip]))
                for stop in sorted(selected_stops):
                    row = convert_stop(stops[stop])
                    if not valid_coordinates(row['stop_lat'], row['stop_lon']):
                        raise ValueError(f'Invalid static stop coordinates: {stop}')
                    repository.insert_stop(row)
                for row in selected_stop_times:
                    repository.insert_stop_time(row)
                def stream(table, kind):
                    for row in history.execute(f'SELECT * FROM {table} WHERE {where} ORDER BY timestamp,id', parameters):
                        record = dict(row)
                        yield record['timestamp'], kind, record['id'], record
                counts = {'vehicle_positions':0,'trip_updates':0,'trip_updates_suppressed':0,'import_transactions':0}
                coordinate_warnings = []
                delay_min, delay_max = None, None
                observed = merge(stream('vehicle_positions', 0), stream('trip_updates', 1))
                for timestamp, group in groupby(observed, key=lambda item:item[0]):
                    vehicles, updates = [], []
                    for timestamp, kind, source_id, record in group:
                        if kind == 0:
                            if not valid_coordinates(record['latitude'], record['longitude']):
                                raise ValueError('Invalid vehicle coordinates in selected history')
                            if not (-36 <= record['latitude'] <= -33 and 137 <= record['longitude'] <= 140) and len(coordinate_warnings) < 5:
                                coordinate_warnings.append({'source_id':source_id,'latitude':record['latitude'],'longitude':record['longitude']})
                            vehicles.append(record)
                        else:
                            if (record['trip_id'], record['stop_id']) not in pairs:
                                raise ValueError('Historical trip/stop pair absent from selected stop_times')
                            expected = iso_timestamp_to_epoch(record['scheduled_arrival'], required=True) + record['delay_seconds']
                            if iso_timestamp_to_epoch(record['actual_arrival'], required=True) != expected:
                                raise ValueError('Inconsistent source arrival/delay')
                            delay_min = record['delay_seconds'] if delay_min is None else min(delay_min, record['delay_seconds'])
                            delay_max = record['delay_seconds'] if delay_max is None else max(delay_max, record['delay_seconds'])
                            updates.append(record)
                    result = repository.persist_realtime_collection(vehicles, updates, checkpoint_seconds=900)
                    counts['vehicle_positions'] += len(vehicles)
                    counts['trip_updates'] += len(updates)
                    counts['trip_updates_suppressed'] += result['trip_updates_suppressed']
                    counts['import_transactions'] += 1
                validation = smoke_demo(config, chosen_trips)
                with closing(sqlite3.connect(staging)) as built:
                    table_counts = {name:built.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] for name in
                                    ('routes','trips','stops','stop_times','vehicle_positions','trip_updates','trip_update_current_state','collection_cycles')}
                    integrity = built.execute('PRAGMA integrity_check').fetchone()[0]
                    if integrity != 'ok':
                        raise ValueError(f'Demo integrity failed: {integrity}')
                    for table in ('vehicle_positions', 'trip_updates'):
                        if counts[table] != sum(row['n'] for row in profiles[table]):
                            raise ValueError('Extraction count differs from bounded source profile')
                    if table_counts['vehicle_positions'] != counts['vehicle_positions']:
                        raise ValueError('Vehicle observations were unexpectedly discarded')
                    if table_counts['trip_updates'] != counts['trip_updates'] - counts['trip_updates_suppressed']:
                        raise ValueError('Trip Update conversion counts are inconsistent')
                    if table_counts['collection_cycles'] != counts['import_transactions']:
                        raise ValueError('Demo import ledger is inconsistent')
                    built.execute("INSERT INTO schema_metadata VALUES ('dataset_label', ?)", (LABEL,))
                    built.execute("INSERT INTO schema_metadata VALUES ('ledger_provenance', 'recorded subset import transactions; NOT original CASR collection-cycle telemetry')")
                    built.commit()
            after = (source.stat().st_size, source.stat().st_mtime_ns)
            if after != before:
                raise RuntimeError('Original source metadata changed during extraction')
            manifest = {
                'label':LABEL, 'config':config, 'source':{'name':source.name,'bytes':before[0],'mtime_ns':before[1],
                    'open_mode':'mode=ro&immutable=1; query_only=ON','unchanged':True},
                'static':metadata, 'source_selected_counts':counts, 'output_counts':table_counts,
                'output_database':fingerprint(staging), 'integrity_check':integrity,
                'delay_range_seconds':[delay_min,delay_max], 'coordinate_warning_examples':coordinate_warnings,
                'selected_trip_ids':sorted(chosen_trips), 'selected_stop_ids':sorted(selected_stops),
                'route_profiles':{route:{'route':convert_route(routes[route]),
                    'vehicle_rows':sum(r['n'] for r in profiles['vehicle_positions'] if r['route_id']==route),
                    'trip_update_source_rows':sum(r['n'] for r in profiles['trip_updates'] if r['route_id']==route),
                    'overlapping_trip_ids': sorted({r['trip_id'] for r in profiles['vehicle_positions'] if r['route_id']==route} & {r['trip_id'] for r in profiles['trip_updates'] if r['route_id']==route}),
                    'shape_ids':sorted({static_trips[trip].get('shape_id','') for trip in chosen_trips if static_trips[trip]['route_id']==route} - {''})}
                    for route in routes},
                'validation':validation,
                'ledger_provenance':'Successful demo import transactions grouped by actual source observation timestamp; not original CASR scheduler cycles',
                'frontend_status':'Existing API tested with Flask test client; browser playback/vehicle endpoints remain SCRUM-234 work',
            }
            manifest['output_database']['name'] = output.name
            published = []
            try:
                with output.open('xb') as target, staging.open('rb') as source_stream:
                    published.append(output)
                    shutil.copyfileobj(source_stream, target)
                with manifest_path.open('x', encoding='utf8') as target:
                    published.append(manifest_path)
                    json.dump(manifest,target,ensure_ascii=False,indent=2)
                    target.write('\n')
            except BaseException:
                for owned in published:
                    owned.unlink(missing_ok=True)
                raise
    return manifest


def valid_coordinates(latitude, longitude):
    return math.isfinite(latitude) and math.isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180


def smoke_demo(config, chosen_trips):
    """Exercise exactly the repository, analysis and Flask interfaces in use."""
    from backend.api.app import app
    from backend.services.pipeline import query_and_analyse
    details = {}
    for route in config['route_ids']:
        vehicles = repository.get_vehicle_positions_filtered(route_id=route, start_time=config['start'], end_time=config['end_exclusive'])
        updates = repository.get_trip_updates_filtered(route_id=route, start_time=config['start'], end_time=config['end_exclusive'])
        if not vehicles or not updates:
            raise ValueError(f'Empty repository query result for {route}')
        if not all(row['trip_id'] in chosen_trips for row in vehicles+updates):
            raise ValueError('Query returned unexpected trip')
        if not all(config['start'] <= row['timestamp'] < config['end_exclusive'] for row in vehicles+updates):
            raise ValueError('Query returned an observation outside the recorded window')
        if not all(iso_timestamp_to_epoch(row['actual_arrival']) - iso_timestamp_to_epoch(row['scheduled_arrival']) == row['delay_seconds'] for row in updates):
            raise ValueError('Repository arrival reconstruction failed')
        stop = updates[0]['stop_id']
        if not repository.get_trip_updates_by_stop(stop):
            raise ValueError('Stop query failed')
        if route not in {row['route_id'] for row in repository.get_routes_by_stop(stop)}:
            raise ValueError('Static route/stop join failed')
        analysis = query_and_analyse(route_id=route, start_time=config['start'], end_time=config['end_exclusive'])
        if route not in analysis['route_performance']:
            raise ValueError('Route analysis failed')
        endpoints = ['/api/routes','/api/stops',f'/api/routes/{route}/performance',f'/api/stops/{stop}/routes',f'/api/stops/{stop}/performance']
        with app.test_client() as client:
            statuses = {endpoint:client.get(endpoint).status_code for endpoint in endpoints}
        if any(status != 200 for status in statuses.values()):
            raise ValueError(f'Backend API smoke failed: {statuses}')
        details[route] = {'vehicle_query_rows':len(vehicles),'trip_update_query_rows':len(updates),
                          'sample_vehicle':vehicles[0], 'sample_trip_update':updates[0],
                          'sample_stop_id':stop,'api_statuses':statuses}
    return details


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source','static-dir','static-archive','output','config'):
        parser.add_argument('--'+name,type=Path,required=True)
    options = parser.parse_args(arguments)
    with options.config.open(encoding='utf8') as file:
        config = json.load(file)
    manifest = generate_demo(options.source,options.static_dir,options.output,config,options.static_archive)
    print(json.dumps({key:manifest[key] for key in ('label','source_selected_counts','output_counts','output_database','integrity_check')},indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
