"""Publish a pinned static GTFS network separately from recorded observations."""

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

from backend.parsers.static_gtfs import parse_routes, parse_stops, parse_trips
from backend.services.gtfs_id_consistency import fingerprint
from backend.services.recorded_demo import valid_coordinates
from backend.services.recorded_map_data import (
    MapDataUnavailableError, extract_shapes, feature_collection,
)

MAP_DATA_ENV = "ADELAIDE_METRO_STATIC_MAP_DATA_PATH"
LABEL = "Static GTFS Network — no historical observations included"
SOURCE_FILES = ("agency.txt", "feed_info.txt", "routes.txt", "stops.txt",
                "trips.txt", "stop_times.txt", "shapes.txt", "calendar.txt",
                "calendar_dates.txt")


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def indexed(records, key):
    result = {}
    for row in records:
        value = row[key]
        if not value or value in result:
            raise ValueError(f"Blank or duplicate {key}: {value}")
        result[value] = row
    return result


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False) + "\n",
                    encoding="utf8")
    return fingerprint(path)


def build_static_map_data(archive, output, *, expected_sha256, version,
                          agency_ids, route_types=(3,), route_ids=None):
    """Verify a pinned ZIP, then atomically publish to a NEW folder; no DB access.

    Shapes are streamed once. Stop-times are streamed and retained only for
    selected trips. IDs are never converted to numbers or used as file paths.
    Payload bytes are deterministic; generation time belongs only to manifest.
    """
    archive, output = Path(archive), Path(output)
    if output.exists():
        raise FileExistsError("Use a new static map directory; never overwrite artifacts")
    source = fingerprint(archive)
    if source["sha256"] != expected_sha256:
        raise ValueError("Static archive SHA-256 differs from the pinned source")
    agency_ids, route_types = set(agency_ids), set(route_types)
    if not agency_ids or not route_types:
        raise ValueError("Explicit agency and route-type selection is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="static-map-", dir=output.parent) as temporary:
        folder = Path(temporary)
        static = folder / "source"
        static.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            for name in SOURCE_FILES:
                # Whitelisted names only: no ZIP paths are trusted or extracted.
                if zipped.namelist().count(name) != 1:
                    raise ValueError(f"Missing or duplicated archive entry: {name}")
                with zipped.open(name) as src, (static / name).open("wb") as dst:
                    while block := src.read(1024 * 1024):
                        dst.write(block)
        feed = list(rows(static / "feed_info.txt"))
        if len(feed) != 1 or feed[0].get("feed_version") != version:
            raise ValueError("Unexpected static feed version")
        agencies = indexed(rows(static / "agency.txt"), "agency_id")
        if not agency_ids <= agencies.keys():
            raise ValueError("Unknown selected agency")
        all_routes = indexed(parse_routes(static / "routes.txt"), "route_id")
        routes = {key: row for key, row in all_routes.items()
                  if row.get("agency_id") in agency_ids and row["route_type"] in route_types}
        if route_ids is not None:
            if not set(route_ids) <= routes.keys():
                raise ValueError("Requested route is outside selection policy")
            routes = {key: row for key, row in routes.items() if key in route_ids}
        if not routes:
            raise ValueError("Empty static route selection")
        all_trips = indexed(parse_trips(static / "trips.txt"), "trip_id")
        if any(row["route_id"] not in all_routes for row in all_trips.values()):
            raise ValueError("Unknown trip route reference")
        trips = {key: row for key, row in all_trips.items() if row["route_id"] in routes}
        services = {r["service_id"] for name in ("calendar.txt", "calendar_dates.txt")
                    for r in rows(static / name)}
        if any(row["service_id"] not in services for row in trips.values()):
            raise ValueError("Unknown trip service reference")
        stops = indexed(parse_stops(static / "stops.txt"), "stop_id")
        visits, stop_routes, stop_trips = defaultdict(list), defaultdict(set), defaultdict(set)
        keys = set()
        for row in rows(static / "stop_times.txt"):
            trip = row["trip_id"]
            if trip not in all_trips:
                raise ValueError("Unknown stop-time trip reference")
            if trip not in trips:
                continue
            stop, seq = row["stop_id"], int(row["stop_sequence"])
            if stop not in stops or seq < 0 or (trip, seq) in keys:
                raise ValueError("Missing stop or invalid/duplicate trip stop_sequence")
            keys.add((trip, seq))
            row["stop_sequence"] = seq
            visits[trip].append(row)
            stop_routes[stop].add(trips[trip]["route_id"])
            stop_trips[stop].add(trip)
        if set(visits) != set(trips) or {t["route_id"] for t in trips.values()} != set(routes):
            raise ValueError("Selected route/trip has no stop-time relationships")
        referenced_stops = set(stop_routes)
        for stop in sorted(referenced_stops):
            if int(stops[stop].get("location_type") or 0) != 0:
                raise ValueError("Stop-times must reference platform/stop locations")
            parent = stops[stop].get("parent_station")
            if parent:
                if parent not in stops or int(stops[parent].get("location_type") or 0) != 1:
                    raise ValueError("Invalid parent station reference")
                stop_routes[parent].update(stop_routes[stop])
                stop_trips[parent].update(stop_trips[stop])
        selected_stops = {}
        for stop in sorted(stop_routes):
            row = dict(stops[stop])
            if not valid_coordinates(row["stop_lat"], row["stop_lon"]):
                raise ValueError(f"Invalid stop coordinates: {stop}")
            row["location_type"] = int(row.get("location_type") or 0)
            row["parent_station"] = row.get("parent_station") or ""
            selected_stops[stop] = {**row, "route_ids": sorted(stop_routes[stop])}
        shape_trips = defaultdict(list)
        for trip in sorted(trips):
            shape = trips[trip].get("shape_id")
            if not shape:
                raise ValueError(f"Selected trip has no static geometry: {trip}")
            shape_trips[(trips[trip]["route_id"], shape)].append(trip)
            visits[trip].sort(key=lambda row: row["stop_sequence"])
        points, diagnostics = extract_shapes(static / "shapes.txt", {s for r, s in shape_trips})
        staging = folder / "published"
        staging.mkdir()
        (staging / "routes").mkdir()
        route_files = {}
        for route in sorted(routes):
            geometry = []
            for (r, shape), ids in sorted(shape_trips.items()):
                if r != route:
                    continue
                geometry.append({"type": "Feature", "id": f"{route}:{shape}",
                    "properties": {**routes[route], "shape_id": shape, "trip_ids": ids,
                        "direction_ids": sorted({trips[t]["direction_id"] for t in ids
                                                 if trips[t]["direction_id"] is not None}),
                        "shape_pt_sequences": points[shape]["sequences"]},
                    "geometry": {"type": "LineString", "coordinates": points[shape]["coordinates"]}})
            stop_features = [{"type": "Feature", "id": stop,
                "properties": {**row, "trip_ids": sorted(stop_trips[stop])},
                "geometry": {"type": "Point", "coordinates": [row["stop_lon"], row["stop_lat"]]}}
                for stop, row in selected_stops.items() if route in row["route_ids"]]
            payload = {"label": LABEL, "data_source": "static_gtfs", "static_feed_version": version,
                "observation_window": None, "historical_data_status": "not_included",
                "route_id": route, "route": routes[route], "geometry": feature_collection(geometry),
                "stops": feature_collection(stop_features),
                "trips": [{**row, "stops": visits[trip]} for trip, row in sorted(trips.items())
                          if row["route_id"] == route]}
            name = hashlib.sha256(route.encode("utf8")).hexdigest() + ".json"
            route_files[route] = write_json(staging / "routes" / name, payload)
        catalog = {"routes": [routes[r] for r in sorted(routes)],
                   "stops": list(selected_stops.values())}
        catalog_file = write_json(staging / "catalog.json", catalog)
        # Preserve service calendars for rebuilding scheduled relationships; not observations.
        calendars = {name: list(rows(static / name)) for name in ("calendar.txt", "calendar_dates.txt")}
        calendar_file = write_json(staging / "calendars.json", calendars)
        manifest = {"format": "adelaide-static-map-v1", "label": LABEL,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "static_feed_version": version, "feed_info": feed[0], "source_archive": source,
            "source_files": {name: fingerprint(static / name) for name in SOURCE_FILES},
            "selection": {"agency_ids": sorted(agency_ids), "route_types": sorted(route_types),
                          "route_ids": sorted(routes), "geographic_boundary": None},
            "agencies": [agencies[a] for a in sorted(agency_ids)],
            "historical_data_status": "not_included", "catalog": catalog_file,
            "calendars": calendar_file, "route_files": route_files,
            "counts": {"routes": len(routes), "stops": len(selected_stops),
                "referenced_stops": len(referenced_stops), "parent_stations": len(selected_stops)-len(referenced_stops),
                "trips": len(trips), "stop_times": len(keys), "shapes": len(points),
                "route_shape_variants": len(shape_trips),
                "shape_points": sum(len(v["coordinates"]) for v in points.values())},
            "shape_diagnostics": diagnostics}
        write_json(staging / "manifest.json", manifest)
        if fingerprint(archive) != source:
            raise ValueError("Source archive changed during publication")
        staging.rename(output)
    return manifest


def configured():
    return bool(os.environ.get(MAP_DATA_ENV))


def _manifest(directory=None):
    configured_path = directory if directory is not None else os.environ.get(MAP_DATA_ENV)
    if not configured_path:
        raise ValueError("Static map data is not configured")
    folder = Path(configured_path)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf8"))
    if manifest["format"] != "adelaide-static-map-v1" or manifest["label"] != LABEL:
        raise ValueError("Unexpected static map manifest")
    return folder, manifest


def _verified_json(path, metadata):
    # Bound each request to its catalog or one route. Never parse source GTFS here.
    if fingerprint(path)["sha256"] != metadata["sha256"]:
        raise ValueError("Static artifact hash mismatch")
    return json.loads(path.read_text(encoding="utf8"))


def load_catalog(directory=None):
    try:
        folder, manifest = _manifest(directory)
        return _verified_json(folder / "catalog.json", manifest["catalog"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise MapDataUnavailableError("Static network catalog is missing or inconsistent; regenerate it") from error


def load_static_route_map_data(route_id, directory=None):
    try:
        folder, manifest = _manifest(directory)
        if route_id not in manifest["route_files"]:
            return None
        # Derive filename locally, never trust an ID or manifest path.
        name = hashlib.sha256(route_id.encode("utf8")).hexdigest() + ".json"
        data = _verified_json(folder / "routes" / name, manifest["route_files"][route_id])
        if (data["route_id"] != route_id or data["label"] != LABEL
                or data["static_feed_version"] != manifest["static_feed_version"]
                or not data["geometry"]["features"]):
            raise ValueError("Inconsistent static route geometry")
        return data
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise MapDataUnavailableError("Static route geometry is missing or inconsistent; regenerate it") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--agency-id", action="append", required=True)
    parser.add_argument("--route-type", action="append", type=int, required=True)
    parser.add_argument("--route-id", action="append")
    args = parser.parse_args()
    result = build_static_map_data(args.archive, args.output, expected_sha256=args.sha256,
        version=args.version, agency_ids=args.agency_id, route_types=args.route_type, route_ids=args.route_id)
    print(json.dumps(result["counts"], indent=2))


if __name__ == "__main__":
    main()
