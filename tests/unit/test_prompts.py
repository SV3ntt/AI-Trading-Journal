from datetime import date

import pytest

import journal.prompts as prompts
from journal.prompts import (
    ensure_account_currency,
    get_optional_date,
    prompt_choice,
    prompt_date,
    prompt_finite_number,
    prompt_forex_price,
    prompt_futures_price,
    prompt_positive_integer,
    prompt_required_text,
    prompt_time,
    resolve_forex_pair_profile,
    resolve_forex_pip_value,
    resolve_forex_pip_value_for_edit,
    resolve_futures_tick_metadata,
)

def provide_inputs(monkeypatch, values):
    answers = iter(values)
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: next(answers),
    )

def make_current_forex_trade(**overrides):
    trade = {
         "market_type": "forex",
        "symbol": "eur/usd",
        "pip_size": 0.0001,
        "pip_value": 10.0,
        "price_precision": 5,
        "lot_size": 1.0,
        "entry": 1.10000,
        "exit": 1.10100,
        "direction": "long",
        "trade_date": "2026-07-27",
        "exit_time": "10:00",
        "account_currency": "USD",
        "conversion_rate": 1.0,
        "conversion_pair": None,
        "conversion_timestamp": None,
        "conversion_rate_source": "not_required",
    }
    trade.update(overrides)
    return trade

def test_prompt_required_text_strips_and_returns_value(monkeypatch):
    provide_inputs(monkeypatch, ["  MES "])

    assert prompt_required_text("Symbol: ", "Symbol") == "MES"

def test_prompt_required_text_retries_blank_input(monkeypatch,
capsys):
    provide_inputs(monkeypatch, [" ", "valid"])

    assert prompt_required_text("Value: ", "Field") == "valid"
    assert "Field cannot be blank." in capsys.readouterr().out

def test_prompt_choice_normalizes_input(monkeypatch):
    provide_inputs(monkeypatch, [" LONG "])

    assert prompt_choice(
        "Direction: ", 
        ("long", "short"),
        "Invalid direction.", 
    ) == "long"

def test_prompt_choice_returns_default_for_blank_input(monkeypatch):
    provide_inputs(monkeypatch, [""])

    assert prompt_choice(
        "Direction: ",
        ("long", "short"),
        "Invalid direction.",
        default="short",
    ) == "short"


def test_prompt_choice_retries_invalid_input(monkeypatch, 
capsys):
    provide_inputs(monkeypatch, ["buy", "short"])

    result = prompt_choice(
        "Direction: ",
        ("long", "short"),
        "Choose long or short.",
    )
    assert result == "short"
    assert "Choose long or short." in capsys.readouterr().out

@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("12.5", 12.5),
        (" 4 ", 4.0),
        ("0", 0.0),
        ("-2.75", -2.75),
    ],
)
def test_prompt_finite_number_returns_valid_number(
    monkeypatch,
    raw_value,
    expected,
):
    provide_inputs(monkeypatch, [raw_value])

    assert prompt_finite_number("Number: ", "Number") == expected

def test_prompt_finite_number_returns_default_for_blank(monkeypatch):
    provide_inputs(monkeypatch, [""])

    assert prompt_finite_number(
        "Risk: ",
        "Risk",
        default=125.0,
    ) == 125.0

def test_prompt_finite_number_retries_invalid_and_below_minimum(
    monkeypatch,
    capsys,
):
    provide_inputs(monkeypatch, ["abc", "-1", "2.5"])

    result = prompt_finite_number(
        "Amount: ",
        "Amount",
        minimum=0,
    )

    output = capsys.readouterr().out
    assert result == 2.5
    assert "Amount must be a number." in output
    assert "Amount must be greater than or equal to 0." in output

def test_prompt_finite_number_enforces_strict_minimum(monkeypatch, 
capsys):
    provide_inputs(monkeypatch, ["0", "0.25"])

    result = prompt_finite_number(
        "Tick size: ",
        "Tick size",
        minimum=0,
        minimum_is_strict=True,
    )

    assert result == 0.25
    assert "Tick size must be greater than 0." in capsys.readouterr().out


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1", 1),
        ("5.0", 5),
        (" 12 ", 12),
    ],
)
def test_prompt_positive_integer_returns_valid_integer(
    monkeypatch,
    raw_value,
    expected,
):
    provide_inputs(monkeypatch, [raw_value])

    assert prompt_positive_integer("Count: ", "Count") == expected


