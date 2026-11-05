"""Compact, explicitly scoped historical prediction statistics for map stops."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from backend.database.stop_delays import query_stop_delays
from backend.services import static_map_data
from backend.services.recorded_map_data import MapDataUnavailableError


def _iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def query_network_stop_delays(start_time, end_time, route_id=None,
                             min_samples="10", scope="observed"):
    bounds = []
    for name, value in (("start_time", start_time), ("end_time", end_time)):
        try:
            dt = datetime.fromisoformat(value)
            if dt.utcoffset() is None:
                raise ValueError()
            bounds.append(dt.astimezone(timezone.utc))
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"{name} is required and must be ISO 8601 with a UTC offset") from error
    start, end = bounds
    if not 0 <= (end - start).total_seconds() <= 3600:
        raise ValueError("Window must be ordered and at most 3600 seconds (inclusive boundaries)")
    if not isinstance(min_samples, str) or not min_samples.isascii() or not min_samples.isdecimal():
        raise ValueError("min_samples must be an integer from 1 to 100000")
    threshold = int(min_samples)
    if not 1 <= threshold <= 100000:
        raise ValueError("min_samples must be an integer from 1 to 100000")
    if scope not in ("observed", "static"):
        raise ValueError("scope must be observed or static")
    if route_id is not None and (not route_id.strip() or len(route_id) > 128):
        raise ValueError("route_id must be a nonempty string of at most 128 characters")

    eligible = None
    static_meta = None
    if scope == "static":
        # Reuse the publisher's validated manifest/catalog readers. Only exact
        # platform/stop IDs are eligible; never roll observations up to parents.
        catalog = static_map_data.load_catalog()
        try:
            _, manifest = static_map_data._manifest(None)
            feed = manifest["feed_info"]
            lo = datetime.strptime(feed["feed_start_date"], "%Y%m%d").date()
            hi = datetime.strptime(feed["feed_end_date"], "%Y%m%d").date()
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise MapDataUnavailableError("Static feed validity metadata is missing or invalid") from error
        local = ZoneInfo("Australia/Adelaide")
        if start.astimezone(local).date() < lo or end.astimezone(local).date() > hi:
            raise ValueError("Window is outside the configured static feed validity dates")
        if route_id is not None and route_id not in {r["route_id"] for r in catalog["routes"]}:
            raise ValueError("route_id is not in the selected static catalog")
        eligible = {s["stop_id"] for s in catalog["stops"]
                    if str(s.get("location_type") or "0") == "0"
                    and (route_id is None or route_id in s.get("route_ids", []))}
        static_meta = {"version": manifest["static_feed_version"],
                       "valid_from": lo.isoformat(), "valid_to": hi.isoformat(),
                       "eligible_stop_count": len(eligible),
                       "parent_station_rollup": False}

    rows, scanned = query_stop_delays(start.timestamp(), end.timestamp(), route_id)
    stops, excluded = [], []
    for row in rows:
        if eligible is not None and row["stop_id"] not in eligible:
            excluded.append(row["stop_id"])
            continue
        available = row["prediction_sample_count"] >= threshold
        stops.append({"stop_id": str(row["stop_id"]),
                      "average_predicted_delay_minutes": round(row["average_delay"], 2) if available else None,
                      "predicted_on_time_percentage": round(row["on_time_percentage"], 2) if available else None,
                      "prediction_sample_count": row["prediction_sample_count"],
                      "data_status": "available" if available else "insufficient_data",
                      "first_selected_observation_time": _iso(row["first_observed_at"]),
                      "last_selected_observation_time": _iso(row["last_observed_at"])})
    return {
        "data_source": "historical_trip_update_predictions",
        "start_time": start.isoformat(), "end_time": end.isoformat(),
        "interval": "inclusive", "route_id": route_id, "scope": scope,
        "historical_route_scope": "explicit route_id" if route_id is not None else "all stored routes; static scope filters stop membership only",
        "aggregation_unit": "latest_prediction_per_stop_visit",
        "visit_identity": ["trip_id", "stop_id", "scheduled_arrival"],
        "tie_break": "greatest observed_at, then greatest row id",
        "min_samples": threshold, "on_time_delay_minutes": {"min": 0, "max": 5, "inclusive": True},
        "missing_stop_policy": "Absent eligible IDs have no_data; use null metrics and zero samples. IDs outside the scope are excluded, not no_data.",
        "static_catalog": static_meta,
        "excluded_observed_stop_ids": excluded,
        "coverage": {"returned_stop_count": len(stops),
                     "prediction_sample_count": sum(s["prediction_sample_count"] for s in stops),
                     "window_retained_row_count_before_route_filter": scanned,
                     "no_data_stop_count": len(eligible) - len(stops) if eligible is not None else None},
        "limitations": "Retained predictions, not confirmed actual arrivals; missing observations do not establish service completeness or stop_sequence compatibility.",
        "stops": stops,
    }
