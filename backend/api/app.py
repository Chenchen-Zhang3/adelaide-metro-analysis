"""Backend API for Adelaide Metro data."""

import sqlite3

from flask import Flask, jsonify
from flask_cors import CORS

from backend.database.repository import (
    get_all_routes,
    get_all_stops,
    get_routes_by_stop,
    get_stop,
)
from backend.services.pipeline import query_and_analyse
from backend.services.recorded_map_data import (
    MapDataUnavailableError,
    load_route_map_data,
)


app = Flask(__name__)
CORS(app)


@app.errorhandler(sqlite3.Error)
def handle_database_error(error):
    """Return a JSON response for database errors."""

    return jsonify({"error": "Database error"}), 500


@app.errorhandler(404)
def handle_not_found(error):
    """Return a JSON response for unknown API routes."""

    return jsonify({"error": "Endpoint not found"}), 404


@app.get("/api/stops")
def get_stops():
    """Return Adelaide Metro stops."""

    stops = get_all_stops()

    return jsonify(stops)


@app.get("/api/routes")
def get_routes():
    """Return Adelaide Metro routes."""

    routes = get_all_routes()

    return jsonify(routes)


@app.get("/api/stops/<stop_id>")
def get_stop_detail(stop_id):
    """Return details for one Adelaide Metro stop."""

    stop = get_stop(stop_id)

    if stop is None:
        return jsonify({"error": "Stop not found"}), 404

    return jsonify(stop)


@app.get("/api/stops/<stop_id>/routes")
def get_stop_routes(stop_id):
    """Return routes that serve the selected stop."""

    routes = get_routes_by_stop(stop_id)

    return jsonify(routes)


@app.get("/api/routes/<route_id>/performance")
def get_route_performance(route_id):
    """Return performance data for one route."""

    analysis = query_and_analyse(route_id=route_id)

    performance = analysis["route_performance"].get(route_id)

    if performance is None:
        return jsonify({"error": "Route performance not found"}), 404

    return jsonify(performance)


@app.get("/api/routes/<route_id>/map-data")
def get_recorded_route_map_data(route_id):
    """Return official shapes and related stops/trips for the recorded demo."""
    try:
        data = load_route_map_data(route_id)
    except MapDataUnavailableError as error:
        return jsonify({"error": str(error)}), 503
    if data is None:
        return jsonify({"error": "Recorded route map data not found"}), 404
    return jsonify(data)


@app.get("/api/stops/<stop_id>/performance")
def get_stop_performance(stop_id):
    """Return performance data for one stop."""

    analysis = query_and_analyse(stop_id=stop_id)

    performance = analysis["stop_performance"].get(stop_id)

    if performance is None:
        return jsonify({"error": "Stop performance not found"}), 404

    return jsonify(performance)