def test_prompt_positive_integer_returns_default_for_blank(monkeypatch):
    provide_inputs(monkeypatch, [""])

    assert prompt_positive_integer(
        "Contracts: ",
        "Contracts",
        default=3,
    ) == 3


def test_prompt_positive_integer_retries_invalid_values(monkeypatch, capsys):
    provide_inputs(monkeypatch, ["2.5", "0", "4"])

    result = prompt_positive_integer("Count: ", "Count")

    assert result == 4
    assert capsys.readouterr().out.count(
        "Count must be a whole number greater than 0."
    ) == 2


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("2026-07-27", "2026-07-27"),
        ("2026 07 27", "2026-07-27"),
        (" 2026-01-05 ", "2026-01-05"),
    ],
)
def test_prompt_date_normalizes_valid_date(
    monkeypatch,
    raw_value,
    expected,
):
    provide_inputs(monkeypatch, [raw_value])

    assert prompt_date("Date: ") == expected


def test_prompt_date_returns_default_for_blank(monkeypatch):
    provide_inputs(monkeypatch, [""])

    assert prompt_date(
        "Date: ",
        default="2026-08-01",
    ) == "2026-08-01"


def test_prompt_date_retries_invalid_date(monkeypatch, capsys):
    provide_inputs(monkeypatch, ["2026-02-30", "2026-02-28"])

    assert prompt_date("Date: ") == "2026-02-28"
    assert "Invalid date." in capsys.readouterr().out


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("09:30", "09:30"),
        (" 07:05 ", "07:05"),
        ("23:59", "23:59"),
    ],
)
def test_prompt_time_normalizes_valid_time(
    monkeypatch,
    raw_value,
    expected,
):
    provide_inputs(monkeypatch, [raw_value])

    assert prompt_time("Time: ") == expected


def test_prompt_time_returns_default_for_blank(monkeypatch):
    provide_inputs(monkeypatch, [""])

    assert prompt_time("Time: ", default="10:15") == "10:15"


def test_prompt_time_retries_invalid_time(monkeypatch, capsys):
    provide_inputs(monkeypatch, ["24:00", "12:45"])

    assert prompt_time("Time: ") == "12:45"
    assert "Invalid time." in capsys.readouterr().out


@pytest.mark.parametrize(
    ("raw_value", "tick_size", "expected"),
    [
        ("7560.75", 0.25, 7560.75),
        ("100.10", 0.10, 100.10),
        ("25", 0.25, 25.0),
    ],
)
def test_prompt_futures_price_accepts_tick_aligned_price(
    monkeypatch,
    raw_value,
    tick_size,
    expected,
):
    provide_inputs(monkeypatch, [raw_value])

    assert prompt_futures_price(
        "Entry: ",
        "Entry price",
        tick_size,
    ) == pytest.approx(expected)


def test_prompt_futures_price_returns_default_for_blank(monkeypatch):
    provide_inputs(monkeypatch, [""])

    assert prompt_futures_price(
        "Entry: ",
        "Entry price",
        0.25,
        default=5000.25,
    ) == 5000.25


def test_prompt_futures_price_retries_invalid_and_misaligned_price(
    monkeypatch,
    capsys,
):
    provide_inputs(monkeypatch, ["abc", "100.10", "100.25"])

    result = prompt_futures_price(
        "Entry: ",
        "Entry price",
        0.25,
    )

    output = capsys.readouterr().out
    assert result == 100.25
    assert "Entry price must be a number." in output
    assert "must align with a tick size of 0.25" in output


@pytest.mark.parametrize(
    ("raw_value", "precision", "expected"),
    [
        ("1.12345", 5, 1.12345),
        ("150.123", 3, 150.123),
        ("1", 5, 1.0),
        ("1.2", 5, 1.2),
    ],
)
def test_prompt_forex_price_accepts_supported_precision(
    monkeypatch,
    raw_value,
    precision,
    expected,
):
    provide_inputs(monkeypatch, [raw_value])

    assert prompt_forex_price(
        "Entry: ",
        "Entry price",
        precision,
    ) == pytest.approx(expected)


