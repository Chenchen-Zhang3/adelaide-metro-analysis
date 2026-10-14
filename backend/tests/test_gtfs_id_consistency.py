"""Focused read-only ID audit tests; no live feed or CASR database access."""

from contextlib import closing
import csv
import hashlib
import json
import sqlite3
import zipfile

import pytest

from backend.services import gtfs_id_consistency as audit


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def sources(tmp_path):
    static = tmp_path / 'static'
    static.mkdir()
    write_csv(static / 'routes.txt', ['route_id','route_short_name','route_long_name','route_type'], [
        {'route_id':'001A', 'route_short_name':'1A','route_long_name':'Test','route_type':3},
        {'route_id':'R2', 'route_short_name':'2','route_long_name':'Other','route_type':3},
    ])
    write_csv(static / 'trips.txt', ['trip_id','route_id','service_id'], [
        {'trip_id':'0007', 'route_id':'001A','service_id':'WK'},
        {'trip_id':'T2', 'route_id':'R2','service_id':'WK'},
    ])
    write_csv(static / 'stops.txt', ['stop_id','stop_name','stop_lat','stop_lon'], [
        {'stop_id':'0009', 'stop_name':'First','stop_lat':-34.9,'stop_lon':138.6},
        {'stop_id':'S2', 'stop_name':'Second','stop_lat':-34.9,'stop_lon':138.6},
    ])
    write_csv(static / 'stop_times.txt', ['trip_id','stop_id','stop_sequence','arrival_time','departure_time'], [
        {'trip_id':'0007','stop_id':'0009','stop_sequence':1,'arrival_time':'09:00:00','departure_time':'09:00:00'},
        {'trip_id':'T2','stop_id':'S2','stop_sequence':1,'arrival_time':'09:00:00','departure_time':'09:00:00'},
    ])
    write_csv(static / 'feed_info.txt', ['feed_publisher_name','feed_version','feed_start_date','feed_end_date'], [
        {'feed_publisher_name':'Fixture only','feed_version':'test','feed_start_date':'20260901','feed_end_date':'20260930'},
    ])
    database = tmp_path / 'legacy.db'
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript('''
            CREATE TABLE vehicle_positions(trip_id TEXT, route_id TEXT, timestamp TEXT);
            CREATE TABLE trip_updates(trip_id TEXT, route_id TEXT, stop_id TEXT, timestamp TEXT);
            INSERT INTO vehicle_positions VALUES ('0007','001A','2026-09-26T09:00:00+09:30');
            INSERT INTO trip_updates VALUES ('0007','001A','0009','2026-09-26T09:00:00+09:30');
        ''')
    return static, database


def add_rows(database, rows):
    with closing(sqlite3.connect(database)) as connection:
        connection.executemany('INSERT INTO trip_updates VALUES (?,?,?,?)', [(*row,'2026-09-26T09:01:00+09:30') for row in rows])
        connection.commit()


def test_exact_strings_and_shared_index_semantics_are_preserved(sources):
    static, database = sources
    report = audit.validate_gtfs_ids(static, database)
    for field in audit.FIELDS:
        assert report['combined_ids'][field]['match_percent'] == 100
        assert report['combined_ids'][field]['unique_realtime_ids'] == 1
    trip = report['sources']['trip_updates']
    assert trip['physical_schema'] == 'legacy_or_vehicle'
    assert trip['mappings']['trip_route_consistent_rows'] == 1
    assert trip['mappings']['trip_stop_compatible_rows'] == 1
    assert trip['demo_route_candidates'][0]['trip_id'] == '0007'
    assert trip['demo_route_candidates'][0]['stop_id'] == '0009'
    assert report['static']['files']['stop_times.txt']['unique_trip_stop_pairs'] == 2


def test_membership_and_relational_mismatches_are_separate_and_weighted(sources):
    static, database = sources
    add_rows(database, [('0007','R2','0009'), ('0007','R2','S2'),
                        ('T-new','X','missing'), ('T-new','X','missing')])
    report = audit.validate_gtfs_ids(static, database, example_limit=1)
    assert report['combined_ids']['route_id']['unique_realtime_ids'] == 3
    assert report['combined_ids']['route_id']['matched_ids'] == 2
    assert report['combined_ids']['trip_id']['unmatched_ids'] == 1
    assert report['combined_ids']['trip_id']['unmatched_rows'] == 2
    trip = report['sources']['trip_updates']
    assert trip['mappings']['trip_route_conflict_rows'] == 2
    assert trip['mappings']['trip_stop_pair_absent_rows'] == 1
    assert trip['mappings']['trip_stop_trip_absent_in_static_rows'] == 2
    assert len(trip['mapping_examples']['trip_route_conflict']) == 1
    assert trip['demo_route_candidates'][0]['fully_compatible_rows'] == 1


def test_unknown_stop_is_distinct_from_unknown_trip(sources):
    static, database = sources
    add_rows(database, [('0007','001A','absent')])
    report = audit.validate_gtfs_ids(static, database)
    assert report['sources']['trip_updates']['mappings']['trip_stop_stop_absent_in_static_rows'] == 1


def test_blank_ids_excluded_from_unique_denominator_and_whitespace_not_rewritten(sources):
    static, database = sources
    add_rows(database, [(None,None,None), ('','',''), ('0007 ','001A ','0009 ')])
    report = audit.validate_gtfs_ids(static, database)
    for field in audit.FIELDS:
        result = report['combined_ids'][field]
        assert result['missing_identifier_rows'] == 2
        assert result['unique_realtime_ids'] == 2
        assert result['match_percent'] == 50
        assert result['whitespace_only_match_candidates'] == 1


