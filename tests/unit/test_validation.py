import copy

import pytest

from journal.constants import (
    FOREX_ONLY_FIELDS,
    FUTURES_ONLY_FIELDS,
    STANDARD_LOT_UNITS,
)
from journal.validation import (
    validate_and_normalize_account,
    validate_and_normalize_trade,
)


def make_futures_trade(**overrides):
    trade = {
        "symbol": "MES",
        "direction": "long",
        "market_type": "futures",
        "entry": 7500.25,
        "exit": 7510.50,
        "contracts": 2,
        "point_value": 5.0,
        "risk_amount": 100.0,
        "commission": 4.0,
        "trade_date": "2026-07-30",
        "entry_time": "09:30",
        "exit_time": "10:00",
        "strategy_method": "ICT",
        "setup": "FVG",
        "notes": "  Patient entry  ",
        "mistake": "  None  ",
    }
    trade.update(overrides)
    return trade


def make_forex_trade(**overrides):
    trade = {
        "symbol": "EURUSD",
        "direction": "long",
        "market_type": "forex",
        "entry": 1.10000,
        "exit": 1.10150,
        "lot_size": 1.0,
        "pip_value": 10.0,
        "risk_amount": 100.0,
        "commission": 2.0,
        "trade_date": "2026-07-30",
        "entry_time": "09:30",
        "exit_time": "10:00",
        "strategy_method": "ICT",
        "setup": "FVG",
        "notes": "FX trade",
        "mistake": "",
    }
    trade.update(overrides)
    return trade


def make_account(**overrides):
    account = {
        "name": "Main Account",
        "type": "Personal",
        "starting_balance": 25000.0,
        "high_water_mark": 26000.0,
        "account_currency": "USD",
    }
    account.update(overrides)
    return account


def test_validate_trade_rejects_non_dictionary():
    result, errors = validate_and_normalize_trade([])

    assert result is None
    assert errors == ["Trade record must be a JSON object."]


def test_validate_known_futures_trade_calculates_and_normalizes_fields():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade()
    )

    assert errors == []
    assert normalized["symbol"] == "mes"
    assert normalized["direction"] == "long"
    assert normalized["market_type"] == "futures"
    assert normalized["entry"] == 7500.25
    assert normalized["exit"] == 7510.50
    assert normalized["contracts"] == 2
    assert normalized["tick_size"] == 0.25
    assert normalized["tick_value"] == 1.25
    assert normalized["point_value"] == 5.0
    assert normalized["points_pnl"] == 10.25
    assert normalized["ticks_pnl"] == 41.0
    assert normalized["dollar_pnl"] == 102.5
    assert normalized["commission"] == 4.0
    assert normalized["net_dollar_pnl"] == 98.5
    assert normalized["risk_amount"] == 100.0
    assert normalized["realized_r"] == 1.025
    assert normalized["result"] == "Win"
    assert normalized["net_result"] == "Win"
    assert normalized["trade_date"] == "2026-07-30"
    assert normalized["entry_time"] == "09:30"
    assert normalized["exit_time"] == "10:00"
    assert normalized["duration"] == 30
    assert normalized["session"] == "New York/London Overlap"
    assert normalized["strategy_methods"] == ["ICT"]
    assert normalized["setup_components"] == [
        "Fair Value Gap (FVG)"
    ]
    assert normalized["notes"] == "Patient entry"
    assert normalized["mistake"] == "None"


def test_validate_trade_does_not_mutate_original_dictionary():
    trade = make_futures_trade(
        strategy_methods=["ict", "orderflow"],
        setup_components=["FVG", "OB"],
    )
    original = copy.deepcopy(trade)

    validate_and_normalize_trade(trade)

    assert trade == original


def test_validate_trade_preserves_unrelated_extra_fields():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(custom_tag="A+ setup")
    )

    assert errors == []
    assert normalized["custom_tag"] == "A+ setup"


def test_missing_market_type_migrates_legacy_trade_to_futures():
    trade = make_futures_trade()
    trade.pop("market_type")

    normalized, errors = validate_and_normalize_trade(trade)

    assert errors == []
    assert normalized["market_type"] == "futures"
    assert normalized["symbol"] == "mes"


