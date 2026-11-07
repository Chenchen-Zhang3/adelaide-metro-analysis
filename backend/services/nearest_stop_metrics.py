"""Stop-level scheduled GTFS frequency and historical prediction observations."""

from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from backend.services import static_map_data

ADELAIDE = ZoneInfo('Australia/Adelaide')


def _active_services(calendars, day):
    target = day.strftime('%Y%m%d')
    weekday = day.strftime('%A').lower()
    active = {r['service_id'] for r in calendars.get('calendar.txt', [])
              if r['start_date'] <= target <= r['end_date'] and r.get(weekday) == '1'}
    for row in calendars.get('calendar_dates.txt', []):
        if row['date'] == target:
            if row['exception_type'] == '1':
                active.add(row['service_id'])
            elif row['exception_type'] == '2':
                active.discard(row['service_id'])
    return active


def _gtfs_seconds(value):
    parts = value.split(':')
    if len(parts) != 3:
        raise ValueError('Invalid GTFS departure time')
    hours, minutes, seconds = map(int, parts)
    if not (0 <= minutes < 60 and 0 <= seconds < 60 and 0 <= hours <= 47):
        raise ValueError('Invalid GTFS departure time')
    return hours * 3600 + minutes * 60 + seconds


def _scheduled(stop_id, start, end):
    if not static_map_data.configured():
        return {'status': 'unavailable', 'reason': 'Static GTFS publication not configured'}
    local_start, local_end = start.astimezone(ADELAIDE), end.astimezone(ADELAIDE)
    if local_start.date() != local_end.date():
        return {'status': 'unavailable', 'reason': 'Select a window within one Adelaide calendar day'}
    folder, manifest = static_map_data._manifest()
    catalog = static_map_data.load_catalog()
    stop = next((s for s in catalog['stops'] if str(s['stop_id']) == stop_id), None)
    if stop is None:
        return {'status': 'unknown_stop', 'reason': 'Stop is not in the published static network'}
    calendars = static_map_data._verified_json(folder / 'calendars.json', manifest['calendars'])
    active = _active_services(calendars, local_start.date())
    if not active:
        return {'status': 'unavailable', 'reason': 'No active timetable services on this date; feed coverage may be missing'}
    lo = local_start.hour * 3600 + local_start.minute * 60 + local_start.second
    hi = local_end.hour * 3600 + local_end.minute * 60 + local_end.second
    if hi <= lo:
        return {'status': 'unavailable', 'reason': 'Unsupported cross-midnight or DST transition window'}
    departures = set()
    for route_id in stop.get('route_ids', []):
        payload = static_map_data.load_static_route_map_data(route_id)
        if payload is None:
            continue
        for trip in payload['trips']:
            if trip.get('service_id') not in active:
                continue
            for visit in trip.get('stops', []):
                if str(visit.get('stop_id')) != stop_id:
                    continue
                time = visit.get('departure_time') or visit.get('arrival_time')
                if time and lo <= _gtfs_seconds(time) < hi:
                    departures.add(trip['trip_id'])
                break
    hours = (end - start).total_seconds() / 3600
    return {'status': 'available', 'scheduled_departures': len(departures),
            'scheduled_trips_per_hour': round(len(departures) / hours, 2),
            'source': 'static_gtfs', 'service_date': str(local_start.date())}


def _reliability(stop_id, start, end, min_samples):
    path = os.environ.get('ADELAIDE_METRO_DATABASE_PATH')
    if not path or not Path(path).is_file():
        return {'status': 'unavailable', 'reason': 'Historical database not configured'}
    # A read-only connection prevents accidental writes to the research snapshot.
    with sqlite3.connect(f'file:{Path(path).resolve()}?mode=ro', uri=True) as conn:
        rows = conn.execute('''SELECT trip_id, delay_seconds FROM trip_updates
                               WHERE stop_id = ? AND observed_at >= ? AND observed_at < ?''',
                            (stop_id, int(start.timestamp()), int(end.timestamp()))).fetchall()
    delays = [float(delay) for _, delay in rows if delay is not None]
    result = {'status': 'insufficient_data' if len(delays) < min_samples else 'available',
              'observation_count': len(delays), 'total_records': len(rows),
              'unique_observed_trips': len({trip for trip, _ in rows if trip is not None}),
              'min_samples': min_samples, 'source': 'gtfs_realtime_trip_update_predictions',
              'note': 'Rates count retained prediction observations, not completed arrivals.'}
    if len(delays) >= min_samples:
        result['predicted_on_time_percent'] = round(100 * sum(0 <= d <= 300 for d in delays) / len(delays), 2)
        result['average_predicted_delay_minutes'] = round(sum(delays) / len(delays) / 60, 2)
    return result


def stop_metrics(stop_id, start, end, min_samples=10):
    if not stop_id or len(stop_id) > 128:
        raise ValueError('Invalid stop ID')
    if start.tzinfo is None or end.tzinfo is None or not start < end:
        raise ValueError('Provide increasing offset-aware start_time and end_time')
    if (end - start).total_seconds() > 86400:
        raise ValueError('Maximum analysis window is 24 hours')
    if not isinstance(min_samples, int) or not 1 <= min_samples <= 1000:
        raise ValueError('min_samples must be between 1 and 1000')
    try:
        scheduled = _scheduled(stop_id, start, end)
    except (OSError, ValueError, KeyError, TypeError, static_map_data.MapDataUnavailableError):
        scheduled = {'status': 'unavailable', 'reason': 'Static GTFS data missing or inconsistent'}
    try:
        reliability = _reliability(stop_id, start, end, min_samples)
    except sqlite3.Error:
        reliability = {'status': 'unavailable', 'reason': 'Historical observations unavailable'}
    return {'stop_id': stop_id, 'start_time': start.isoformat(), 'end_time': end.isoformat(),
            'scheduled_frequency': scheduled, 'historical_prediction_reliability': reliability}
