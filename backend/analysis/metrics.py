"""Functions for calculating transport performance metrics."""


def average_delay(delays):
    """Return the average delay in minutes."""
    if not delays:
        return 0.0

    return sum(delays) / len(delays)


def delayed_service_count(delays, threshold=5):
    """Count services delayed by more than the threshold."""
    return sum(delay > threshold for delay in delays)


def delayed_rate(delays):
    """Return percentage of delayed services (>5 and <=10 minutes)."""
    if not delays:
        return 0.0

    delayed = sum(5 < delay <= 10 for delay in delays)

    return (delayed / len(delays)) * 100

def on_time_rate(delays, threshold=5):
    """Return the percentage of services that are on time."""
    if not delays:
        return 0.0

    on_time = sum(0 <= delay <= threshold for delay in delays)

    return (on_time / len(delays)) * 100


def early_arrival_rate(delays):
    """Return the percentage of services arriving early."""
    if not delays:
        return 0.0

    early = sum(delay < 0 for delay in delays)

    return (early / len(delays)) * 100


def severe_delay_rate(delays, threshold=10):
    """Return the percentage of severely delayed services."""
    if not delays:
        return 0.0

    severe = sum(delay > threshold for delay in delays)

    return (severe / len(delays)) * 100