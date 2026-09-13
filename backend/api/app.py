"""Backend API for Adelaide Metro data."""

from flask import Flask, jsonify

from backend.database.repository import (
    get_all_routes,
    get_all_stops,
    get_stop,
)
from backend.services.pipeline import query_and_analyse


app = Flask(__name__)


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


@app.get("/api/routes/<route_id>/performance")
def get_route_performance(route_id):
    """Return performance data for one route."""

    analysis = query_and_analyse(route_id=route_id)

    performance = analysis["route_performance"].get(route_id)

    if performance is None:
        return jsonify({"error": "Route performance not found"}), 404

    return jsonify(performance)


@app.get("/api/stops/<stop_id>/performance")
def get_stop_performance(stop_id):
    """Return performance data for one stop."""

    analysis = query_and_analyse(stop_id=stop_id)

    performance = analysis["stop_performance"].get(stop_id)

    if performance is None:
        return jsonify({"error": "Stop performance not found"}), 404

    return jsonify(performance)