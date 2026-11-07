
"""Aggregation and delay hotspot analysis for Adelaide Metro.

This module validates delay observations, calculates grouped
reliability statistics, and identifies stops with high levels
of late and severely delayed services.

Records can be grouped by route, stop, or time period.
"""

from collections import defaultdict
from math import isfinite

from .metrics import average_delay, average_positive_delay
from .punctuality import classify_punctuality


def validate_records(records):
    """Validate delay observations before performing aggregation.

    Each record must be a dictionary containing a finite numeric
    delay_minutes value. Boolean, missing, non-numeric, NaN, and
    infinite delay values are rejected.

    Returns:
        list: Validated records in their original order.

    Raises:
        ValueError: If a record has an invalid structure or delay.
    """

    valid_records = []

    # Check each observation independently.
    for index, record in enumerate(records):

        # Every observation must use a dictionary structure.
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} must be a dictionary")

        # Delay is required for all analytical calculations.
        if "delay_minutes" not in record:
            raise ValueError(f"Record {index} has no delay_minutes")

        delay = record["delay_minutes"]

        # Reject booleans, non-numeric values, NaN and infinity.
        if (
            isinstance(delay, bool)
            or not isinstance(delay, (int, float))
            or not isfinite(delay)
        ):
            raise ValueError(f"Invalid delay in record {index}")

        valid_records.append(record)

    return valid_records


def calculate_group_metrics(delays):
    """Calculate delay and punctuality statistics for one group.

    Args:
        delays: Collection of signed delay values in minutes.

    Returns:
        dict: Service counts, average delays, punctuality
        categories, and percentages rounded to two decimals.

    An empty group returns an empty dictionary.
    """

    # Each supplied delay represents one analysis observation.
    total = len(delays)

    if total == 0:
        return {}

    # Assign every observation to one punctuality category.
    categories = [
        classify_punctuality(delay)
        for delay in delays
    ]

    # Count observations in the four exclusive categories.
    early = categories.count("Early")
    on_time = categories.count("On Time")
    delayed = categories.count("Delayed")
    severe = categories.count("Severely Delayed")

    # Late services include both Delayed and Severely Delayed.
    # Percentages use the total number of group observations.
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
    """Group records by a selected field and calculate statistics.

    Args:
        records: Collection of delay observation dictionaries.
        field_name: Field used to identify each group.

    Returns:
        dict: Mapping from group IDs to calculated metrics.

    Raises:
        ValueError: If a required grouping field is missing.
    """

    # Store delay observations separately for each group ID.
    groups = defaultdict(list)

    for record in validate_records(records):

        # All observations must contain the requested group field.
        if field_name not in record or record[field_name] is None:
            raise ValueError(f"Missing field: {field_name}")

        group_id = record[field_name]

        # Add the signed delay to its corresponding group.
        groups[group_id].append(record["delay_minutes"])

    # Calculate reliability metrics independently for each group.
    return {
        group_id: calculate_group_metrics(delays)
        for group_id, delays in groups.items()
    }


def aggregate_by_route(records):
    """Calculate delay and punctuality metrics for each route."""

    # Group observations using their route identifiers.
    return aggregate_by_field(records, "route_id")


def aggregate_by_stop(records):
    """Calculate delay and punctuality metrics for each stop."""

    # Group observations using their stop identifiers.
    return aggregate_by_field(records, "stop_id")


def aggregate_by_time_period(records):
    """Calculate delay statistics for each recorded time period."""

    # Compare performance across periods such as Morning or Afternoon.
    return aggregate_by_field(records, "time_period")


def find_delay_hotspots(records, min_services=10, top_n=None):
    """Identify and rank stop-level delay hotspots.

    Stops are ranked using the following priorities:
        1. Highest severe delay percentage.
        2. Highest total late percentage.
        3. Highest average positive delay.
        4. Highest number of severely delayed services.
        5. Stop ID as a deterministic tie-breaker.

    Args:
        records: Historical delay observations containing stop IDs.
        min_services: Minimum observations required per stop.
            The default of 10 is a provisional threshold.
        top_n: Optional maximum number of ranked stops.

    Returns:
        list: Ranked hotspot dictionaries with one-based ranks.

    Raises:
        ValueError: If min_services or top_n is invalid.

    Note:
        The ranking describes supplied observations only.
        It does not identify the causes of delays or guarantee
        statistical significance.
    """

    # The minimum sample threshold must be a positive integer.
    # Boolean values are explicitly rejected.
    if (
        isinstance(min_services, bool)
        or not isinstance(min_services, int)
        or min_services < 1
    ):
        raise ValueError("min_services must be a positive integer")

    # Validate the optional maximum number of returned hotspots.
    if top_n is not None and (
        isinstance(top_n, bool)
        or not isinstance(top_n, int)
        or top_n < 1
    ):
        raise ValueError("top_n must be a positive integer")

    # Calculate stop-level performance before ranking.
    stop_performance = aggregate_by_stop(records)
    hotspots = []

    for stop_id, performance in stop_performance.items():

        # Exclude stops with fewer than the required observations.
        # These stops remain available in ordinary stop aggregation.
        if performance["total_services"] < min_services:
            continue

        # Preserve the stop identifier and its calculated metrics.
        hotspots.append({
            "stop_id": stop_id,
            **performance,
        })

    # Sort by descending reliability risk indicators.
    # Negative values implement descending numeric ordering.
    # Stop IDs provide deterministic ordering for remaining ties.
    hotspots.sort(
        key=lambda item: (
            -item["severe_delay_percentage"],
            -item["total_late_percentage"],
            -item["average_positive_delay"],
            -item["severely_delayed_count"],
            str(item["stop_id"]),
        )
    )

    # Return only the requested number of hotspots, if specified.
    if top_n is not None:
        hotspots = hotspots[:top_n]

    # Assign ranks starting from one after sorting and filtering.
    for rank, hotspot in enumerate(hotspots, start=1):
        hotspot["rank"] = rank

    return hotspots


def prepare_analysis_output(records, min_services=10):
    """Prepare grouped reliability results for backend integration.

    Args:
        records: Delay observations containing route_id, stop_id,
            time_period, and delay_minutes.
        min_services: Minimum observations for hotspot eligibility.

    Returns:
        dict: Route performance, stop performance, time-period
        performance, and ranked delay hotspots.

    This function prepares analysis results but does not
    independently retrieve GTFS feeds or write to a database.
    """

    # Validate observations before calculating grouped results.
    validated = validate_records(records)

    # Assemble the four analysis outputs for downstream consumers.
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