def test_known_futures_contract_symbol_infers_tick_metadata():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(symbol="MESZ26")
    )

    assert errors == []
    assert normalized["symbol"] == "mesz26"
    assert normalized["tick_size"] == 0.25
    assert normalized["tick_value"] == 1.25


def test_unknown_futures_symbol_can_use_point_value_without_ticks():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            symbol="CUSTOM",
            entry=100.0,
            exit=102.5,
            point_value=20.0,
            contracts=3,
        )
    )

    assert errors == []
    assert normalized["tick_size"] is None
    assert normalized["tick_value"] is None
    assert normalized["ticks_pnl"] is None
    assert normalized["points_pnl"] == 2.5
    assert normalized["dollar_pnl"] == 150.0


def test_explicit_futures_tick_metadata_derives_point_value():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            symbol="ES",
            entry=5000.25,
            exit=5001.00,
            contracts=1,
            tick_size=0.25,
            tick_value=12.50,
            point_value=999.0,
        )
    )

    assert errors == []
    assert normalized["tick_size"] == 0.25
    assert normalized["tick_value"] == 12.50
    assert normalized["point_value"] == 50.0
    assert normalized["ticks_pnl"] == 3.0
    assert normalized["dollar_pnl"] == 37.5


def test_incomplete_tick_metadata_uses_point_value_fallback():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(tick_size=0.50)
    )

    assert errors == []
    assert normalized["tick_size"] == 0.25
    assert normalized["tick_value"] == 1.25
    assert normalized["point_value"] == 5.0


def test_short_futures_trade_calculates_profit_correctly():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            direction=" SHORT ",
            entry=7510.50,
            exit=7500.25,
        )
    )

    assert errors == []
    assert normalized["direction"] == "short"
    assert normalized["points_pnl"] == 10.25
    assert normalized["result"] == "Win"


def test_commission_can_change_gross_win_to_net_loss():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            entry=7500.00,
            exit=7500.25,
            contracts=1,
            commission=2.00,
        )
    )

    assert errors == []
    assert normalized["dollar_pnl"] == 1.25
    assert normalized["net_dollar_pnl"] == -0.75
    assert normalized["result"] == "Win"
    assert normalized["net_result"] == "Loss"
    assert normalized["realized_r"] == pytest.approx(0.0125)


def test_break_even_trade_with_commission_is_net_loss():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(entry=7500.00, exit=7500.00)
    )

    assert errors == []
    assert normalized["points_pnl"] == 0.0
    assert normalized["result"] == "Break-even"
    assert normalized["net_result"] == "Loss"


def test_overnight_trade_duration_crosses_midnight():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            entry_time="23:50",
            exit_time="00:20",
        )
    )

    assert errors == []
    assert normalized["duration"] == 30
    assert normalized["session"] == "Sydney/Asia Overlap"


def test_trade_date_and_times_are_normalized():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            trade_date=" 2026 07 30 ",
            entry_time=" 09:30 ",
            exit_time=" 10:00 ",
        )
    )

    assert errors == []
    assert normalized["trade_date"] == "2026-07-30"
    assert normalized["entry_time"] == "09:30"
    assert normalized["exit_time"] == "10:00"


def test_none_notes_and_mistake_become_empty_strings():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(notes=None, mistake=None)
    )

    assert errors == []
    assert normalized["notes"] == ""
    assert normalized["mistake"] == ""


def test_unspecified_strategy_and_setup_become_empty_lists():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            strategy_method="",
            setup="",
        )
    )

    assert errors == []
    assert normalized["strategy_methods"] == []
    assert normalized["setup_components"] == []


def test_stored_strategy_and_setup_lists_are_normalized():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            strategy_methods=["ict", "footprint", "ICT"],
            setup_components=["FVG", "OB", "fvg"],
        )
    )

    assert errors == []
    assert normalized["strategy_methods"] == ["ICT", "Order Flow"]
    assert normalized["setup_components"] == [
        "Fair Value Gap (FVG)",
        "Order Block",
    ]


