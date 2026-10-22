from backend.analysis.punctuality import (
    calculate_delay_minutes,
    classify_punctuality,
)

from backend.analysis.metrics import (
    average_delay,
    delayed_rate,
    on_time_rate,
    severe_delay_rate,
)

from backend.analysis.aggregation import prepare_analysis_output


def test_delay_calculation():
    scheduled = 1000
    actual = 1420

    result = calculate_delay_minutes(scheduled, actual)

    assert result == 7


def test_early():
    assert classify_punctuality(-3) == "Early"


def test_on_time():
    assert classify_punctuality(3) == "On Time"


def test_delayed():
    assert classify_punctuality(7) == "Delayed"


def test_severely_delayed():
    assert classify_punctuality(12) == "Severely Delayed"


def test_average_delay():
    delays = [2, 5, 8, 10]

    assert average_delay(delays) == 6.25


def test_delayed_rate():
    delays = [2, 3, 7, 12]

    assert delayed_rate(delays) == 25.0


def test_on_time_rate():
    delays = [1, 3, 7, 12]

    assert on_time_rate(delays) == 50.0


def test_severe_delay_rate():
    delays = [2, 3, 7, 12]

    assert severe_delay_rate(delays) == 25.0


def test_validate_analysis_with_sample_data():
    sample_records = [
        {
            "route_id": "R1",
            "stop_id": "A01",
            "time_period": "Morning",
            "delay_minutes": 2,
        },
        {
            "route_id": "R1",
            "stop_id": "A01",
            "time_period": "Morning",
            "delay_minutes": 8,
        },
        {
            "route_id": "R2",
            "stop_id": "A02",
            "time_period": "Afternoon",
            "delay_minutes": -2,
        },
        {
            "route_id": "R2",
            "stop_id": "A02",
            "time_period": "Afternoon",
            "delay_minutes": 12,
        },
    ]

    result = prepare_analysis_output(
    sample_records,
    min_services=2,
)

    # Validate route-level results
    assert result["route_performance"]["R1"]["total_services"] == 2
    assert result["route_performance"]["R1"]["average_delay"] == 5.0
    assert result["route_performance"]["R1"]["on_time_count"] == 1
    assert result["route_performance"]["R1"]["delayed_count"] == 1
    assert result["route_performance"]["R1"]["on_time_percentage"] == 50.0
    assert result["route_performance"]["R1"]["delayed_percentage"] == 50.0

    assert result["route_performance"]["R2"]["early_count"] == 1
    assert (
        result["route_performance"]["R2"]["severely_delayed_count"]
        == 1
    )
    assert result["route_performance"]["R2"]["early_percentage"] == 50.0
    assert (
        result["route_performance"]["R2"]["severe_delay_percentage"]
        == 50.0
    )

    # Validate stop-level results
    assert result["stop_performance"]["A01"]["average_delay"] == 5.0
    assert result["stop_performance"]["A01"]["on_time_percentage"] == 50.0
    assert result["stop_performance"]["A01"]["delayed_percentage"] == 50.0

    assert result["stop_performance"]["A02"]["average_delay"] == 5.0
    assert result["stop_performance"]["A02"]["early_percentage"] == 50.0
    assert (
        result["stop_performance"]["A02"]["severe_delay_percentage"]
        == 50.0
    )

    # Validate time-period results
    assert result["time_period_performance"]["Morning"]["on_time_count"] == 1
    assert result["time_period_performance"]["Morning"]["delayed_count"] == 1
    assert (
        result["time_period_performance"]["Morning"]["on_time_percentage"]
        == 50.0
    )
    assert (
        result["time_period_performance"]["Morning"]["delayed_percentage"]
        == 50.0
    )

    assert result["time_period_performance"]["Afternoon"]["early_count"] == 1
    assert (
        result["time_period_performance"]["Afternoon"][
            "severely_delayed_count"
        ]
        == 1
    )

    # Validate delay hotspot output
    assert "delay_hotspots" in result
    assert len(result["delay_hotspots"]) == 2


from backend.services.pipeline import prepare_analysis_records


def test_latest_prediction_deduplication():
    records = [
        {
            "trip_id": "T1",
            "route_id": "R1",
            "stop_id": "S1",
            "scheduled_arrival": "2026-10-22T10:00:00+10:30",
            "delay_seconds": 120,
            "timestamp": "2026-10-22T09:50:00+10:30",
        },
        {
            "trip_id": "T1",
            "route_id": "R1",
            "stop_id": "S1",
            "scheduled_arrival": "2026-10-22T10:00:00+10:30",
            "delay_seconds": 480,
            "timestamp": "2026-10-22T09:55:00+10:30",
        },
    ]

    result = prepare_analysis_records(records)

    assert len(result) == 1
    assert result[0]["delay_minutes"] == 8
    assert result[0]["punctuality_status"] == "Delayed"
    assert result[0]["data_type"] == "realtime_prediction"


def test_multiple_scheduled_arrivals():
    records = [
        {
            "trip_id": "T1",
            "route_id": "R1",
            "stop_id": "S1",
            "scheduled_arrival": "2026-10-22T10:00:00+10:30",
            "delay_seconds": 300,
            "timestamp": "2026-10-22T09:50:00+10:30",
        },
        {
            "trip_id": "T2",
            "route_id": "R1",
            "stop_id": "S1",
            "scheduled_arrival": "2026-10-22T10:15:00+10:30",
            "delay_seconds": 720,
            "timestamp": "2026-10-22T10:05:00+10:30",
        },
    ]

    result = prepare_analysis_records(records)

    assert len(result) == 2
    assert result[0]["punctuality_status"] == "On Time"
    assert result[1]["punctuality_status"] == "Severely Delayed"

from backend.services.pipeline import prepare_analysis_records


def test_latest_prediction_deduplication():
    records = [
        {
            "trip_id": "T1",
            "route_id": "R1",
            "stop_id": "S1",
            "scheduled_arrival": "2026-10-22T10:00:00+10:30",
            "delay_seconds": 120,
            "timestamp": "2026-10-22T09:50:00+10:30",
        },
        {
            "trip_id": "T1",
            "route_id": "R1",
            "stop_id": "S1",
            "scheduled_arrival": "2026-10-22T10:00:00+10:30",
            "delay_seconds": 480,
            "timestamp": "2026-10-22T09:55:00+10:30",
        },
    ]

    result = prepare_analysis_records(records)

    assert len(result) == 1
    assert result[0]["delay_minutes"] == 8
    assert result[0]["punctuality_status"] == "Delayed"
    assert result[0]["data_type"] == "realtime_prediction"


def test_multiple_scheduled_arrivals():
    records = [
        {
            "trip_id": "T1",
            "route_id": "R1",
            "stop_id": "S1",
            "scheduled_arrival": "2026-10-22T10:00:00+10:30",
            "delay_seconds": 300,
            "timestamp": "2026-10-22T09:50:00+10:30",
        },
        {
            "trip_id": "T2",
            "route_id": "R1",
            "stop_id": "S1",
            "scheduled_arrival": "2026-10-22T10:15:00+10:30",
            "delay_seconds": 720,
            "timestamp": "2026-10-22T10:05:00+10:30",
        },
    ]

    result = prepare_analysis_records(records)

    assert len(result) == 2
    assert result[0]["punctuality_status"] == "On Time"
    assert result[1]["punctuality_status"] == "Severely Delayed"