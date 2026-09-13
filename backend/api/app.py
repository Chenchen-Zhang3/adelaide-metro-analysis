"""Backend API for Adelaide Metro data."""

from flask import Flask, jsonify
from flask_cors import CORS

from backend.database.repository import (
    get_all_stops,
    get_routes_by_stop,
    get_trip_updates_by_stop,
)


app = Flask(__name__)

CORS(app)


@app.get("/api/stops")
def get_stops():
    """Return Adelaide Metro stops."""

    stops = get_all_stops()

    return jsonify(stops)


@app.get("/api/stops/<stop_id>/routes")
def get_stop_routes(stop_id):
    """Return routes that serve the selected stop."""

    routes = get_routes_by_stop(stop_id)

    return jsonify(routes)


@app.get("/api/stops/<stop_id>/performance")
def get_stop_performance(stop_id):
    """Return available performance records for the selected stop."""

    trip_updates = get_trip_updates_by_stop(stop_id)

    return jsonify(trip_updates)