def test_futures_normalization_removes_all_forex_only_fields():
    trade = make_futures_trade()
    for field in FOREX_ONLY_FIELDS:
        trade[field] = "stale"

    normalized, errors = validate_and_normalize_trade(trade)

    assert errors == []
    for field in FOREX_ONLY_FIELDS:
        assert field not in normalized


@pytest.mark.parametrize(
    ("direction", "expected_points", "expected_result"),
    [
        ("long", -10.25, "Loss"),
        ("short", 10.25, "Win"),
    ],
)
def test_direction_controls_points_pnl(
    direction,
    expected_points,
    expected_result,
):
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            direction=direction,
            entry=7510.50,
            exit=7500.25,
        )
    )

    assert errors == []
    assert normalized["points_pnl"] == expected_points
    assert normalized["result"] == expected_result


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("entry", None, "Entry price must be a number. "),
        ("entry", 0, "Entry price must be greater than 0. "),
        ("exit", -1, "Exit price must be greater than 0. "),
        ("risk_amount", 0, "Risk amount must be greater than 0. "),
        (
            "commission",
            -0.01,
            "Commission must be greater than or equal to 0. ",
        ),
        ("entry", True, "Entry price must be a number. "),
        ("exit", float("inf"), "Exit price must be a finite number. "),
        ("risk_amount", float("nan"), "Risk amount must be a finite number. "),
    ],
)
def test_invalid_shared_numeric_field_is_rejected(
    field,
    value,
    expected_error,
):
    trade = make_futures_trade()
    trade[field] = value

    normalized, errors = validate_and_normalize_trade(trade)

    assert normalized is None
    assert expected_error in errors


@pytest.mark.parametrize("contracts", [None, 0, -1, 1.5, True, "two"])
def test_invalid_contracts_are_rejected(contracts):
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(contracts=contracts)
    )

    assert normalized is None
    assert (
        "Contracts must be a whole number greater than 0."
        in errors
    )


@pytest.mark.parametrize("point_value", [None, 0, -5, True, "bad"])
def test_invalid_point_value_is_rejected(point_value):
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            symbol="CUSTOM",
            point_value=point_value,
        )
    )

    assert normalized is None
    assert any(error.startswith("Point value must") for error in errors)


@pytest.mark.parametrize(
    ("field", "value", "error_text"),
    [
        ("tick_size", 0, "Tick size must be greater than 0. "),
        ("tick_size", "bad", "Tick size must be a number. "),
        ("tick_value", -1, "Tick value must be greater than 0. "),
        ("tick_value", float("inf"), "Tick value must be a finite number. "),
    ],
)
def test_invalid_explicit_tick_metadata_is_rejected(
    field,
    value,
    error_text,
):
    trade = make_futures_trade(
        symbol="CUSTOM",
        tick_size=0.25,
        tick_value=1.25,
    )
    trade[field] = value

    normalized, errors = validate_and_normalize_trade(trade)

    assert normalized is None
    assert error_text in errors


@pytest.mark.parametrize(
    ("field", "value", "label"),
    [
        ("entry", 5000.10, "Entry price"),
        ("exit", 5001.10, "Exit price"),
    ],
)
def test_futures_price_must_align_with_explicit_tick_size(
    field,
    value,
    label,
):
    trade = make_futures_trade(
        symbol="ES",
        entry=5000.25,
        exit=5001.00,
        tick_size=0.25,
        tick_value=12.50,
    )
    trade[field] = value

    normalized, errors = validate_and_normalize_trade(trade)

    assert normalized is None
    assert (
        f"{label} must align with a tick size of 0.25."
        in errors
    )


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("symbol", "", "Symbol cannot be blank."),
        ("direction", "buy", "Direction must be long or short."),
        (
            "market_type",
            "stocks",
            "Market type must be futures or forex.",
        ),
        (
            "trade_date",
            "2026-02-30",
            "Trade date must be in YYYY-MM-DD format.",
        ),
        (
            "entry_time",
            "24:00",
            "Entry time must use 24-hour format HH:MM 24-hour format.",
        ),
        (
            "exit_time",
            "not-a-time",
            "Exit time must use 24-hour format HH:MM.",
        ),
    ],
)
def test_invalid_common_text_or_datetime_field_is_rejected(
    field,
    value,
    expected_error,
):
    trade = make_futures_trade()
    trade[field] = value

    normalized, errors = validate_and_normalize_trade(trade)

    assert normalized is None
    assert expected_error in errors


