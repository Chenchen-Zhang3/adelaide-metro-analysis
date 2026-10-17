
import pytest

from backend.analysis.aggregation import (
    aggregate_by_stop,
    find_delay_hotspots,
    prepare_analysis_output,
)

from backend.analysis.punctuality import (
    calculate_delay_minutes,
    classify_punctuality,
)

def test_punctuality_boundaries():
    assert classify_punctuality(-1) == "Early"
    assert classify_punctuality(0) == "On Time"
    assert classify_punctuality(5) == "On Time"
    assert classify_punctuality(5.1) == "Delayed"
    assert classify_punctuality(10) == "Delayed"
    assert classify_punctuality(10.1) == "Severely Delayed"


def test_delay_calculation():
    assert calculate_delay_minutes(1000, 1600) == 10
    assert calculate_delay_minutes(1600, 1000) == -10


@pytest.fixture
def sample_records():
    delays_a = [12] * 5 + [8] * 5 + [2] * 10
    delays_b = [15] * 2 + [3] * 18

    records = []

    for stop_id, delays in [
        ("A01", delays_a),
        ("B01", delays_b),
    ]:
        for delay in delays:
            records.append({
                "stop_id": stop_id,
                "route_id": "R1",
                "time_period": "Morning",
                "delay_minutes": delay,
            })

    return records


def test_stop_aggregation(sample_records):
    result = aggregate_by_stop(sample_records)

    assert result["A01"]["total_services"] == 20
    assert result["A01"]["severely_delayed_count"] == 5
    assert result["A01"]["delayed_count"] == 5
    assert result["A01"]["total_late_percentage"] == 50.0


def test_hotspot_ranking(sample_records):
    hotspots = find_delay_hotspots(
        sample_records, min_services=10
    )

    assert len(hotspots) == 2
    assert hotspots[0]["stop_id"] == "A01"
    assert hotspots[0]["rank"] == 1
    assert hotspots[1]["stop_id"] == "B01"


def test_minimum_services(sample_records):
    hotspots = find_delay_hotspots(
        sample_records, min_services=21
    )

    assert hotspots == []


def test_invalid_delay():
    records = [{
        "stop_id": "A01",
        "delay_minutes": None,
    }]

    with pytest.raises(ValueError):
        aggregate_by_stop(records)


def test_backend_output(sample_records):
    output = prepare_analysis_output(
        sample_records, min_services=10
    )

    assert "route_performance" in output
    assert "stop_performance" in output
    assert "time_period_performance" in output
    assert "delay_hotspots" in output
