
"""Delay and reliability metrics for Adelaide Metro services.

This module calculates average delays, service counts, and punctuality
percentages using signed delay values measured in minutes.

Positive delays indicate late arrivals, while negative delays
indicate early arrivals.
"""

from .punctuality import classify_punctuality


def average_delay(delays):
    """Calculate the mean signed delay across all observations.

    Early arrivals contribute negative values and may offset
    positive delays in the average.

    Returns 0.0 when the input collection is empty.
    """

    # Avoid division by zero when no observations are available.
    if not delays:
        return 0.0

    # Include both early and late arrivals in the mean.
    return sum(delays) / len(delays)


def average_positive_delay(delays):
    """Calculate average delay among positive delay values only.

    A positive delay means d > 0, including small delays that
    are still classified as On Time under the five-minute rule.

    Returns 0.0 if no positive delays exist.
    """

    # Exclude early arrivals and exactly on-schedule arrivals.
    positive_delays = [d for d in delays if d > 0]

    if not positive_delays:
        return 0.0

    # Calculate the mean of positive delay observations.
    return sum(positive_delays) / len(positive_delays)


def delayed_service_count(delays, threshold=5):
    """Count services whose delay exceeds the given threshold.

    The default threshold is five minutes. At this threshold,
    both Delayed and Severely Delayed services are counted.

    A delay equal to the threshold is not counted.
    """

    # Count only observations strictly above the threshold.
    return sum(d > threshold for d in delays)


def total_late_count(delays):
    """Count services classified as late under the five-minute rule.

    This includes Delayed and Severely Delayed services.
    Early and On Time observations are excluded.
    """

    # Operational lateness begins above five minutes.
    return sum(d > 5 for d in delays)


def delayed_rate(delays):
    """Calculate the percentage classified specifically as Delayed.

    Delayed means 5 < delay <= 10 minutes.
    Severely Delayed observations are not included here.

    Returns 0.0 for an empty collection.
    """

    if not delays:
        return 0.0

    # Reuse the shared classification logic for consistency.
    count = sum(
        classify_punctuality(d) == "Delayed"
        for d in delays
    )

    # Convert the category count into a percentage.
    return count / len(delays) * 100


def on_time_rate(delays, threshold=5):
    """Calculate the percentage of On Time observations.

    An observation is On Time when its signed delay is
    between zero and the inclusive threshold.

    Early arrivals are excluded from this percentage.
    Returns 0.0 for empty input.
    """

    if not delays:
        return 0.0

    # Both zero and the threshold are inclusive boundaries.
    count = sum(0 <= d <= threshold for d in delays)

    return count / len(delays) * 100


def early_arrival_rate(delays):
    """Calculate the percentage of services arriving early.

    Any negative signed delay is classified as Early.
    Returns 0.0 when no observations are supplied.
    """

    if not delays:
        return 0.0

    # Count observations occurring before scheduled arrival.
    count = sum(d < 0 for d in delays)

    return count / len(delays) * 100


def severe_delay_rate(delays, threshold=10):
    """Calculate the percentage of severely delayed services.

    The default threshold is ten minutes.
    Only delays strictly greater than the threshold count.

    Returns 0.0 for empty input.
    """

    if not delays:
        return 0.0

    # A delay of exactly ten minutes is not severe by default.
    count = sum(d > threshold for d in delays)

    return count / len(delays) * 100
