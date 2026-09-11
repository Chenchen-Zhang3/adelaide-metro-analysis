"""Backend API for Adelaide Metro data."""

from flask import Flask, jsonify

from backend.database.repository import (
    get_all_routes,
    get_all_stops,
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