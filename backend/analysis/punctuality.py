
"""Functions for analysing Adelaide Metro service punctuality."""

from datetime import datetime


def calculate_delay_minutes(scheduled_timestamp, actual_timestamp):
    """
    Calculate the difference between actual and scheduled arrival.

    Positive = late
    Negative = early

    Supports numeric timestamps in seconds or datetime objects.
    """
    if isinstance(scheduled_timestamp, datetime) and isinstance(
        actual_timestamp, datetime
    ):
        difference = actual_timestamp - scheduled_timestamp
        return difference.total_seconds() / 60

    if isinstance(scheduled_timestamp, (int, float)) and isinstance(
        actual_timestamp, (int, float)
    ):
        return (actual_timestamp - scheduled_timestamp) / 60

    raise TypeError("Both timestamps must have compatible types.")


def classify_punctuality(delay_minutes):
    """
    Classify arrival punctuality.

    Early: delay < 0
    On Time: 0 <= delay <= 5
    Delayed: 5 < delay <= 10
    Severely Delayed: delay > 10
    """
    if delay_minutes < 0:
        return "Early"
    elif delay_minutes <= 5:
        return "On Time"
    elif delay_minutes <= 10:
        return "Delayed"
    else:
        return "Severely Delayed"
