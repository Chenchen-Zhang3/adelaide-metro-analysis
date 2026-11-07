"""PR04 stop-level metrics: strict dates, stop-specific timetable and predictions."""
from datetime import datetime
import sqlite3
from zoneinfo import ZoneInfo

import pytest

from backend.services import nearest_stop_metrics as metrics

TZ = ZoneInfo('Australia/Adelaide')
START = datetime(2026, 10, 22, 13, 0, tzinfo=TZ)
END = datetime(2026, 10, 22, 14, 0, tzinfo=TZ)


def test_scheduled_counts_selected_stop_not_route_origin(monkeypatch, tmp_path):
    (tmp_path / 'calendars.json').write_text('{}')
    monkeypatch.setattr(metrics.static_map_data, 'configured', lambda: True)
    monkeypatch.setattr(metrics.static_map_data, '_manifest', lambda: (tmp_path, {'calendars': {}}))
    monkeypatch.setattr(metrics.static_map_data, '_verified_json', lambda *args: {
        'calendar.txt': [{'service_id': 'S1', 'start_date': '20260101',
                          'end_date': '20261231', 'thursday': '1'}],
        'calendar_dates.txt': []})
    monkeypatch.setattr(metrics.static_map_data, 'load_catalog', lambda: {
        'stops': [{'stop_id': 'TARGET', 'route_ids': ['G10']}]})
    monkeypatch.setattr(metrics.static_map_data, 'load_static_route_map_data', lambda route: {
        'trips': [
            {'trip_id': 'T1', 'service_id': 'S1', 'stops': [
                {'stop_id': 'ORIGIN', 'departure_time': '12:50:00'},
                {'stop_id': 'TARGET', 'departure_time': '13:15:00'}]},
            {'trip_id': 'T2', 'service_id': 'S1', 'stops': [
                {'stop_id': 'ORIGIN', 'departure_time': '13:05:00'},
                {'stop_id': 'TARGET', 'departure_time': '14:05:00'}]},
            {'trip_id': 'T3', 'service_id': 'OTHER', 'stops': [
                {'stop_id': 'TARGET', 'departure_time': '13:30:00'}]},
        ]})
    result = metrics._scheduled('TARGET', START, END)
    assert result['scheduled_departures'] == 1
    assert result['scheduled_trips_per_hour'] == 1.0


def test_reliability_filters_stop_and_requires_samples(monkeypatch, tmp_path):
    db = tmp_path / 'history.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE trip_updates (trip_id TEXT, stop_id TEXT, delay_seconds REAL, observed_at INTEGER)')
        t = int(START.timestamp())
        conn.executemany('INSERT INTO trip_updates VALUES (?, ?, ?, ?)', [
            ('T1', 'TARGET', 120, t), ('T1', 'TARGET', 400, t + 30),
            ('T2', 'OTHER', 120, t + 30), ('T3', 'TARGET', 0, t - 30),
        ])
    monkeypatch.setenv('ADELAIDE_METRO_DATABASE_PATH', str(db))
    result = metrics._reliability('TARGET', START, END, 2)
    assert result['observation_count'] == 2
    assert result['unique_observed_trips'] == 1
    assert result['predicted_on_time_percent'] == 50.0
    assert metrics._reliability('TARGET', START, END, 3)['status'] == 'insufficient_data'


def test_rejects_invalid_windows():
    with pytest.raises(ValueError):
        metrics.stop_metrics('TARGET', END, START)
    with pytest.raises(ValueError):
        metrics.stop_metrics('TARGET', START, END, 0)


def test_api_rejects_missing_time():
    from backend.api.app import app
    response = app.test_client().get('/api/stops/TARGET/service-metrics')
    assert response.status_code == 400