def test_trade_validation_collects_multiple_errors():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            symbol="",
            direction="buy",
            entry="bad",
            risk_amount=0,
            contracts=0,
            trade_date="bad",
            entry_time="bad",
        )
    )

    assert normalized is None
    assert len(errors) == 7
    assert "Symbol cannot be blank." in errors
    assert "Direction must be long or short." in errors


def test_calculated_overflow_is_rejected_safely():
    normalized, errors = validate_and_normalize_trade(
        make_futures_trade(
            symbol="CUSTOM",
            entry=1.0,
            exit=1e308,
            point_value=1e308,
            contracts=2,
        )
    )

    assert normalized is None
    assert errors == [
        "Calculated trade values are too large to store safely."
    ]


def test_validate_standard_forex_trade_calculates_and_normalizes_fields():
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade()
    )

    assert errors == []
    assert normalized["symbol"] == "eur/usd"
    assert normalized["market_type"] == "forex"
    assert normalized["lot_size"] == 1.0
    assert normalized["pip_size"] == 0.0001
    assert normalized["pip_value"] == 10.0
    assert normalized["price_precision"] == 5
    assert normalized["pips_pnl"] == pytest.approx(15.0)
    assert normalized["dollar_pnl"] == pytest.approx(150.0)
    assert normalized["net_dollar_pnl"] == pytest.approx(148.0)
    assert normalized["realized_r"] == pytest.approx(1.5)
    assert normalized["standard_lot_units"] == STANDARD_LOT_UNITS
    assert normalized["account_currency"] is None
    assert normalized["conversion_rate"] is None
    assert normalized["conversion_pair"] is None
    assert normalized["conversion_timestamp"] is None
    assert normalized["conversion_rate_source"] is None
    assert normalized["result"] == "Win"
    assert normalized["net_result"] == "Win"


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("EURUSD", "eur/usd"),
        ("EUR/USD", "eur/usd"),
        ("eur-usd", "eur/usd"),
        (" EUR USD ", "eur/usd"),
    ],
)
def test_forex_symbol_is_normalized(symbol, expected):
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(symbol=symbol)
    )

    assert errors == []
    assert normalized["symbol"] == expected


def test_jpy_quote_pair_uses_standard_jpy_profile():
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(
            symbol="USDJPY",
            direction="short",
            entry=150.000,
            exit=149.920,
            pip_value=6.70,
        )
    )

    assert errors == []
    assert normalized["symbol"] == "usd/jpy"
    assert normalized["pip_size"] == 0.01
    assert normalized["price_precision"] == 3
    assert normalized["pips_pnl"] == pytest.approx(8.0)
    assert normalized["dollar_pnl"] == pytest.approx(53.6)


def test_standard_forex_profile_overrides_stored_pip_metadata():
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(
            pip_size="stale",
            price_precision="stale",
        )
    )

    assert errors == []
    assert normalized["pip_size"] == 0.0001
    assert normalized["price_precision"] == 5


def test_custom_forex_pair_uses_supplied_pip_profile():
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(
            symbol="XAU/USD",
            entry=2300.10,
            exit=2301.25,
            pip_size=0.01,
            price_precision=2,
            pip_value=1.0,
        )
    )

    assert errors == []
    assert normalized["symbol"] == "xau/usd"
    assert normalized["pip_size"] == 0.01
    assert normalized["price_precision"] == 2
    assert normalized["pips_pnl"] == pytest.approx(115.0)
    assert normalized["dollar_pnl"] == pytest.approx(115.0)


