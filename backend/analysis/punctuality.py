
"""Punctuality analysis for Adelaide Metro transport services.

This module calculates signed arrival delays and classifies services
as Early, On Time, Delayed, or Severely Delayed.
"""

from datetime import datetime


def calculate_delay_minutes(scheduled_timestamp, actual_timestamp):
    """Calculate arrival delay relative to the scheduled arrival time.

    Args:
        scheduled_timestamp: Scheduled arrival as a numeric timestamp
            in seconds or a Python datetime object.
        actual_timestamp: Actual or predicted arrival in the same
            supported representation.

    Returns:
        float: Signed delay in minutes.
            Positive values indicate late arrival.
            Negative values indicate early arrival.
            Zero indicates arrival exactly on schedule.

    Raises:
        TypeError: If the two timestamps have incompatible types.

    Note:
        This function calculates a time difference only. Whether the
        input represents an actual arrival or a predicted arrival
        depends on the upstream GTFS data source.
    """

    # Handle two datetime objects by converting their difference
    # from seconds into minutes.
    if isinstance(scheduled_timestamp, datetime) and isinstance(
        actual_timestamp, datetime
    ):
        difference = actual_timestamp - scheduled_timestamp
        return difference.total_seconds() / 60

    # Handle numeric timestamps measured in seconds.
    # Subtract scheduled time from actual/predicted time.
    if isinstance(scheduled_timestamp, (int, float)) and isinstance(
        actual_timestamp, (int, float)
    ):
        return (actual_timestamp - scheduled_timestamp) / 60

    # Reject unsupported or incompatible timestamp types.
    raise TypeError("Both timestamps must have compatible types.")


def classify_punctuality(delay_minutes):
    """Classify a transport service using its signed delay.

    Classification thresholds:
        Early: delay < 0 minutes
        On Time: 0 <= delay <= 5 minutes
        Delayed: 5 < delay <= 10 minutes
        Severely Delayed: delay > 10 minutes

    Args:
        delay_minutes: Signed arrival delay in minutes.

    Returns:
        str: One of four punctuality categories.

    Boundary rules:
        Exactly 0 or 5 minutes is On Time.
        Exactly 10 minutes is Delayed.
        Only delays greater than 10 minutes are Severely Delayed.
    """

    # A negative delay means the service arrived before schedule.
    if delay_minutes < 0:
        return "Early"

    # Services arriving up to five minutes late are On Time.
    elif delay_minutes <= 5:
        return "On Time"

    # Delays greater than five and up to ten minutes are Delayed.
    elif delay_minutes <= 10:
        return "Delayed"

    # Any delay greater than ten minutes is Severely Delayed.
    else:
        return "Severely Delayed"
