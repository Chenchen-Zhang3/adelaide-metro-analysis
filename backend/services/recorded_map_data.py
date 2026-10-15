"""Official static route geometry and recorded-demo map handover, without DB writes."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from backend.services.gtfs_id_consistency import fingerprint
from backend.services.recorded_demo import LABEL, load_inputs, valid_coordinates, verify_archive


MAP_DATA_ENV = 'ADELAIDE_METRO_DEMO_MAP_DATA_PATH'
PAYLOAD_FILES = ('route-shapes.geojson', 'stops.geojson', 'trip-map.json')


class MapDataUnavailableError(RuntimeError):
    """Map artifacts are missing, inconsistent or unconfigured."""


def extract_shapes(path, requested):
    """Stream only selected official shapes; retain repeated coordinates."""
    points = defaultdict(list)
    with Path(path).open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        fields = {'shape_id','shape_pt_lat','shape_pt_lon','shape_pt_sequence'}
        if not fields.issubset(reader.fieldnames or []):
            raise ValueError('shapes.txt is missing required columns')
        for row in reader:
            if row['shape_id'] not in requested:
                continue
            lat, lon = float(row['shape_pt_lat']), float(row['shape_pt_lon'])
            sequence = int(row['shape_pt_sequence'])
            if not valid_coordinates(lat,lon) or sequence < 0:
                raise ValueError(f'Invalid shape coordinate/sequence for {row["shape_id"]}')
            points[row['shape_id']].append((sequence,lon,lat))
    result, diagnostics = {}, {}
    for shape in sorted(requested):
        ordered = sorted(points[shape])
        if len(ordered) < 2:
            raise ValueError(f'Missing/insufficient official shape points: {shape}')
        if len({point[0] for point in ordered}) != len(ordered):
            raise ValueError(f'Ambiguous duplicated shape_pt_sequence: {shape}')
        coordinates = [[lon,lat] for sequence,lon,lat in ordered]
        if len({tuple(point) for point in coordinates}) < 2:
            raise ValueError(f'Degenerate official shape: {shape}')
        result[shape] = {'coordinates':coordinates, 'sequences':[row[0] for row in ordered]}
        diagnostics[shape] = {
            'point_count':len(ordered),
            'repeated_coordinate_count':len(coordinates)-len({tuple(point) for point in coordinates}),
            'adjacent_duplicate_count':sum(a == b for a,b in zip(coordinates,coordinates[1:])),
            'outside_broad_adelaide_bounds':sum(not (-36 <= lat <= -33 and 137 <= lon <= 140) for lon,lat in coordinates),
        }
    return result, diagnostics


def feature_collection(features):
    return {'type':'FeatureCollection','features':features}


def build_map_data(demo_db, demo_manifest, static_dir, archive, output):
    """Read pinned demo/static inputs and atomically publish a new artifact folder."""
    demo_db, output = Path(demo_db).resolve(strict=True), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Use a new map-data directory; existing artifacts are never overwritten')
    with Path(demo_manifest).open(encoding='utf8') as file:
        recorded = json.load(file)
    config = recorded['config']
    if recorded['label'] != LABEL or set(config['route_ids']) != {'G10','M44','506'}:
        raise ValueError('Expected the SCRUM-233 recorded three-route demo manifest')
    demo_fingerprint = fingerprint(demo_db)
    if demo_fingerprint['sha256'] != recorded['output_database']['sha256']:
        raise ValueError('Demo database hash differs from its manifest')
    before = demo_db.stat().st_mtime_ns
    routes, static_trips, static_stops, static_metadata = load_inputs(static_dir,config)
    verify_archive(static_dir,archive,config,static_metadata)
    shapes_path = Path(static_dir) / 'shapes.txt'
    shape_file = fingerprint(shapes_path)
    with zipfile.ZipFile(archive) as zipped, zipped.open('shapes.txt') as file:
        if hashlib.file_digest(file,'sha256').hexdigest() != shape_file['sha256']:
            raise ValueError('shapes.txt differs from the pinned official archive')
    with closing(sqlite3.connect(demo_db.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        if db.execute("SELECT value FROM schema_metadata WHERE name='historical_storage_version'").fetchone()[0] != '2':
            raise ValueError('Expected the v2 demo database')
        trips = {row['trip_id']:dict(row) for row in db.execute('SELECT * FROM trips ORDER BY trip_id')}
        stops = {row['stop_id']:dict(row) for row in db.execute('SELECT * FROM stops ORDER BY stop_id')}
        selected_routes = {row['route_id']:dict(row) for row in db.execute('SELECT * FROM routes ORDER BY route_id')}
        if set(trips) != set(recorded['selected_trip_ids']) or set(stops) != set(recorded['selected_stop_ids']) or set(selected_routes) != set(config['route_ids']):
            raise ValueError('Demo dimension IDs differ from the manifest')
        historical_pairs = {(row[0],row[1]) for row in db.execute('SELECT DISTINCT trip_id,route_id FROM vehicle_positions UNION SELECT DISTINCT trip_id,route_id FROM trip_updates')}
        if historical_pairs != {(trip,row['route_id']) for trip,row in trips.items()}:
            raise ValueError('Recorded trip/route IDs differ from demo dimensions')
        stop_times = [dict(row) for row in db.execute('SELECT trip_id,stop_id,stop_sequence FROM stop_times ORDER BY trip_id,stop_sequence,stop_id')]
    trip_stops = defaultdict(list)
    stop_routes, stop_trips, shape_trips = defaultdict(set), defaultdict(set), defaultdict(list)
    trip_map = []
    for row in stop_times:
        if row['trip_id'] not in trips or row['stop_id'] not in stops:
            raise ValueError('Orphan demo trip/stop relationship')
        trip_stops[row['trip_id']].append({'stop_id':row['stop_id'],'stop_sequence':row['stop_sequence']})
        stop_routes[row['stop_id']].add(trips[row['trip_id']]['route_id'])
        stop_trips[row['stop_id']].add(row['trip_id'])
    if set(stop_trips) != set(stops):
        raise ValueError('Demo stops must belong to selected trip stop_times')
    for trip, row in trips.items():
        official = static_trips.get(trip)
        if official is None or official['route_id'] != row['route_id']:
            raise ValueError(f'Official trip/route mismatch: {trip}')
        shape = official.get('shape_id')
        if not shape:
            raise ValueError(f'Demo trip has no official shape_id: {trip}')
        if not trip_stops[trip]:
            raise ValueError(f'Demo trip has no ordered stop relationships: {trip}')
        shape_trips[(row['route_id'],shape)].append(trip)
        trip_map.append({'trip_id':trip,'route_id':row['route_id'],'shape_id':shape,
                         'direction_id':official.get('direction_id'), 'stops':trip_stops[trip]})
    shape_ids = {shape for route,shape in shape_trips}
    points, diagnostics = extract_shapes(shapes_path,shape_ids)
    geometry_features = []
    for (route,shape), trip_ids in sorted(shape_trips.items()):
        feature = {'type':'Feature','id':f'{route}:{shape}',
                   'properties':{**selected_routes[route], 'shape_id':shape,
                                 'trip_ids':sorted(trip_ids),
                                 'direction_ids':sorted({static_trips[trip]['direction_id'] for trip in trip_ids if static_trips[trip].get('direction_id') is not None}),
                                 'shape_pt_sequences':points[shape]['sequences']},
                   'geometry':{'type':'LineString','coordinates':points[shape]['coordinates']}}
        geometry_features.append(feature)
    stop_features = []
    for stop, row in stops.items():
        official = static_stops.get(stop)
        if official is None or any(row[key] != official[key] for key in ('stop_name','stop_lat','stop_lon')):
            raise ValueError(f'Official stop mismatch: {stop}')
        if not valid_coordinates(row['stop_lat'],row['stop_lon']):
            raise ValueError(f'Invalid stop coordinates: {stop}')
        stop_features.append({'type':'Feature','id':stop,
                              'properties':{**row,'route_ids':sorted(stop_routes[stop]),'trip_ids':sorted(stop_trips[stop])},
                              'geometry':{'type':'Point','coordinates':[row['stop_lon'],row['stop_lat']]}})
    payloads = {'route-shapes.geojson':feature_collection(geometry_features),
                'stops.geojson':feature_collection(stop_features),
                'trip-map.json':{'label':LABEL,'static_feed_version':config['static_feed_version'],'trips':trip_map}}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='map-data-',dir=output.parent) as temporary:
        staging = Path(temporary) / 'published'
        staging.mkdir()
        for name,payload in payloads.items():
            with (staging/name).open('w',encoding='utf8') as file:
                json.dump(payload,file,ensure_ascii=False,separators=(',',':'),allow_nan=False)
                file.write('\n')
        manifest = {'label':LABEL,'static_feed_version':config['static_feed_version'],
                    'observation_window':{'start':config['start'],'end_exclusive':config['end_exclusive']},
                    'demo_database':demo_fingerprint,'static':static_metadata,
                    'files':{name:fingerprint(staging/name) for name in PAYLOAD_FILES},
                    'route_ids':sorted(selected_routes),'trip_count':len(trips),'stop_count':len(stops),
                    'shape_count':len(shape_ids),'feature_count':len(geometry_features),
                    'shapes':diagnostics,'route_shapes':{route:sorted(shape for route_key,shape in shape_trips if route_key==route) for route in sorted(selected_routes)},
                    'route_stop_counts':{route:sum(route in routes_for_stop for routes_for_stop in stop_routes.values()) for route in sorted(selected_routes)},
                    'coordinate_order':'GeoJSON [longitude, latitude]; use L.geoJSON directly',
                    'limitations':['Official full selected-trip shapes, not a time-clipped vehicle trajectory.',
                                   'Repeated coordinates are preserved, not silently deduplicated.',
                                   'Browser integration and playback are not claimed complete.']}
        with (staging/'manifest.json').open('w',encoding='utf8') as file:
            json.dump(manifest,file,ensure_ascii=False,indent=2)
            file.write('\n')
        if fingerprint(demo_db)['sha256'] != demo_fingerprint['sha256'] or demo_db.stat().st_mtime_ns != before:
            raise RuntimeError('Demo database changed during map extraction')
        staging.rename(output)
    return manifest


def load_route_map_data(route_id, directory=None):
    """Serve verified artifacts only; never create or write to any database."""
    configured = directory if directory is not None else os.environ.get(MAP_DATA_ENV)
    if not configured:
        raise MapDataUnavailableError('Recorded demo map-data directory is not configured')
    folder = Path(configured)
    try:
        with (folder/'manifest.json').open(encoding='utf8') as file:
            manifest = json.load(file)
        if manifest['label'] != LABEL:
            raise ValueError('Incorrect recorded-data label')
        if route_id not in manifest['route_ids']:
            return None
        payloads = {}
        for name in PAYLOAD_FILES:
            if fingerprint(folder/name)['sha256'] != manifest['files'][name]['sha256']:
                raise ValueError('Map-data file hash mismatch')
            with (folder/name).open(encoding='utf8') as file:
                payloads[name] = json.load(file)
        geometry = [feature for feature in payloads['route-shapes.geojson']['features'] if feature['properties']['route_id']==route_id]
        stops = [feature for feature in payloads['stops.geojson']['features'] if route_id in feature['properties']['route_ids']]
        trips = [trip for trip in payloads['trip-map.json']['trips'] if trip['route_id']==route_id]
        if not geometry or not stops or not trips:
            raise ValueError('Incomplete recorded route map data')
        return {'label':LABEL,'static_feed_version':manifest['static_feed_version'],
                'observation_window':manifest['observation_window'], 'route_id':route_id,
                'geometry':feature_collection(geometry),'stops':feature_collection(stops),'trips':trips}
    except (OSError,ValueError,KeyError,TypeError) as error:
        raise MapDataUnavailableError('Recorded demo map-data artifacts are missing or inconsistent; regenerate them') from error


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('demo-db','demo-manifest','static-dir','static-archive','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    options = parser.parse_args(arguments)
    report = build_map_data(options.demo_db,options.demo_manifest,options.static_dir,options.static_archive,options.output)
    print(json.dumps({key:report[key] for key in ('route_shapes','shape_count','shapes','stop_count','route_stop_counts','files')},indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