def test_prompt_forex_price_returns_default_for_blank(monkeypatch):
    provide_inputs(monkeypatch, [""])

    assert prompt_forex_price(
        "Entry: ",
        "Entry price",
        5,
        default=1.10001,
    ) == 1.10001


def test_prompt_forex_price_retries_invalid_and_excess_precision(
    monkeypatch,
    capsys,
):
    provide_inputs(monkeypatch, ["-1", "1.123456", "1.12345"])

    result = prompt_forex_price(
        "Entry: ",
        "Entry price",
        5,
    )

    output = capsys.readouterr().out
    assert result == pytest.approx(1.12345)
    assert "Entry price must be greater than 0." in output
    assert "cannot exceed 5 decimal places" in output


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("EURUSD", (0.0001, 5, True)),
        ("usd/jpy", (0.01, 3, True)),
    ],
)
def test_resolve_forex_pair_profile_returns_standard_profile(
    monkeypatch,
    symbol,
    expected,
):
    def fail_if_called(*_args, **_kwargs):
        pytest.fail("Manual profile prompt should not be used.")

    monkeypatch.setattr(
        prompts,
        "prompt_positive_integer",
        fail_if_called,
    )
    monkeypatch.setattr(
        prompts,
        "prompt_finite_number",
        fail_if_called,
    )

    assert resolve_forex_pair_profile(symbol) == expected


def test_resolve_forex_pair_profile_prompts_for_nonstandard_pair(monkeypatch):
    calls = []

    def fake_positive_integer(prompt, field_name, default=None):
        calls.append(("integer", prompt, field_name, default))
        return 2

    def fake_finite_number(
        prompt,
        field_name,
        minimum=None,
        minimum_is_strict=False,
        default=None,
    ):
        calls.append(
            (
                "number",
                prompt,
                field_name,
                minimum,
                minimum_is_strict,
                default,
            )
        )
        return 0.01

    monkeypatch.setattr(
        prompts,
        "prompt_positive_integer",
        fake_positive_integer,
    )
    monkeypatch.setattr(
        prompts,
        "prompt_finite_number",
        fake_finite_number,
    )

    assert resolve_forex_pair_profile("XAU/USD") == (0.01, 2, False)
    assert calls == [
        (
            "integer",
            "Enter price precision (decimal places): ",
            "Price precision",
            None,
        ),
        (
            "number",
            "Enter pip size: ",
            "Pip size",
            0,
            True,
            None,
        ),
    ]


def test_resolve_forex_pip_value_when_quote_matches_account(capsys):
    result = resolve_forex_pip_value(
        symbol="eur/usd",
        pip_size=0.0001,
        price_precision=5,
        is_standard_pair=True,
        account={"account_currency": "USD"},
        exit_price=1.10500,
        exit_date="2026-07-27",
        exit_time="10:00",
    )

    assert result == {
        "pip_value": 10.0,
        "conversion_rate": 1.0,
        "conversion_pair": None,
        "conversion_timestamp": None,
        "conversion_rate_source": "not_required",
    }

    output = capsys.readouterr().out
    assert "Standard pair detected." in output
    assert "Source: USD quote currency" in output


def test_resolve_forex_pip_value_when_base_matches_account(capsys):
    result = resolve_forex_pip_value(
        symbol="usd/jpy",
        pip_size=0.01,
        price_precision=3,
        is_standard_pair=True,
        account={"account_currency": "USD"},
        exit_price=150.0,
        exit_date="2026-07-27",
        exit_time="10:30",
    )

    assert result["pip_value"] == pytest.approx(1000 / 150)
    assert result["conversion_rate"] == pytest.approx(1 / 150)
    assert result["conversion_pair"] == "USD/JPY"
    assert result["conversion_timestamp"] == "2026-07-27 10:30"
    assert result["conversion_rate_source"] == "trade_exit_price"

    output = capsys.readouterr().out
    assert "Source: Trade exit price" in output


