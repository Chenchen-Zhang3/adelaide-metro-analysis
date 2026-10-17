
"""Functions for calculating transport performance metrics."""

from .punctuality import classify_punctuality


def average_delay(delays):
    """Return the average delay in minutes."""
    if not delays:
        return 0.0

    return sum(delays) / len(delays)


def average_positive_delay(delays):
    """Return average delay among late arrivals only."""
    positive_delays = [d for d in delays if d > 0]

    if not positive_delays:
        return 0.0

    return sum(positive_delays) / len(positive_delays)


def delayed_service_count(delays, threshold=5):
    """Count all services delayed beyond the threshold."""
    return sum(d > threshold for d in delays)


def total_late_count(delays):
    """Count delayed and severely delayed services."""
    return sum(d > 5 for d in delays)


def delayed_rate(delays):
    """Percentage of services classified as Delayed."""
    if not delays:
        return 0.0

    count = sum(
        classify_punctuality(d) == "Delayed"
        for d in delays
    )
    return count / len(delays) * 100


def on_time_rate(delays, threshold=5):
    """Percentage of arrivals between 0 and threshold."""
    if not delays:
        return 0.0

    count = sum(0 <= d <= threshold for d in delays)
    return count / len(delays) * 100


def early_arrival_rate(delays):
    """Percentage of services arriving early."""
    if not delays:
        return 0.0

    count = sum(d < 0 for d in delays)
    return count / len(delays) * 100


def severe_delay_rate(delays, threshold=10):
    """Percentage of services delayed more than threshold."""
    if not delays:
        return 0.0

    count = sum(d > threshold for d in delays)
    return count / len(delays) * 100
