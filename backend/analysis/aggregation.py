"""Functions for aggregating Adelaide Metro performance data."""

from .metrics import average_delay
from .punctuality import classify_punctuality


def aggregate_by_route(records):
    """Aggregate transport performance by route."""

    routes = {}

    for record in records:
        route_id = record["route_id"]
        delay = record["delay_minutes"]

        if route_id not in routes:
            routes[route_id] = []

        routes[route_id].append(delay)

    results = {}

    for route_id, delays in routes.items():
        classifications = [
            classify_punctuality(delay)
            for delay in delays
        ]

        results[route_id] = {
            "total_services": len(delays),
            "average_delay": round(average_delay(delays), 2),

            "early_count": classifications.count("Early"),
            "on_time_count": classifications.count("On Time"),
            "delayed_count": classifications.count("Delayed"),
            "severely_delayed_count":
                classifications.count("Severely Delayed"),

            "early_percentage": round(
                classifications.count("Early") / len(delays) * 100, 2
            ),
            "on_time_percentage": round(
                classifications.count("On Time") / len(delays) * 100, 2
            ),
            "delayed_percentage": round(
                classifications.count("Delayed") / len(delays) * 100, 2
            ),
            "severe_delay_percentage": round(
                classifications.count("Severely Delayed") / len(delays) * 100, 2
            ),
        }

    return results
   

def aggregate_by_stop(records):
    """Aggregate transport performance by stop."""

    stops = {}

    for record in records:
        stop_id = record["stop_id"]
        delay = record["delay_minutes"]

        if stop_id not in stops:
            stops[stop_id] = []

        stops[stop_id].append(delay)

    results = {}

    for stop_id, delays in stops.items():
        classifications = [
            classify_punctuality(delay)
            for delay in delays
        ]

        results[stop_id] = {
            "total_services": len(delays),
            "average_delay": round(average_delay(delays), 2),

            "early_count": classifications.count("Early"),
            "on_time_count": classifications.count("On Time"),
            "delayed_count": classifications.count("Delayed"),
            "severely_delayed_count":
                classifications.count("Severely Delayed"),

            "early_percentage": round(
                classifications.count("Early") / len(delays) * 100, 2
            ),
            "on_time_percentage": round(
                classifications.count("On Time") / len(delays) * 100, 2
            ),
            "delayed_percentage": round(
                classifications.count("Delayed") / len(delays) * 100, 2
            ),
            "severe_delay_percentage": round(
                classifications.count("Severely Delayed") / len(delays) * 100, 2
            ),
        }

    return results


def aggregate_by_time_period(records):
    """Aggregate transport performance by time period."""

    periods = {}

    for record in records:
        time_period = record["time_period"]
        delay = record["delay_minutes"]

        if time_period not in periods:
            periods[time_period] = []

        periods[time_period].append(delay)

    results = {}

    for time_period, delays in periods.items():
        classifications = [
            classify_punctuality(delay)
            for delay in delays
        ]

        results[time_period] = {
            "total_services": len(delays),
            "average_delay": round(average_delay(delays), 2),

            "early_count": classifications.count("Early"),
            "on_time_count": classifications.count("On Time"),
            "delayed_count": classifications.count("Delayed"),
            "severely_delayed_count":
                classifications.count("Severely Delayed"),

            "early_percentage": round(
                classifications.count("Early") / len(delays) * 100, 2
            ),
            "on_time_percentage": round(
                classifications.count("On Time") / len(delays) * 100, 2
            ),
            "delayed_percentage": round(
                classifications.count("Delayed") / len(delays) * 100, 2
            ),
            "severe_delay_percentage": round(
                classifications.count("Severely Delayed") / len(delays) * 100, 2
            ),
        }

    return results

def find_delay_hotspots(records, min_services=1):
    """Identify stops with the worst delay performance."""

    stop_performance = aggregate_by_stop(records)
    hotspots = []

    for stop_id, performance in stop_performance.items():
        if performance["total_services"] >= min_services:
            hotspots.append({
                "stop_id": stop_id,
                "average_delay": performance["average_delay"],
                "delayed_percentage": performance["delayed_percentage"],
                "severe_delay_percentage":
                    performance["severe_delay_percentage"],
            })

    return sorted(
        hotspots,
        key=lambda x: (
            x["severe_delay_percentage"],
            x["average_delay"]
        ),
        reverse=True
    )

def prepare_analysis_output(records):
    """Prepare structured transport analysis output for backend."""

    return {
        "route_performance": aggregate_by_route(records),
        "stop_performance": aggregate_by_stop(records),
        "time_period_performance": aggregate_by_time_period(records),
        "delay_hotspots": find_delay_hotspots(records),
    }