def test_forex_conversion_metadata_is_normalized_and_preserved():
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(
            account_currency=" cad ",
            conversion_rate="1.36",
            conversion_pair="USD/CAD",
            conversion_timestamp="2026-07-30T10:00",
            conversion_rate_source="historical_market_data",
        )
    )

    assert errors == []
    assert normalized["account_currency"] == "CAD"
    assert normalized["conversion_rate"] == 1.36
    assert normalized["conversion_pair"] == "USD/CAD"
    assert normalized["conversion_timestamp"] == "2026-07-30T10:00"
    assert normalized["conversion_rate_source"] == "historical_market_data"


def test_blank_forex_conversion_metadata_becomes_none():
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(
            account_currency="",
            conversion_rate="",
            conversion_pair="",
            conversion_timestamp="",
            conversion_rate_source="",
        )
    )

    assert errors == []
    assert normalized["account_currency"] is None
    assert normalized["conversion_rate"] is None
    assert normalized["conversion_pair"] is None
    assert normalized["conversion_timestamp"] is None
    assert normalized["conversion_rate_source"] is None


def test_forex_trade_account_currency_is_uppercased_without_account_validation():
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(account_currency=" xyz ")
    )

    assert errors == []
    assert normalized["account_currency"] == "XYZ"


def test_forex_normalization_removes_all_futures_only_fields():
    trade = make_forex_trade()
    for field in FUTURES_ONLY_FIELDS:
        trade[field] = "stale"

    normalized, errors = validate_and_normalize_trade(trade)

    assert errors == []
    for field in FUTURES_ONLY_FIELDS:
        assert field not in normalized


@pytest.mark.parametrize("lot_size", [None, 0, -1, True, "bad"])
def test_invalid_forex_lot_size_is_rejected(lot_size):
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(lot_size=lot_size)
    )

    assert normalized is None
    assert any(error.startswith("Lot size must") for error in errors)


@pytest.mark.parametrize("pip_value", [None, 0, -1, True, "bad"])
def test_invalid_forex_pip_value_is_rejected(pip_value):
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(pip_value=pip_value)
    )

    assert normalized is None
    assert any(error.startswith("Pip value must") for error in errors)


@pytest.mark.parametrize(
    ("field", "value", "error_start"),
    [
        ("pip_size", None, "Pip size must"),
        ("pip_size", 0, "Pip size must"),
        ("pip_size", "bad", "Pip size must"),
        ("price_precision", None, "Price precision must"),
        ("price_precision", 0, "Price precision must"),
        ("price_precision", 2.5, "Price precision must"),
    ],
)
def test_custom_forex_pair_requires_valid_pip_profile(
    field,
    value,
    error_start,
):
    trade = make_forex_trade(
        symbol="XAU/USD",
        entry=2300.10,
        exit=2301.25,
        pip_size=0.01,
        price_precision=2,
    )
    trade[field] = value

    normalized, errors = validate_and_normalize_trade(trade)

    assert normalized is None
    assert any(error.startswith(error_start) for error in errors)


@pytest.mark.parametrize(
    ("field", "value", "label"),
    [
        ("entry", 1.123456, "Entry price"),
        ("exit", 1.123456, "Exit price"),
    ],
)
def test_standard_forex_price_cannot_exceed_pair_precision(
    field,
    value,
    label,
):
    trade = make_forex_trade(entry=1.12345, exit=1.12355)
    trade[field] = value

    normalized, errors = validate_and_normalize_trade(trade)

    assert normalized is None
    assert (
        f"{label} cannot exceed 5 decimal places for this pair."
        in errors
    )


@pytest.mark.parametrize(
    "conversion_rate",
    [0, -1, True, "bad", float("inf")],
)
def test_invalid_supplied_conversion_rate_is_rejected(conversion_rate):
    normalized, errors = validate_and_normalize_trade(
        make_forex_trade(conversion_rate=conversion_rate)
    )

    assert normalized is None
    assert any(error.startswith("Conversion rate must") for error in errors)


def test_validate_account_rejects_non_dictionary():
    result, errors = validate_and_normalize_account([])

    assert result is None
    assert errors == ["Account data must be a JSON object."]