def test_resolve_forex_pip_value_uses_available_conversion_rate(
    monkeypatch,
    capsys,
):
    requested = []

    def fake_conversion_rate(from_currency, to_currency, timestamp):
        requested.append((from_currency, to_currency, timestamp))
        return 0.0091, "historical_market_data"

    monkeypatch.setattr(
        prompts,
        "get_fx_conversion_rate",
        fake_conversion_rate,
    )

    result = resolve_forex_pip_value(
        symbol="gbp/jpy",
        pip_size=0.01,
        price_precision=3,
        is_standard_pair=True,
        account={"account_currency": "CAD"},
        exit_price=190.0,
        exit_date="2026-07-27",
        exit_time="11:15",
    )

    assert requested == [("JPY", "CAD", "2026-07-27 11:15")]
    assert result["pip_value"] == pytest.approx(9.1)
    assert result["conversion_rate"] == 0.0091
    assert result["conversion_pair"] == "JPY/CAD"
    assert result["conversion_timestamp"] == "2026-07-27 11:15"
    assert result["conversion_rate_source"] == "historical_market_data"
    assert "Source: Historical market data" in capsys.readouterr().out


def test_resolve_forex_pip_value_prompts_for_missing_conversion_rate(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        prompts,
        "get_fx_conversion_rate",
        lambda *_args: (None, None),
    )

    calls = []

    def fake_prompt(
        prompt,
        field_name,
        minimum=None,
        minimum_is_strict=False,
        default=None,
    ):
        calls.append(
            (
                prompt,
                field_name,
                minimum,
                minimum_is_strict,
                default,
            )
        )
        return 0.009

    monkeypatch.setattr(prompts, "prompt_finite_number", fake_prompt)

    result = resolve_forex_pip_value(
        symbol="gbp/jpy",
        pip_size=0.01,
        price_precision=3,
        is_standard_pair=True,
        account={"account_currency": "CAD"},
        exit_price=190.0,
        exit_date="2026-07-27",
        exit_time="11:15",
    )

    assert calls == [
        (
            "Enter JPY/CAD conversion rate: ",
            "Conversion rate",
            0,
            True,
            None,
        )
    ]
    assert result["pip_value"] == pytest.approx(9.0)
    assert result["conversion_rate"] == 0.009
    assert result["conversion_rate_source"] == "manual"

    output = capsys.readouterr().out
    assert "no market data source is configured" in output
    assert "Source: Manually supplied" in output


def test_ensure_account_currency_returns_existing_currency(monkeypatch):
    account = {"account_currency": "CAD"}

    def fail_if_called(*_args, **_kwargs):
        pytest.fail("Input or saving should not be used.")

    monkeypatch.setattr("builtins.input", fail_if_called)
    monkeypatch.setattr(prompts, "save_account", fail_if_called)

    assert ensure_account_currency(account) == "CAD"
    assert account == {"account_currency": "CAD"}


def test_ensure_account_currency_retries_and_saves_currency(
    monkeypatch,
    capsys,
):
    account = {}
    provide_inputs(monkeypatch, ["US", "ABC", " cad "])

    saved_accounts = []
    monkeypatch.setattr(
        prompts,
        "save_account",
        lambda value: saved_accounts.append(value.copy()) or True,
    )

    assert ensure_account_currency(account) == "CAD"
    assert account["account_currency"] == "CAD"
    assert saved_accounts == [{"account_currency": "CAD"}]

    output = capsys.readouterr().out
    assert output.count("must be a recognized") == 2


def test_ensure_account_currency_warns_when_save_fails(monkeypatch, capsys):
    account = {}
    provide_inputs(monkeypatch, ["USD"])
    monkeypatch.setattr(prompts, "save_account", lambda _value: False)

    assert ensure_account_currency(account) == "USD"
    assert "could not be saved" in capsys.readouterr().out


