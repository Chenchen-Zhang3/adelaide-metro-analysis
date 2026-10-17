
"""Aggregation and delay hotspot analysis for Adelaide Metro."""

from collections import defaultdict
from math import isfinite

from .metrics import average_delay, average_positive_delay
from .punctuality import classify_punctuality


def validate_records(records):
    """Validate analysis records before aggregation."""
    valid_records = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} must be a dictionary")

        if "delay_minutes" not in record:
            raise ValueError(f"Record {index} has no delay_minutes")

        delay = record["delay_minutes"]

        if (
            isinstance(delay, bool)
            or not isinstance(delay, (int, float))
            or not isfinite(delay)
        ):
            raise ValueError(f"Invalid delay in record {index}")

        valid_records.append(record)

    return valid_records


def calculate_group_metrics(delays):
    """Calculate performance metrics for a group."""
    total = len(delays)

    if total == 0:
        return {}

    categories = [
        classify_punctuality(delay)
        for delay in delays
    ]

    early = categories.count("Early")
    on_time = categories.count("On Time")
    delayed = categories.count("Delayed")
    severe = categories.count("Severely Delayed")

    return {
        "total_services": total,
        "average_delay": round(average_delay(delays), 2),
        "average_positive_delay": round(
            average_positive_delay(delays), 2
        ),
        "early_count": early,
        "on_time_count": on_time,
        "delayed_count": delayed,
        "severely_delayed_count": severe,
        "total_late_count": delayed + severe,
        "early_percentage": round(early / total * 100, 2),
        "on_time_percentage": round(on_time / total * 100, 2),
        "delayed_percentage": round(delayed / total * 100, 2),
        "severe_delay_percentage": round(
            severe / total * 100, 2
        ),
        "total_late_percentage": round(
            (delayed + severe) / total * 100, 2
        ),
    }


def aggregate_by_field(records, field_name):
    """Aggregate records by a specified field."""
    groups = defaultdict(list)

    for record in validate_records(records):
        if field_name not in record or record[field_name] is None:
            raise ValueError(f"Missing field: {field_name}")

        group_id = record[field_name]
        groups[group_id].append(record["delay_minutes"])

    return {
        group_id: calculate_group_metrics(delays)
        for group_id, delays in groups.items()
    }


def aggregate_by_route(records):
    """Aggregate performance by route."""
    return aggregate_by_field(records, "route_id")


def aggregate_by_stop(records):
    """Aggregate performance by stop."""
    return aggregate_by_field(records, "stop_id")


def aggregate_by_time_period(records):
    """Aggregate performance by time period."""
    return aggregate_by_field(records, "time_period")


def find_delay_hotspots(records, min_services=10, top_n=None):
    """
    Identify delay hotspots from historical records.

    Ranking:
    1. Severe delay percentage
    2. Total late percentage
    3. Average positive delay
    4. Number of severely delayed services

    min_services=10 is a provisional threshold.
    """
    if (
        isinstance(min_services, bool)
        or not isinstance(min_services, int)
        or min_services < 1
    ):
        raise ValueError("min_services must be a positive integer")

    if top_n is not None and (
        isinstance(top_n, bool)
        or not isinstance(top_n, int)
        or top_n < 1
    ):
        raise ValueError("top_n must be a positive integer")

    stop_performance = aggregate_by_stop(records)
    hotspots = []

    for stop_id, performance in stop_performance.items():
        if performance["total_services"] < min_services:
            continue

        hotspots.append({
            "stop_id": stop_id,
            **performance,
        })

    hotspots.sort(
        key=lambda item: (
            -item["severe_delay_percentage"],
            -item["total_late_percentage"],
            -item["average_positive_delay"],
            -item["severely_delayed_count"],
            str(item["stop_id"]),
        )
    )

    if top_n is not None:
        hotspots = hotspots[:top_n]

    for rank, hotspot in enumerate(hotspots, start=1):
        hotspot["rank"] = rank

    return hotspots


def prepare_analysis_output(records, min_services=10):
    """Prepare structured results for backend integration."""
    validated = validate_records(records)

    return {
        "route_performance": aggregate_by_route(validated),
        "stop_performance": aggregate_by_stop(validated),
        "time_period_performance": aggregate_by_time_period(
            validated
        ),
        "delay_hotspots": find_delay_hotspots(
            validated,
            min_services=min_services
        ),
    }
