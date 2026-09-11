"""Backend API for Adelaide Metro data."""

from flask import Flask, jsonify

from backend.database.repository import (
    get_all_routes,
    get_all_stops,
    get_stop,
)


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