def test_validate_account_normalizes_all_fields():
    normalized, errors = validate_and_normalize_account(
        make_account(
            name="  Trading Account  ",
            type=" funded ",
            starting_balance="25000",
            high_water_mark="26500.50",
            account_currency=" cad ",
        )
    )

    assert errors == []
    assert normalized["name"] == "Trading Account"
    assert normalized["type"] == "Funded"
    assert normalized["starting_balance"] == 25000.0
    assert normalized["high_water_mark"] == 26500.50
    assert normalized["account_currency"] == "CAD"


def test_validate_account_does_not_mutate_original_dictionary():
    account = make_account(
        name="  Main Account  ",
        type="personal",
    )
    original = copy.deepcopy(account)

    validate_and_normalize_account(account)

    assert account == original


def test_validate_account_preserves_unrelated_extra_fields():
    normalized, errors = validate_and_normalize_account(
        make_account(broker="The5ers")
    )

    assert errors == []
    assert normalized["broker"] == "The5ers"


@pytest.mark.parametrize(
    ("account_type", "expected"),
    [
        ("personal", "Personal"),
        ("EVALUATION", "Evaluation"),
        (" Funded ", "Funded"),
    ],
)
def test_valid_account_types_are_case_insensitive(
    account_type,
    expected,
):
    normalized, errors = validate_and_normalize_account(
        make_account(type=account_type)
    )

    assert errors == []
    assert normalized["type"] == expected


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("name", "", "Account name cannot be blank."),
        (
            "type",
            "Demo",
            "Account type must be Personal, Evaluation, or Funded.",
        ),
        (
            "starting_balance",
            -1,
            "Starting balance must be greater than or equal to 0. ",
        ),
        (
            "starting_balance",
            "bad",
            "Starting balance must be a number. ",
        ),
        (
            "starting_balance",
            float("inf"),
            "Starting balance must be a finite number. ",
        ),
        (
            "starting_balance",
            True,
            "Starting balance must be a number. ",
        ),
    ],
)
def test_invalid_required_account_field_is_rejected(
    field,
    value,
    expected_error,
):
    account = make_account()
    account[field] = value

    normalized, errors = validate_and_normalize_account(account)

    assert normalized is None
    assert expected_error in errors


def test_account_validation_collects_multiple_errors():
    normalized, errors = validate_and_normalize_account(
        {
            "name": "",
            "type": "Demo",
            "starting_balance": "bad",
        }
    )

    assert normalized is None
    assert errors == [
        "Account name cannot be blank.",
        "Account type must be Personal, Evaluation, or Funded.",
        "Starting balance must be a number. ",
    ]


def test_missing_high_water_mark_defaults_to_starting_balance():
    account = make_account()
    account.pop("high_water_mark")

    normalized, errors = validate_and_normalize_account(account)

    assert errors == []
    assert normalized["high_water_mark"] == 25000.0


@pytest.mark.parametrize("high_water_mark", ["bad", 24999, -1, True])
def test_invalid_high_water_mark_resets_to_starting_balance(
    high_water_mark,
):
    normalized, errors = validate_and_normalize_account(
        make_account(high_water_mark=high_water_mark)
    )

    assert errors == []
    assert normalized["high_water_mark"] == 25000.0


def test_high_water_mark_can_equal_starting_balance():
    normalized, errors = validate_and_normalize_account(
        make_account(high_water_mark=25000)
    )

    assert errors == []
    assert normalized["high_water_mark"] == 25000.0


def test_zero_starting_balance_is_allowed():
    normalized, errors = validate_and_normalize_account(
        make_account(starting_balance=0, high_water_mark=0)
    )

    assert errors == []
    assert normalized["starting_balance"] == 0.0
    assert normalized["high_water_mark"] == 0.0


@pytest.mark.parametrize(
    ("currency", "expected"),
    [
        ("usd", "USD"),
        (" CAD ", "CAD"),
        ("JPY", "JPY"),
        (None, None),
        ("", None),
        ("XYZ", None),
        ("US", None),
        (123, None),
    ],
)
def test_account_currency_is_normalized_or_cleared(
    currency,
    expected,
):
    normalized, errors = validate_and_normalize_account(
        make_account(account_currency=currency)
    )

    assert errors == []
    assert normalized["account_currency"] == expected