@pytest.mark.parametrize('filename,field', [('routes.txt','route_id'),('trips.txt','trip_id'),('stops.txt','stop_id')])
def test_partial_static_data_does_not_report_false_zero_match(sources, filename, field):
    static, database = sources
    (static / filename).unlink()
    report = audit.validate_gtfs_ids(static, database)
    assert report['combined_ids'][field]['status'] == 'unavailable_static_file'
    assert report['combined_ids'][field]['match_percent'] is None
    assert filename in report['static']['missing_files']


def test_missing_stop_times_leaves_id_checks_available(sources):
    static, database = sources
    (static / 'stop_times.txt').unlink()
    report = audit.validate_gtfs_ids(static, database)
    assert report['combined_ids']['stop_id']['match_percent'] == 100
    assert report['sources']['trip_updates']['mapping_status']['trip_stop'] == 'partial_or_unavailable'
    assert 'trip_stop_compatible_rows' not in report['sources']['trip_updates']['mappings']


def test_empty_history_has_no_misleading_match_percentage(sources):
    static, database = sources
    with closing(sqlite3.connect(database)) as connection:
        connection.execute('DELETE FROM vehicle_positions')
        connection.execute('DELETE FROM trip_updates')
        connection.commit()
    report = audit.validate_gtfs_ids(static, database)
    assert report['combined_ids']['route_id']['match_percent'] is None
    assert report['sources']['trip_updates']['rows'] == 0


def test_readonly_connection_and_source_bytes_are_preserved(sources, monkeypatch):
    static, database = sources
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    real_connect = sqlite3.connect
    def verify_readonly(database_uri, **kwargs):
        assert database_uri.endswith('?mode=ro') and kwargs['uri'] is True
        connection = real_connect(database_uri, **kwargs)
        with pytest.raises(sqlite3.OperationalError):
            connection.execute('DELETE FROM trip_updates')
        connection.rollback()  # The rejected DML still begins an implicit transaction.
        return connection
    monkeypatch.setattr(audit.sqlite3, 'connect', verify_readonly)
    report = audit.validate_gtfs_ids(static, database)
    assert report['history']['source_metadata_unchanged']
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_v2_integer_observation_schema_supported_without_repo_queries(sources):
    static, database = sources
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript('''
            CREATE TABLE v2(trip_id TEXT,route_id TEXT,stop_id TEXT,observed_at INTEGER);
            INSERT INTO v2 SELECT trip_id,route_id,stop_id,1780000000 FROM trip_updates;
            DROP TABLE trip_updates;
            ALTER TABLE v2 RENAME TO trip_updates;
        ''')
        connection.commit()
    report = audit.validate_gtfs_ids(static, database)
    assert report['sources']['trip_updates']['physical_schema'] == 'v2'
    assert report['sources']['trip_updates']['observation_span'] == [1780000000, 1780000000]
    assert report['sources']['vehicle_positions']['mapping_status']['trip_stop'] == 'not_applicable'
    assert report['combined_ids']['trip_id']['match_percent'] == 100


def test_archive_fingerprints_and_modified_local_file_are_reported(sources, tmp_path):
    static, database = sources
    archive = tmp_path / 'official-fixture.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        for path in static.iterdir():
            zipped.write(path, path.name)
    with (static / 'trips.txt').open('a', encoding='utf8') as output:
        output.write('\n')
    report = audit.validate_gtfs_ids(static, database, static_archive=archive)
    assert report['static']['archive_file_matches']['routes.txt'] is True
    assert report['static']['archive_file_matches']['trips.txt'] is False
    assert report['static']['feed_info'][0]['feed_version'] == 'test'


def test_conflicting_static_trip_mapping_is_not_a_demo_candidate(sources):
    static, database = sources
    with (static / 'trips.txt').open('a', encoding='utf8') as output:
        output.write('0007,R2,WK\n')
    report = audit.validate_gtfs_ids(static, database)
    assert report['static']['diagnostics']['conflicting_trip_route_keys'] == 1
    assert report['sources']['trip_updates']['mappings']['trip_route_ambiguous_static_rows'] == 1
    assert not report['sources']['trip_updates']['demo_route_candidates']


def test_output_cannot_overwrite_database_or_existing_evidence(sources, tmp_path):
    static, database = sources
    for output in (database, tmp_path / 'existing.json'):
        if output.suffix == '.json':
            output.write_text('existing evidence', encoding='utf8')
        with pytest.raises(SystemExit):
            audit.main(['--static-dir',str(static),'--database',str(database),'--output',str(output)])


def test_cli_writes_small_reusable_summary(sources, tmp_path):
    static, database = sources
    output = tmp_path / 'report.json'
    assert audit.main(['--static-dir',str(static),'--database',str(database),'--output',str(output)]) == 0
    assert json.loads(output.read_text(encoding='utf8'))['combined_ids']['trip_id']['matched_ids'] == 1


def test_missing_source_is_not_created(sources, tmp_path):
    static, _ = sources
    missing = tmp_path / 'absent.db'
    with pytest.raises(FileNotFoundError):
        audit.validate_gtfs_ids(static, missing)
    assert not missing.exists()
