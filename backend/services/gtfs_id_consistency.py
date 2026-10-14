"""Read-only static/historical GTFS ID audit; never initialise a database."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
from datetime import datetime, timezone
import hashlib
from itertools import islice
import json
from pathlib import Path
import sqlite3
import zipfile

from backend.parsers.static_gtfs import parse_routes, parse_stops, parse_trips
from backend.services.gtfs_converter import build_stop_time_index


FIELDS = ('route_id', 'trip_id', 'stop_id')


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'name': path.name, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def load_static(directory, archive=None):
    """Reuse project parsers; stream the large stop-time file in small batches."""
    directory = Path(directory)
    identifiers = {}
    trip_routes = defaultdict(set)
    files, problems = {}, Counter()
    for field, filename, parser in (
        ('route_id', 'routes.txt', parse_routes),
        ('trip_id', 'trips.txt', parse_trips),
        ('stop_id', 'stops.txt', parse_stops),
    ):
        path = directory / filename
        if not path.is_file():
            identifiers[field] = None
            continue
        rows = parser(path)
        ids = [row[field] for row in rows]
        identifiers[field] = {value for value in ids if value not in (None, '')}
        problems[f'{field}_blank_records'] = sum(value in (None, '') for value in ids)
        problems[f'{field}_duplicate_records'] = len(ids) - len(set(ids))
        problems[f'{field}_whitespace_records'] = sum(bool(value) and value != value.strip() for value in ids)
        files[filename] = fingerprint(path)
        files[filename]['rows'] = len(rows)
        if field == 'trip_id':
            for row in rows:
                trip_routes[row['trip_id']].add(row['route_id'])
                if identifiers['route_id'] is not None and row['route_id'] not in identifiers['route_id']:
                    problems['trip_route_reference_missing'] += 1
    problems['conflicting_trip_route_keys'] = sum(len(routes) > 1 for routes in trip_routes.values())
    pairs = None
    stop_path = directory / 'stop_times.txt'
    if stop_path.is_file():
        pairs = set()
        count = 0
        with stop_path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            required = {'trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time'}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError('stop_times.txt is missing required fields')
            while batch := list(islice(reader, 5000)):
                # Keep the existing string-ID / integer-sequence key semantics.
                for trip_id, stop_id, sequence in build_stop_time_index(batch):
                    pairs.add((trip_id, stop_id))
                for row in batch:
                    if identifiers['trip_id'] is not None and row['trip_id'] not in identifiers['trip_id']:
                        problems['stop_time_trip_reference_missing'] += 1
                    if identifiers['stop_id'] is not None and row['stop_id'] not in identifiers['stop_id']:
                        problems['stop_time_stop_reference_missing'] += 1
                count += len(batch)
        files['stop_times.txt'] = {**fingerprint(stop_path), 'rows': count, 'unique_trip_stop_pairs': len(pairs)}
    for name in ('feed_info.txt', 'shapes.txt'):
        if (directory / name).is_file():
            files[name] = fingerprint(directory / name)
    feed_info = []
    if (directory / 'feed_info.txt').is_file():
        with (directory / 'feed_info.txt').open(encoding='utf-8-sig', newline='') as stream:
            feed_info = list(csv.DictReader(stream))
    provenance = {'directory': str(directory.resolve()), 'files': files, 'feed_info': feed_info,
                  'missing_files': [name for name in ('routes.txt', 'trips.txt', 'stops.txt', 'stop_times.txt') if name not in files],
                  'diagnostics': dict(problems)}
    if archive is not None:
        archive = Path(archive)
        provenance['archive'] = fingerprint(archive)
        with zipfile.ZipFile(archive) as zipped:
            checks = {}
            for name, details in files.items():
                try:
                    with zipped.open(name) as stream:
                        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                    checks[name] = digest == details['sha256']
                except KeyError:
                    checks[name] = None
            provenance['archive_file_matches'] = checks
    return identifiers, trip_routes, pairs, provenance


def id_result(observed, reference, missing_rows, row_counts, limit):
    """Unique-ID percentages exclude NULL/empty IDs; row coverage is separate."""
    result = {'unique_realtime_ids': len(observed), 'missing_identifier_rows': missing_rows}
    if reference is None:
        return {**result, 'status': 'unavailable_static_file', 'unique_static_ids': None,
                'matched_ids': None, 'unmatched_ids': None, 'match_percent': None}
    matched = observed & reference
    unmatched = observed - reference
    return {**result, 'status': 'checked', 'unique_static_ids': len(reference),
            'matched_ids': len(matched), 'unmatched_ids': len(unmatched),
            'match_percent': round(100 * len(matched) / len(observed), 6) if observed else None,
            'matched_rows': sum(row_counts[value] for value in matched),
            'unmatched_rows': sum(row_counts[value] for value in unmatched),
            'unmatched_examples': sorted(unmatched)[:limit],
            'whitespace_only_match_candidates': sum(value.strip() in reference for value in unmatched if value != value.strip())}


def validate_gtfs_ids(static_directory, history_database, example_limit=10, static_archive=None):
    """Stream SQL-grouped history; memory holds unique IDs/pairs, not raw rows."""
    if example_limit < 0:
        raise ValueError('example_limit cannot be negative')
    path = Path(history_database).resolve(strict=True)
    before = path.stat()
    reference, trip_routes, pairs, provenance = load_static(static_directory, static_archive)
    union_ids = {field: set() for field in FIELDS}
    union_counts = {field: Counter() for field in FIELDS}
    union_missing = Counter()
    sources = {}
    # mode=ro refuses writes/creation; query_only adds a second write guard.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('PRAGMA temp_store=FILE')
        connection.execute('BEGIN')  # One consistent read snapshot, also for v2 backups.
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'trip_updates' not in tables and 'vehicle_positions' not in tables:
            raise ValueError('No historical realtime tables found')
        for table in ('vehicle_positions', 'trip_updates'):
            if table not in tables:
                sources[table] = {'status': 'missing_table'}
                continue
            columns = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
            fields = ('trip_id', 'route_id', 'stop_id') if table == 'trip_updates' else ('trip_id', 'route_id')
            if not set(fields).issubset(columns):
                raise ValueError(f'{table} is missing identifier columns')
            time_column = 'observed_at' if 'observed_at' in columns else 'timestamp'
            if time_column not in columns:
                raise ValueError(f'{table} has no supported observation timestamp')
            schema = 'v2' if table == 'trip_updates' and time_column == 'observed_at' else 'legacy_or_vehicle'
            observed = {field: set() for field in fields}
            counts = {field: Counter() for field in fields}
            missing, diagnostics, mappings, examples = Counter(), Counter(), Counter(), defaultdict(list)
            route_coverage = defaultdict(Counter)
            representative = {}
            total_rows, groups = 0, 0
            group_fields = ', '.join(fields)
            cursor = connection.execute(f'SELECT {group_fields}, COUNT(*) FROM {table} GROUP BY {group_fields}')
            for row in cursor:
                values, weight = dict(zip(fields, row[:-1])), row[-1]
                groups += 1
                total_rows += weight
                for field, value in values.items():
                    if value in (None, ''):
                        missing[field] += weight
                        continue
                    if not isinstance(value, str):
                        diagnostics[f'{field}_non_string_rows'] += weight
                    value = str(value)
                    values[field] = value
                    if value != value.strip():
                        diagnostics[f'{field}_whitespace_rows'] += weight
                    observed[field].add(value)
                    counts[field][value] += weight
                trip, route, stop = values.get('trip_id'), values.get('route_id'), values.get('stop_id')
                mapping_ok = False
                if reference['trip_id'] is not None:
                    if not trip or not route:
                        category = 'trip_route_missing_identifier'
                    elif trip not in trip_routes:
                        category = 'trip_route_trip_absent_in_static'
                    elif len(trip_routes[trip]) != 1:
                        category = 'trip_route_ambiguous_static'
                    elif route not in trip_routes[trip]:
                        category = 'trip_route_conflict'
                    else:
                        category = 'trip_route_consistent'
                        mapping_ok = True
                    mappings[category + '_groups'] += 1
                    mappings[category + '_rows'] += weight
                    if category != 'trip_route_consistent' and len(examples[category]) < example_limit:
                        examples[category].append({**values, 'rows': weight})
                if table == 'trip_updates' and pairs is not None:
                    if not trip or not stop:
                        category = 'trip_stop_missing_identifier'
                    elif reference['trip_id'] is not None and trip not in reference['trip_id']:
                        category = 'trip_stop_trip_absent_in_static'
                    elif reference['stop_id'] is not None and stop not in reference['stop_id']:
                        category = 'trip_stop_stop_absent_in_static'
                    elif (trip, stop) not in pairs:
                        category = 'trip_stop_pair_absent'
                    else:
                        category = 'trip_stop_compatible'
                    mappings[category + '_groups'] += 1
                    mappings[category + '_rows'] += weight
                    if category != 'trip_stop_compatible' and len(examples[category]) < example_limit:
                        examples[category].append({**values, 'rows': weight})
                    if route:
                        route_coverage[route]['historical_rows'] += weight
                        if mapping_ok and category == 'trip_stop_compatible' and reference['route_id'] is not None and route in reference['route_id']:
                            route_coverage[route]['fully_compatible_rows'] += weight
                            representative.setdefault(route, {'route_id': route, 'trip_id': trip, 'stop_id': stop})
            span = connection.execute(f'SELECT MIN({time_column}), MAX({time_column}) FROM {table}').fetchone()
            result = {'status': 'checked', 'physical_schema': schema, 'rows': total_rows,
                      'distinct_identifier_groups': groups, 'timestamp_column': time_column,
                      'observation_span': list(span), 'normalisation_diagnostics': dict(diagnostics),
                      'ids': {field: id_result(observed[field], reference[field], missing[field], counts[field], example_limit) for field in fields},
                      'mapping_status': {'trip_route': 'checked' if reference['trip_id'] is not None else 'unavailable',
                                         'trip_stop': ('not_applicable' if table == 'vehicle_positions' else
                                                      'checked' if pairs is not None and reference['trip_id'] is not None and reference['stop_id'] is not None else 'partial_or_unavailable')},
                      'mappings': dict(mappings), 'mapping_examples': dict(examples)}
            if table == 'trip_updates':
                result['demo_route_candidates'] = [
                    {**representative[route], **route_coverage[route]}
                    for route in sorted(representative, key=lambda key: (-route_coverage[key]['fully_compatible_rows'], key))[:example_limit]
                ]
            sources[table] = result
            for field in fields:
                union_ids[field].update(observed[field])
                union_counts[field].update(counts[field])
                union_missing[field] += missing[field]
        history_static_counts = {
            name: connection.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
            for name in ('routes', 'trips', 'stops', 'stop_times') if name in tables
        }
        connection.rollback()
    after = path.stat()
    unchanged = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    if not unchanged:
        raise RuntimeError('Historical source metadata changed during validation; use a stable backup')
    return {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'static': provenance,
            'history': {'path': str(path), 'bytes': before.st_size, 'mtime_ns': before.st_mtime_ns,
                        'open_mode': 'mode=ro; query_only=ON; consistent read transaction',
                        'source_metadata_unchanged': unchanged,
                        'static_reference_table_rows': history_static_counts},
            'combined_ids': {field: id_result(union_ids[field], reference[field], union_missing[field], union_counts[field], example_limit) for field in FIELDS},
            'sources': sources,
            'limitations': ['Percentages describe stored history, not raw live feeds.',
                            'Collector enrichment can exclude unmatched raw Trip Updates before storage.',
                            'ID membership does not prove calendar/service-date or shape compatibility.',
                            'Feed coverage dates do not prove exact production feed version.']}


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--static-dir', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--static-archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--example-limit', type=int, default=10)
    options = parser.parse_args(arguments)
    if options.output.suffix.lower() != '.json' or options.output.exists():
        parser.error('--output must be a new .json file; existing files are never overwritten')
    report = validate_gtfs_ids(options.static_dir, options.database, options.example_limit, options.static_archive)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    with options.output.open('x', encoding='utf8') as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print(json.dumps({'output': str(options.output), 'combined_ids': report['combined_ids']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
