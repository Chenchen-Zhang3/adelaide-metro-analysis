"""Small paginated historical-vehicle contract; no collection or writes."""
from contextlib import closing
from datetime import datetime, timezone

from backend.database.connection import get_connection


def query_vehicle_history(route_id, start_time=None, end_time=None,
                          limit="500", offset="0"):
    """Query [start_time, end_time), requiring explicit timezone-aware bounds.

    SQLite julianday compares instants rather than lexically comparing offsets.
    Offset pagination is for a fixed recorded dataset, not an actively growing DB.
    """
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        limit, offset = int(limit), int(offset)
    except (TypeError, ValueError) as error:
        raise ValueError("Supply ISO start_time/end_time and integer limit/offset") from error
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("Time bounds must include a UTC offset")
    if start >= end:
        raise ValueError("start_time must be before end_time")
    if not 1 <= limit <= 1000 or not 0 <= offset <= 2**63 - 1:
        raise ValueError("limit must be 1..1000 and offset must be a non-negative SQLite integer")
    with closing(get_connection()) as connection:
        if not connection.execute("SELECT 1 FROM routes WHERE route_id = ?", (route_id,)).fetchone():
            return None
        rows = connection.execute(
            "SELECT * FROM vehicle_positions WHERE route_id = ? "
            "AND julianday(timestamp) >= julianday(?) "
            "AND julianday(timestamp) < julianday(?) "
            "ORDER BY julianday(timestamp), id LIMIT ? OFFSET ?",
            (route_id, start.astimezone(timezone.utc).isoformat(),
             end.astimezone(timezone.utc).isoformat(), limit + 1, offset),
        ).fetchall()
    more = len(rows) > limit
    return {"route_id": route_id, "start_time": start.isoformat(),
            "end_exclusive": end.isoformat(), "limit": limit, "offset": offset,
            "next_offset": offset + limit if more else None,
            "positions": [dict(row) for row in rows[:limit]]}
