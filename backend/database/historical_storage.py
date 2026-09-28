"""Storage-boundary helpers for the optimised historical GTFS schema."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo


ADELAIDE_TIMEZONE = ZoneInfo("Australia/Adelaide")
TRIP_UPDATE_CHECKPOINT_ENVIRONMENT_VARIABLE = (
    "ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS"
)
DEFAULT_TRIP_UPDATE_CHECKPOINT_SECONDS = 15 * 60


def configured_trip_update_checkpoint_seconds(environ=None):
    """Return the positive unchanged-state checkpoint interval."""
    environment = os.environ if environ is None else environ
    raw_value = environment.get(
        TRIP_UPDATE_CHECKPOINT_ENVIRONMENT_VARIABLE,
        str(DEFAULT_TRIP_UPDATE_CHECKPOINT_SECONDS),
    )
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{TRIP_UPDATE_CHECKPOINT_ENVIRONMENT_VARIABLE} must be an integer"
        ) from error
    if value <= 0:
        raise ValueError(
            f"{TRIP_UPDATE_CHECKPOINT_ENVIRONMENT_VARIABLE} must be greater than zero"
        )
    return value


def iso_timestamp_to_epoch(value, field_name="timestamp", required=False):
    """Convert an ISO timestamp to UTC epoch seconds for SQLite storage."""
    if value in (None, ""):
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=ADELAIDE_TIMEZONE)
    return int(parsed.timestamp())


def epoch_to_adelaide_iso(value):
    """Convert stored UTC epoch seconds to the established Adelaide ISO format."""
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=ADELAIDE_TIMEZONE).isoformat()


def derived_actual_arrival(scheduled_arrival_epoch, delay_seconds):
    """Reconstruct actual arrival without physically storing the redundant field."""
    if scheduled_arrival_epoch is None:
        return None
    return epoch_to_adelaide_iso(
        int(scheduled_arrival_epoch) + int(delay_seconds)
    )


def validate_derivable_actual_arrival(
    scheduled_arrival_epoch,
    actual_arrival,
    delay_seconds,
):
    """Reject a supplied actual arrival that cannot be reconstructed exactly."""
    if actual_arrival in (None, ""):
        return
    actual_epoch = iso_timestamp_to_epoch(
        actual_arrival,
        field_name="actual_arrival",
        required=True,
    )
    expected = int(scheduled_arrival_epoch) + int(delay_seconds)
    if actual_epoch != expected:
        raise ValueError(
            "actual_arrival must equal scheduled_arrival + delay_seconds"
        )
