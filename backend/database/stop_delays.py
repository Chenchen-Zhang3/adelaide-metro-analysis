"""Bounded v2 prediction aggregation; no schema or persistence changes."""
import sqlite3
import time

from backend.analysis.punctuality import classify_punctuality
from backend.database import repository

MAX_ROWS = 100_000
QUERY_SECONDS = 5


class StopDelayLimitError(ValueError):
    """The request cannot be safely completed within interactive limits."""


def query_stop_delays(start_epoch, end_epoch, route_id=None):
    """Use the observation index; return aggregates, never raw observations.

    Identity matches prepare_analysis_records: trip/stop/scheduled arrival.
    Latest means greatest observation instant, then greatest row ID for ties.
    The legacy Python path compares formatted timestamps; using actual instants
    here also orders correctly across an Adelaide daylight-saving fold.
    """
    where = "observed_at >= ? AND observed_at <= ?"
    params = [start_epoch, end_epoch]
    if route_id is not None:
        where += " AND route_id = ?"
        params.append(route_id)
    # Count all rows in the time slice, including other routes, so a sparse
    # route filter cannot bypass the maximum amount of index scanning.
    count_sql = """SELECT count(*) FROM (
        SELECT 1 FROM trip_updates INDEXED BY idx_trip_updates_observed
        WHERE observed_at >= ? AND observed_at <= ? LIMIT ?
    )"""
    sql = f"""
        WITH ranked AS (
            SELECT stop_id, delay_seconds, observed_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY trip_id, stop_id, scheduled_arrival
                       ORDER BY observed_at DESC, id DESC
                   ) AS revision
            FROM trip_updates INDEXED BY idx_trip_updates_observed
            WHERE {where}
        )
        SELECT stop_id, COUNT(*) AS prediction_sample_count,
               AVG(delay_seconds / 60.0) AS average_delay,
               SUM(is_on_time(delay_seconds / 60.0)) * 100.0 / COUNT(*)
                   AS on_time_percentage,
               MIN(observed_at) AS first_observed_at,
               MAX(observed_at) AS last_observed_at
        FROM ranked WHERE revision = 1
        GROUP BY stop_id ORDER BY stop_id
    """
    db = repository.get_connection()
    started = time.monotonic()
    try:
        db.set_progress_handler(
            lambda: int(time.monotonic() - started > QUERY_SECONDS), 1000
        )
        db.create_function("is_on_time", 1,
                           lambda delay: int(classify_punctuality(delay) == "On Time"))
        # Keep the guard and aggregation on one read snapshot if a collector
        # happens to write concurrently to a development database.
        db.execute("BEGIN")
        count = db.execute(count_sql, (start_epoch, end_epoch, MAX_ROWS + 1)).fetchone()[0]
        if count > MAX_ROWS:
            raise StopDelayLimitError("Window exceeds 100000 retained rows; narrow the time interval")
        rows = [dict(row) for row in db.execute(sql, params)]
        return rows, count
    except sqlite3.OperationalError as error:
        if "interrupted" in str(error):
            raise StopDelayLimitError("Query exceeded 5 seconds; narrow the time interval") from error
        raise
    finally:
        db.set_progress_handler(None, 0)
        db.close()
