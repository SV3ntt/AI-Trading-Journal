import math 

import pytest 

from journal.calculations import (
    calculate_dollar_pnl,
    calculate_duration, 
    calculate_net_dollar_pnl,
    calculate_net_result,
    calculate_points_pnl,
    calculate_pips_pnl,
    calculate_realized_r,
    calculate_result,
    calculate_ticks_pnl,
    clean_float_noise,
    get_finite_number, 
    get_positive_integer, 
    is_multiple_of,
    normalize_date_value, 
    normalize_time_value,
)

def test_calculate_points_pnl_for_long_win():
    result = calculate_points_pnl("long", 100.0, 105.0)

    assert result == 5.0

def test_calculate_points_pnl_for_long_loss():
    result = calculate_points_pnl("long", 105.0, 100.0)

    assert result == -5.0

def test_calculate_points_pnl_for_short_win():
    result = calculate_points_pnl("short", 105.0, 100.0)

    assert result == 5.0

def test_calculate_points_pnl_for_short_loss():
    result = calculate_points_pnl("short", 100.0, 105.0)

    assert result == -5.0

def test_calculate_dollar_pnl_for_winning_trade():
    result = calculate_dollar_pnl(10.25, 5.0, 2)

    assert result == 102.50

def test_calculate_dollar_pnl_for_losing_trade():
    result = calculate_dollar_pnl(-4.0, 2.0, 3)

    assert result == -24.0

def test_calculate_net_dollar_pnl_for_win():
    result = calculate_net_dollar_pnl(100.0, 4.50)

    assert result == 95.50

def test_calculate_net_dollar_pnl_for_loss():
    result = calculate_net_dollar_pnl(-100.0, 4.50)

    assert result == -104.50

def test_calculate_realized_r_for_win():
    result = calculate_realized_r(150.0, 100.0)

    assert result == 1.5

def test_calculate_realized_r_for_loss():
    result = calculate_realized_r(-50.0, 100.0)

    assert result == -0.5

@pytest.mark.parametrize("risk_amount", [0, -100.0])
def test_calculate_realized_r_returns_zero_for_non_positive_risk(
    risk_amount
):
    result = calculate_realized_r(100.0, risk_amount)

    assert result == 0

@pytest.mark.parametrize(
    ("points_pnl", "expected"), 
    [
        (5.0, "Win"),
        (-5.0, "Loss"),
        (0.0, "Break-even"),
    ],
)
def test_calculate_result(points_pnl, expected):
    result = calculate_result(points_pnl)

    assert result == expected

@pytest.mark.parametrize(
    ("net_dollar_pnl", "expected"),
    [
        (25.0, "Win"),
        (-25.0, "Loss"),
        (0.0, "Break-even"),
    ],
)
def test_calculate_net_result(net_dollar_pnl, expected):
    result = calculate_net_result(net_dollar_pnl)

    assert result == expected

def test_is_multiple_of_returns_true_for_exact_multiple():
    assert is_multiple_of(10.25, 0.25) is True

def test_is_multiple_of_handles_floating_point_noise():
    assert is_multiple_of(0.3, 0.1) is True

def test_is_multiple_of_returns_false_for_non_multiple():
    assert is_multiple_of(10.10, 0.25) is False

@pytest.mark.parametrize("unit", [0, -0.25])
def test_is_multiple_of_returns_false_for_non_positive_unit(unit):
    assert is_multiple_of(10.0, unit) is False

def test_clean_float_noise_cleans_near_integer():
    result = clean_float_noise(40.0000000001)

    assert result == 40.0

def test_clean_float_noise_cleans_decimal_noise():
    result = clean_float_noise(0.30000000000000004)

    assert result == 0.3

def test_clean_float_noise_keeps_precision_within_tolerance():
    result = clean_float_noise(1.23456789)

    assert result == 1.234568
    
def test_calculate_ticks_pnl_for_profit():
    result = calculate_ticks_pnl(10.25, 0.25)

    assert result == 41.0

def test_calculate_ticks_pnl_for_loss():
    result = calculate_ticks_pnl(-2.5, 0.25)

    assert result == -10.0

def test_calculate_pips_pnl_for_standard_pair():
    result = calculate_pips_pnl(0.0017, 0.0001)

    assert result == 17.0

def test_calculate_pips_pnl_for_jpy_pair():
    result = calculate_pips_pnl(0.17, 0.01)

    assert result == 17.0

def test_calculate_duration_for_same_day_trade():
    result = calculate_duration("09:30", "10:45")

    assert result == 75

def test_calculate_duration_for_overnight_trade():
    result = calculate_duration("23:30", "00:15")

    assert result == 45

def test_calculate_duration_for_matching_times():
    result = calculate_duration("09:30", "09:30")

    assert result == 0

def test_get_finite_number_converts_numeric_string():
    result = get_finite_number("12.5", "Price")

    assert result == 12.5

def test_get_finite_number_accepts_inclusive_minimum():
    result = get_finite_number(0, "Commission", minimum=0)
    assert result == 0.0

def test_get_finite_number_accepts_value_above_strict_minumim():
    result = get_finite_number(
        0.01, 
        "Risk",
        minimum=0,
        minimum_is_strict=True,
    )

    assert result == 0.01

@pytest.mark.parametrize("value", [True, False, "abc", None])
def test_get_finite_number_rejects_non_numbers(value):
    with pytest.raises(ValueError, match="must be a number"):
        get_finite_number(value, "Price")

@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
def test_get_finite_number_rejects_non_finite_numbers(value):
    with pytest.raises(ValueError, match="must be a finite number"):
        get_finite_number(value, "Price")

def test_get_finite_number_rejects_value_below_inclusive_minimum():
    with pytest.raises(
        ValueError,
        match="must be greater than or equal to 0"
    ):
        get_finite_number(-1, "Commission", minimum=0)

def test_get_finite_number_rejects_value_equal_to_strict_minimum():
    with pytest.raises(ValueError, match="greater than 0"):
        get_finite_number(
            0, 
            "Risk",
            minimum=0,
            minimum_is_strict=True,
        )

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, 1),
        (3.0, 3),
        ("5", 5),
    ],
)
def test_get_positive_integer_accepts_positive_whole_numbers(
    value, 
    expected,
):
    result = get_positive_integer(value, "Contracts")

    assert result == expected
    assert isinstance(result, int)


@pytest.mark.parametrize(
    "value",
    [0, -1, 1.5, True, False, math.inf, math.nan, "abt", None], 
)
def test_get_positive_integer_rejects_invalid_values(value):
    with pytest.raises(
        ValueError,
        match="must be a whole number greater than 0"
    ):
        get_positive_integer(value, "Contracts")

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-07-30", "2026-07-30"),
        (" 2026-07-30", "2026-07-30"),
        ("2026 07 30", "2026-07-30"),
    ], 
)
def test_normalize_date_value(value, expected):
    assert normalize_date_value(value) == expected

@pytest.mark.parametrize(
    "value", 
    ["2026-02-30", "07-30-2026", "not-a-date", "2026/13/01", "2026-00-10", "2026-01-00"],
)
def test_normalize_date_value_rejects_invalid_dates(value):
    with pytest.raises(ValueError):
        normalize_date_value(value)

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("09:05", "09:05"),
        (" 09:05", "09:05"),
        ("9:05", "09:05"),
    ],
)
def test_normalize_time_value(value, expected):
    assert normalize_time_value(value) == expected

@pytest.mark.parametrize(
    "value", 
    ["24:00", "09:60", "not-a-time"],
)
def test_normalize_time_value_rejects_invalid_times(value):
    with pytest.raises(ValueError):
        normalize_time_value(value)
