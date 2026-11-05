"""Backend API for Adelaide Metro data."""

import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.database.repository import (
    get_all_routes,
    get_all_stops,
    get_routes_by_stop,
    get_stop,
)
from backend.services import static_map_data
from backend.services.stop_delays import query_network_stop_delays
from backend.database.stop_delays import StopDelayLimitError
from backend.services.pipeline import query_and_analyse
from backend.services.vehicle_history import query_vehicle_history
from backend.services.recorded_map_data import (
    MAP_DATA_ENV as DEMO_MAP_DATA_ENV,
    MapDataUnavailableError,
    load_route_map_data,
)


app = Flask(__name__)
CORS(app)


@app.get("/api/analysis/stop-delays")
def get_network_stop_delays():
    """Bounded bulk statistics; never fall back to an unfiltered query."""
    allowed = {"start_time", "end_time", "route_id", "min_samples", "scope"}
    if set(request.args) - allowed or any(len(request.args.getlist(k)) != 1 for k in request.args):
        return jsonify({"error": "Unknown or repeated query parameter"}), 400
    try:
        return jsonify(query_network_stop_delays(
            request.args.get("start_time"), request.args.get("end_time"),
            route_id=request.args.get("route_id"),
            min_samples=request.args.get("min_samples", "10"),
            scope=request.args.get("scope", "observed"),
        ))
    except StopDelayLimitError as error:
        return jsonify({"error": str(error), "code": "analysis_limit_exceeded"}), 422
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


def performance_time_filters():
    """Validate optional inclusive observation-time bounds for performance."""
    filters = {}
    instants = {}
    for name in ("start_time", "end_time"):
        if name not in request.args:
            continue
        try:
            instant = datetime.fromisoformat(request.args[name])
            if instant.utcoffset() is None:
                raise ValueError("Missing UTC offset")
            instant = instant.astimezone(timezone.utc)
        except (ValueError, OverflowError) as error:
            raise ValueError(
                f"{name} must be an ISO 8601 timestamp with a UTC offset"
            ) from error
        instants[name] = instant
        filters[name] = instant.isoformat()
    if (
        "start_time" in instants and "end_time" in instants
        and instants["start_time"] > instants["end_time"]
    ):
        raise ValueError("start_time must be before or equal to end_time")
    return filters


@app.errorhandler(sqlite3.Error)
def handle_database_error(error):
    """Return a JSON response for database errors."""

    return jsonify({"error": "Database error"}), 500


@app.errorhandler(MapDataUnavailableError)
def handle_map_data_error(error):
    return jsonify({"error": str(error)}), 503


@app.errorhandler(404)
def handle_not_found(error):
    """Return a JSON response for unknown API routes."""

    return jsonify({"error": "Endpoint not found"}), 404


@app.get("/api/stops")
def get_stops():
    """Return Adelaide Metro stops."""

    stops = (static_map_data.load_catalog()["stops"]
             if static_map_data.configured() else get_all_stops())

    return jsonify(stops)


@app.get("/api/routes")
def get_routes():
    """Return Adelaide Metro routes."""

    routes = (static_map_data.load_catalog()["routes"]
              if static_map_data.configured() else get_all_routes())

    return jsonify(routes)


@app.get("/api/stops/<stop_id>")
def get_stop_detail(stop_id):
    """Return details for one Adelaide Metro stop."""

    stop = (next((row for row in static_map_data.load_catalog()["stops"]
                  if row["stop_id"] == stop_id), None)
            if static_map_data.configured() else get_stop(stop_id))

    if stop is None:
        return jsonify({"error": "Stop not found"}), 404

    return jsonify(stop)


@app.get("/api/stops/<stop_id>/routes")
def get_stop_routes(stop_id):
    """Return routes that serve the selected stop."""

    if static_map_data.configured():
        catalog = static_map_data.load_catalog()
        stop = next((row for row in catalog["stops"] if row["stop_id"] == stop_id), None)
        routes = [row for row in catalog["routes"]
                  if stop and row["route_id"] in stop["route_ids"]]
    else:
        routes = get_routes_by_stop(stop_id)

    return jsonify(routes)


@app.get("/api/routes/<route_id>/performance")
def get_route_performance(route_id):
    """Return performance data for one route."""

    try:
        analysis = query_and_analyse(
            route_id=route_id, **performance_time_filters()
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    performance = analysis["route_performance"].get(route_id)

    if performance is None:
        return jsonify({"error": "Route performance not found"}), 404

    return jsonify(performance)


@app.get("/api/routes/<route_id>/map-data")
def get_recorded_route_map_data(route_id):
    """Prefer configured recorded demo; opt in to a separate static publication."""
    source = request.args.get("source")
    if source not in (None, "static", "recorded"):
        return jsonify({"error": "source must be static or recorded"}), 400
    if source == "static":
        data = static_map_data.load_static_route_map_data(route_id)
    elif source == "recorded" or os.environ.get(DEMO_MAP_DATA_ENV):
        # Corrupt demo artifacts fail closed, never silently become static data.
        data = load_route_map_data(route_id)
        if data is None and source is None and static_map_data.configured():
            data = static_map_data.load_static_route_map_data(route_id)
    elif static_map_data.configured():
        data = static_map_data.load_static_route_map_data(route_id)
    else:
        data = load_route_map_data(route_id)
    if data is None:
        return jsonify({"error": "Route map data not found"}), 404
    return jsonify(data)


@app.get("/api/routes/<route_id>/vehicle-positions")
def get_route_vehicle_history(route_id):
    """Return a bounded page of recorded observations, not live vehicle state."""
    try:
        data = query_vehicle_history(route_id, **request.args.to_dict())
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    if data is None:
        return jsonify({"error": "Route not found"}), 404
    return jsonify(data)


@app.get("/api/stops/<stop_id>/performance")
def get_stop_performance(stop_id):
    """Return performance data for one stop."""

    try:
        analysis = query_and_analyse(
            stop_id=stop_id, **performance_time_filters()
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    performance = analysis["stop_performance"].get(stop_id)

    if performance is None:
        return jsonify({"error": "Stop performance not found"}), 404

    return jsonify(performance)


@app.get("/api/analysis/hotspots")
def get_delay_hotspots():
    """Return historical delay hotspots."""

    try:
        min_services = request.args.get(
            "min_services", default=10, type=int
        )

        if min_services < 1:
            return jsonify({
                "error": "min_services must be positive"
            }), 400

        route_id = request.args.get("route_id")
        stop_id = request.args.get("stop_id")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")

        analysis = query_and_analyse(
            route_id=route_id,
            stop_id=stop_id,
            start_time=start_time,
            end_time=end_time,
            min_services=min_services,
        )

        return jsonify({
            "hotspots": analysis["delay_hotspots"],
            "total_hotspots": len(analysis["delay_hotspots"]),
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400
