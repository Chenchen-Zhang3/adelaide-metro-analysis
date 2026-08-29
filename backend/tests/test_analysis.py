from backend.analysis.punctuality import (
    calculate_delay_minutes,
    classify_punctuality,
)

from backend.analysis.metrics import (
    average_delay,
    delay_frequency,
    on_time_rate,
)


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


def test_delay_frequency():
    delays = [2, 3, 7, 12]

    assert delay_frequency(delays) == 50.0


def test_on_time_rate():
    delays = [1, 3, 7, 12]

    assert on_time_rate(delays) == 50.0