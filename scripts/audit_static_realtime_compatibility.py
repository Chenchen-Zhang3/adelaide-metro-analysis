"""Replay a saved Trip Updates protobuf against an official static ZIP, offline.

No feed requests or database writes. Output counts separate structural matches,
arrival eligibility and actual existing collector conversion.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.realtime.collector import GTFSRealtimeCollector
from backend.realtime.decoder import decode_feed
from backend.realtime.validation import is_valid_trip_update, is_valid_stop_time_update
from backend.services.gtfs_converter import build_stop_time_index, convert_trip_update


def audit(static_zip, snapshot):
    static_zip, snapshot = Path(static_zip), Path(snapshot)
    with zipfile.ZipFile(static_zip) as archive:
        def rows(name):
            return list(csv.DictReader(io.StringIO(archive.read(name).decode('utf-8-sig')))) if name in archive.namelist() else []
        stop_times = rows('stop_times.txt')
        trips = {row['trip_id']: row for row in rows('trips.txt')}
        info = rows('feed_info.txt')
        calendars = {row['service_id']: row for row in rows('calendar.txt')}
        exceptions = {(row['service_id'], row['date']): row['exception_type'] for row in rows('calendar_dates.txt')}
        stop_hash = hashlib.sha256(archive.read('stop_times.txt')).hexdigest()
    index = build_stop_time_index(stop_times)
    by_pair, by_trip = defaultdict(list), defaultdict(list)
    for row in stop_times:
        by_pair[row['trip_id'], row['stop_id']].append(row)
        by_trip[row['trip_id']].append(row)
    ordinals = defaultdict(list)
    for trip_id, pattern in by_trip.items():
        pattern.sort(key=lambda row:int(row['stop_sequence']))
        for position, row in enumerate(pattern, 1):
            ordinals[trip_id, row['stop_id']].append(position)
    all_stops = {row['stop_id'] for row in stop_times}
    raw = snapshot.read_bytes()
    feed = decode_feed(raw)
    counts, valid_categories, offsets, routes, services = Counter(), Counter(), Counter(), defaultdict(Counter), Counter()
    mismatches, matched_examples, affected = [], [], {}
    for entity in feed.entity:
        if not entity.HasField('trip_update'):
            continue
        update = entity.trip_update
        trip_id, route, date = update.trip.trip_id, update.trip.route_id, update.trip.start_date
        counts['trip_entities'] += 1
        services[date] += 1
        active = None
        trip = trips.get(trip_id, {})
        service = trip.get('service_id')
        if service and date:
            exception = exceptions.get((service, date))
            if exception:
                active = exception == '1'
            elif service in calendars:
                cal = calendars[service]
                day = datetime.strptime(date, '%Y%m%d').strftime('%A').lower()
                active = cal['start_date'] <= date <= cal['end_date'] and cal[day] == '1'
        counts['active_service_trip_entities' if active else 'inactive_or_unknown_service_trip_entities'] += 1
        if trip and trip.get('route_id') != route:
            counts['route_disagreement'] += 1
        entity_valid = is_valid_trip_update(entity)
        if not entity_valid:
            counts['invalid_trip_entities'] += 1
        entity_categories = Counter()
        for stop in update.stop_time_update:
            counts['stop_entries'] += 1
            key = (trip_id, stop.stop_id, int(stop.stop_sequence))
            candidates = by_pair[trip_id, stop.stop_id]
            if key in index:
                category = 'exact'
            elif trip_id not in by_trip:
                category = 'missing_trip'
            elif stop.stop_id not in all_stops:
                category = 'missing_stop'
            elif not candidates:
                category = 'missing_trip_stop_pair'
            elif len(candidates) > 1:
                category = 'ambiguous_pair_sequence_mismatch'
            else:
                category = 'unique_pair_sequence_mismatch'
            counts[category] += 1
            if len(candidates) > 1:
                counts['repeated_stop_pair_entries'] += 1
            valid = entity_valid and is_valid_stop_time_update(stop)
            if valid:
                valid_categories[category] += 1
            else:
                counts['invalid_before_static_lookup'] += 1
                if not stop.HasField('arrival') or not stop.arrival.HasField('time'):
                    counts['missing_arrival_time'] += 1
            entity_categories[category] += 1
            routes[route][category] += 1
            if category == 'unique_pair_sequence_mismatch':
                offsets[int(candidates[0]['stop_sequence']) - stop.stop_sequence] += 1
                if ordinals[trip_id, stop.stop_id] == [stop.stop_sequence]:
                    counts['mismatch_equals_dense_static_ordinal'] += 1
            example = {
                'trip_id': trip_id, 'route_id': route, 'stop_id': stop.stop_id,
                'realtime_sequence': stop.stop_sequence,
                'static_sequences': [int(r['stop_sequence']) for r in candidates],
                'static_arrivals': [r['arrival_time'] for r in candidates],
                'static_ordinals': ordinals[trip_id, stop.stop_id],
                'service_date': date, 'start_time': update.trip.start_time,
                'shape_id': trip.get('shape_id'), 'service_id': service, 'service_active': active,
                'trip_relationship': int(update.trip.schedule_relationship),
                'stop_relationship': int(stop.schedule_relationship),
                'arrival_time': stop.arrival.time if stop.HasField('arrival') and stop.arrival.HasField('time') else None,
                'arrival_delay': stop.arrival.delay if stop.HasField('arrival') and stop.arrival.HasField('delay') else None,
                'category': category, 'eligible_before_lookup': valid,
                'current_action': 'keep' if valid and category == 'exact' else 'skip',
            }
            if category != 'exact':
                mismatches.append(example)
            elif len(matched_examples) < 4:
                matched_examples.append(example)
        if set(entity_categories) != {'exact'}:
            affected[trip_id] = {'counts': dict(entity_categories), 'trip': trip,
                                 'static_pattern': [{'stop_id':r['stop_id'], 'sequence':r['stop_sequence'], 'arrival':r['arrival_time']}
                                                    for r in by_trip[trip_id]],
                                 'realtime_pattern': [{'stop_id':s.stop_id, 'sequence':s.stop_sequence,
                                                       'arrival':s.arrival.time if s.HasField('arrival') and s.arrival.HasField('time') else None}
                                                      for s in update.stop_time_update]}
    converted = GTFSRealtimeCollector(stop_time_index=index)._convert_trip_updates(feed)
    direct = []
    for entity in feed.entity:
        if is_valid_trip_update(entity):
            direct.extend(convert_trip_update(entity, index))
    counts['direct_converted_records'] = len(direct)
    counts['collector_database_ready_records'] = len(converted)
    counts['eligible_before_lookup'] = sum(valid_categories.values())
    counts['valid_mapping_skips'] = sum(v for k,v in valid_categories.items() if k != 'exact')
    counts['unique_trips'] = len({e.trip_update.trip.trip_id for e in feed.entity if e.HasField('trip_update')})
    original_example = [dict(r, ordinal=ordinals[r['trip_id'], r['stop_id']])
                        for r in by_pair['1180165', '417']]
    return {
        'static': {'feed_info':info, 'archive_sha256':hashlib.sha256(static_zip.read_bytes()).hexdigest(),
                   'stop_times_sha256':stop_hash, 'rows':len(stop_times), 'index_keys':len(index),
                   'duplicate_index_keys':len(stop_times)-len(index),
                   'repeated_trip_stop_pairs':sum(len(rs)>1 for rs in by_pair.values())},
        'realtime': {'snapshot_sha256':hashlib.sha256(raw).hexdigest(),
                     'header_timestamp':feed.header.timestamp,
                     'header_utc':datetime.fromtimestamp(feed.header.timestamp, timezone.utc).isoformat(),
                     'gtfs_realtime_version':feed.header.gtfs_realtime_version,
                     'header_fields':str(feed.header), 'service_dates':dict(services)},
        'counts': dict(counts), 'eligible_categories':dict(valid_categories),
        'static_minus_realtime_sequence_offsets':dict(offsets),
        'routes':{r:dict(c) for r,c in routes.items()},
        'matched_examples': matched_examples, 'mismatches': mismatches,
        'original_report_static_example': {'trip':trips.get('1180165'), 'stop_times':original_example},
        'affected_trip_patterns': affected,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--static-zip', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = audit(args.static_zip, args.snapshot)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('mismatches','affected_trip_patterns','routes')}, indent=2))