def test_resolve_forex_pip_value_for_edit_reuses_unchanged_metadata(
    monkeypatch,
):
    current = make_current_forex_trade()

    def fail_if_called(*_args, **_kwargs):
        pytest.fail("Pip value should not be recalculated.")

    monkeypatch.setattr(
        prompts,
        "resolve_forex_pip_value",
        fail_if_called,
    )

    result = resolve_forex_pip_value_for_edit(
        current=current,
        new_symbol="eur/usd",
        new_pip_size=0.0001,
        new_price_precision=5,
        new_lot_size=1.0,
        new_entry=1.10000,
        new_exit=1.10100,
        new_direction="long",
        new_trade_date="2026-07-27",
        new_exit_time="10:00",
        account={"account_currency": "USD"},
    )

    assert result == {
        "pip_value": 10.0,
        "conversion_rate": 1.0,
        "conversion_pair": None,
        "conversion_timestamp": None,
        "conversion_rate_source": "not_required",
    }


def test_resolve_forex_pip_value_for_edit_ensures_missing_account_currency(
    monkeypatch,
):
    current = make_current_forex_trade(account_currency=None)
    account = {}

    monkeypatch.setattr(
        prompts,
        "ensure_account_currency",
        lambda value: value.setdefault("account_currency", "USD"),
    )

    expected = {
        "pip_value": 10.0,
        "conversion_rate": 1.0,
        "conversion_pair": None,
        "conversion_timestamp": None,
        "conversion_rate_source": "not_required",
    }

    calls = []

    def fake_resolve(**kwargs):
        calls.append(kwargs)
        return expected

    monkeypatch.setattr(prompts, "resolve_forex_pip_value", fake_resolve)

    result = resolve_forex_pip_value_for_edit(
        current=current,
        new_symbol="eur/usd",
        new_pip_size=0.0001,
        new_price_precision=5,
        new_lot_size=1.0,
        new_entry=1.10000,
        new_exit=1.10200,
        new_direction="long",
        new_trade_date="2026-07-27",
        new_exit_time="10:00",
        account=account,
    )

    assert result is expected
    assert account["account_currency"] == "USD"
    assert calls[0]["account"] is account
    assert calls[0]["is_standard_pair"] is True


def test_resolve_forex_pip_value_for_edit_applies_confirmed_change(
    monkeypatch,
    capsys,
):
    current = make_current_forex_trade()
    updated = {
        "pip_value": 12.0,
        "conversion_rate": 1.2,
        "conversion_pair": "USD/CAD",
        "conversion_timestamp": "2026-07-27 10:00",
        "conversion_rate_source": "manual",
    }

    monkeypatch.setattr(
        prompts,
        "resolve_forex_pip_value",
        lambda **_kwargs: updated,
    )
    provide_inputs(monkeypatch, [" yes "])

    result = resolve_forex_pip_value_for_edit(
        current=current,
        new_symbol="eur/usd",
        new_pip_size=0.0001,
        new_price_precision=5,
        new_lot_size=1.0,
        new_entry=1.10000,
        new_exit=1.10200,
        new_direction="long",
        new_trade_date="2026-07-27",
        new_exit_time="10:00",
        account={"account_currency": "USD"},
    )

    assert result is updated
    output = capsys.readouterr().out
    assert "Pip value would change from $10.0000 to $12.0000" in output
    assert "gross dollar P/L from $100.00 to $240.00" in output


def test_resolve_forex_pip_value_for_edit_cancels_declined_change(
    monkeypatch,
    capsys,
):
    current = make_current_forex_trade()
    monkeypatch.setattr(
        prompts,
        "resolve_forex_pip_value",
        lambda **_kwargs: {
            "pip_value": 12.0,
            "conversion_rate": 1.2,
            "conversion_pair": "USD/CAD",
            "conversion_timestamp": "2026-07-27 10:00",
            "conversion_rate_source": "manual",
        },
    )
    provide_inputs(monkeypatch, ["no"])

    result = resolve_forex_pip_value_for_edit(
        current=current,
        new_symbol="eur/usd",
        new_pip_size=0.0001,
        new_price_precision=5,
        new_lot_size=1.0,
        new_entry=1.10000,
        new_exit=1.10200,
        new_direction="long",
        new_trade_date="2026-07-27",
        new_exit_time="10:00",
        account={"account_currency": "USD"},
    )

    assert result is None
    assert "Edit cancelled" in capsys.readouterr().out


