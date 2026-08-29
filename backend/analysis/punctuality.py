"""Functions for analysing Adelaide Metro service punctuality."""


def calculate_delay_minutes(scheduled_timestamp, actual_timestamp):
    """
    Calculate delay in minutes.

    Positive = late
    Negative = early
    """
    return (actual_timestamp - scheduled_timestamp) / 60


def classify_punctuality(delay_minutes):
    """
    Classify a service using the current provisional thresholds.

    The exact five-minute boundary still needs client confirmation.
    """
    if delay_minutes < 0:
        return "Early"
    elif delay_minutes <= 5:
        return "On Time"
    elif delay_minutes <= 10:
        return "Delayed"
    else:
        return "Severely Delayed"