def test_resolve_forex_pip_value_for_edit_skips_confirmation_when_value_same(
    monkeypatch,
):
    current = make_current_forex_trade()
    unchanged_value = {
        "pip_value": 10.0,
        "conversion_rate": 1.0,
        "conversion_pair": None,
        "conversion_timestamp": None,
        "conversion_rate_source": "not_required",
    }
    monkeypatch.setattr(
        prompts,
        "resolve_forex_pip_value",
        lambda **_kwargs: unchanged_value,
    )

    def fail_if_called(*_args, **_kwargs):
        pytest.fail("Confirmation should not be requested.")

    monkeypatch.setattr("builtins.input", fail_if_called)

    result = resolve_forex_pip_value_for_edit(
        current=current,
        new_symbol="eur/usd",
        new_pip_size=0.0001,
        new_price_precision=5,
        new_lot_size=2.0,
        new_entry=1.10000,
        new_exit=1.10100,
        new_direction="long",
        new_trade_date="2026-07-27",
        new_exit_time="10:00",
        account={"account_currency": "USD"},
    )

    assert result is unchanged_value


def test_resolve_forex_pip_value_for_edit_handles_missing_previous_value(
    monkeypatch,
):
    current = make_current_forex_trade(pip_value=None)
    updated = {
        "pip_value": 10.0,
        "conversion_rate": 1.0,
        "conversion_pair": None,
        "conversion_timestamp": None,
        "conversion_rate_source": "not_required",
    }
    monkeypatch.setattr(
        prompts,
        "resolve_forex_pip_value",
        lambda **_kwargs: updated,
    )

    def fail_if_called(*_args, **_kwargs):
        pytest.fail("Confirmation should not be requested.")

    monkeypatch.setattr("builtins.input", fail_if_called)

    result = resolve_forex_pip_value_for_edit(
        current=current,
        new_symbol="eur/usd",
        new_pip_size=0.0001,
        new_price_precision=5,
        new_lot_size=1.0,
        new_entry=1.10000,
        new_exit=1.10200,
        new_direction="long",
        new_trade_date="2026-07-27",
        new_exit_time="10:00",
        account={"account_currency": "USD"},
    )

    assert result is updated


def test_resolve_futures_tick_metadata_uses_known_profile(monkeypatch):
    printed_profiles = []
    monkeypatch.setattr(
        prompts,
        "print_futures_instrument_profile",
        lambda profile: printed_profiles.append(profile),
    )

    assert resolve_futures_tick_metadata("MES1!") == (0.25, 1.25)
    assert printed_profiles[0]["root"] == "MES"
    assert printed_profiles[0]["point_value"] == 5.0


def test_resolve_futures_tick_metadata_prompts_for_unknown_contract(
    monkeypatch,
    capsys,
):
    values = iter([0.5, 2.0])
    calls = []

    def fake_prompt(
        prompt,
        field_name,
        minimum=None,
        minimum_is_strict=False,
        default=None,
    ):
        calls.append(
            (
                prompt,
                field_name,
                minimum,
                minimum_is_strict,
                default,
            )
        )
        return next(values)

    monkeypatch.setattr(prompts, "prompt_finite_number", fake_prompt)

    assert resolve_futures_tick_metadata("CUSTOM") == (0.5, 2.0)
    assert calls == [
        ("Enter tick size: ", "Tick size", 0, True, None),
        ("Enter tick value: $", "Tick value", 0, True, None),
    ]

    output = capsys.readouterr().out
    assert "not in the built-in specifications" in output
    assert "Point value: $4.00" in output


def test_get_optional_date_returns_none_for_blank(monkeypatch):
    provide_inputs(monkeypatch, [""])

    assert get_optional_date("Date: ") is None


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("2026-08-01", date(2026, 8, 1)),
        ("2026 08 01", date(2026, 8, 1)),
        (" 2026-12-31 ", date(2026, 12, 31)),
    ],
)
def test_get_optional_date_returns_parsed_date(
    monkeypatch,
    raw_value,
    expected,
):
    provide_inputs(monkeypatch, [raw_value])

    assert get_optional_date("Date: ") == expected


def test_get_optional_date_retries_invalid_date(monkeypatch, capsys):
    provide_inputs(monkeypatch, ["not-a-date", "2026-08-01"])

    assert get_optional_date("Date: ") == date(2026, 8, 1)
    assert "Invalid date." in capsys.readouterr().out
