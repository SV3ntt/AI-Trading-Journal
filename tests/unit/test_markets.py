import pytest

import journal.markets as markets 
from journal.markets import(
    calculate_forex_pip_value,
    get_forex_pair_currencies,
    get_fx_conversion_rate,
    get_known_futures_profile,
    get_known_futures_tick_size,
    get_known_futures_tick_value,
    get_standard_forex_pip_profile,
    get_standard_forex_pip_profile,
    match_known_futures_root,
    match_known_futures_root,
    normalize_forex_symbol,
)

@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("MES", "MES"),
        ("mes", "MES"),
        (" MES ", "MES"),
        ("MNQ", "MNQ"),
        ("MGC", "MGC"),
        ("SIL", "SIL"),
        ("MCL", "MCL"),
        ("ES", "ES"),
        ("es", "ES"),
        ("NQ", "NQ"),
        ("YM", "YM"),
        ("MYM", "MYM"),
        ("RTY", "RTY"),
        ("M2K", "M2K"),
        ("CL", "CL"),
        ("GC", "GC"),
        ("SI", "SI"),
    ],
)
def test_match_known_futures_root_accepts_root_symbols(
    symbol,
    expected,
):
    assert match_known_futures_root(symbol) == expected

@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
    ("MES1!", "MES"),
    ("mes1!", "MES"),
    ("MNQ1!", "MNQ"),
    ("MGC1!", "MGC"),
    ("ES1!", "ES"),
    ("NQ1!", "NQ"),
    ("YM1!", "YM"),
    ("RTY1!", "RTY"),
    ("CL1!", "CL"),
    ("GC1!", "GC"),
    ("SI1!", "SI"),
    ],
)
def test_match_known_futures_root_accepts_continous_symbols(
    symbol,
    expected,
):
    assert match_known_futures_root(symbol) == expected

@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("MESZ6", "MES"),
        ("MESz26", "MES"),
        ("mnqh7", "MNQ"),
        ("MGCQ26", "MGC"),
        ("SILN6", "SIL"),
        ("MCLX26", "MCL"),
        ("ESZ26", "ES"),
        ("nqh7", "NQ"),
        ("YMM26", "YM"),
        ("MYMZ6", "MYM"),
        ("RTYH26", "RTY"),
        ("M2KZ26", "M2K"),
        ("CLQ26", "CL"),
        ("GCJ26", "GC"),
        ("SIK26", "SI"),
    ],
)
def test_match_known_futures_root_accepts_dead_contracts(
    symbol,
    expected,
):
    assert match_known_futures_root(symbol) == expected


@pytest.mark.parametrize(
    "symbol",
    [
        "ZB",
        "6E",
        "UNKOWN",
        "MESZ",
        "MESZ2026",
        "MES21!",
        "",
        None,
    ],
)
def test_match_known_futures_root_rejects_unknown_or_invalid_symbols(
    symbol,
):
    assert match_known_futures_root(symbol) is None

def test_get_known_futures_profile_returns_complete_mes_profile():
    result = get_known_futures_profile("MESz26")

    assert result == {
        "name": "Micro E-mini S&P 500",
        "tick_size": 0.25,
        "tick_value": 1.25,
        "point_value": 5.0,
        "root": "MES",
    }

def test_get_known_futures_profile_retuens_copy():
    first_result = get_known_futures_profile("MES")
    first_result["tick_size"] = 999

    second_result = get_known_futures_profile("MES")

    assert second_result["tick_size"] == 0.25

def test_get_known_futures_profile_retuens_none_for_unknown_symbol():
    assert get_known_futures_profile("ZB") is None

@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("MES", 0.25),
        ("MNQ", 0.25),
        ("MGCZ26", 0.10),
        ("SILN6", 0.005),
        ("MCL", 0.01),
    ],
)
def test_get_known_futures_tick_size_(symbol, expected):
    assert get_known_futures_tick_size(symbol) == expected

def test_get_known_futures_tick_size_returns_none_for_unknown_symbol():
    assert get_known_futures_tick_size("ZB") is None

@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("MES", 1.25),
        ("MNQ", 0.50),
        ("MGCZ26", 1.00),
        ("SILN6", 5.00),
        ("MCL", 1.00),
    ],
)
def test_get_known_futures_tick_value_(symbol, expected):
    assert get_known_futures_tick_value(symbol) == expected

def test_get_known_futures_tick_value_returns_none_for_unknown_symbol():
    assert get_known_futures_tick_value("ZB") is None

@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("EURUSD", "eur/usd"),
        ("eurusd", "eur/usd"),
        ("EUR/USD", "eur/usd"),
        ("eur-usd", "eur/usd"),
        ("EUR USD", "eur/usd"),
        ("  EUR / USD  ", "eur/usd"),
        ("USDJPY", "usd/jpy"),
    ],
)
def test_normalize_forex_symbol_accepts_supported_formats(
    symbol, 
    expected,
):
    assert normalize_forex_symbol(symbol) == expected

@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("EUR_USD", "eur_usd"),
        ("EUR/US", "eur/us"),
        ("NOT-A-PAIR", "not-a-pair"),
        ("", ""),
        (None, "none"),
    ],
)
def test_normalize_forex_symbol_returns_lowercase_fallback_for_invalid_input(
    symbol, 
    expected,
):
    assert normalize_forex_symbol(symbol) == expected

@pytest.mark.parametrize(
     ("symbol", "expected"),
    [
        ("EURUSD", ("EUR", "USD")),
        ("eur/usd", ("EUR", "USD")),
        ("GBP-JPY", ("GBP", "JPY")),
        (" AUD CAD ", ("AUD", "CAD")),
    ],
)
def test_get_forex_pair_currencies_retuens_base_and_quote(
    symbol, 
    expected,
):
    assert get_forex_pair_currencies(symbol) == expected

@pytest.mark.parametrize(
    "symbol",
    ["EUR_USD", "EUR/US", "INVALID", "", None],
)
def test_get_forex_pair_currencies_returns_none_for_invalid_symbol(
    symbol,
):
    assert get_forex_pair_currencies(symbol) is None


@pytest.mark.parametrize(
    "symbol",
    ["EURUSD", "GBP/USD", "AUD-CAD", "NZD CHF"],
)
def test_get_standard_forex_pip_profile_for_non_jpy_pair(symbol):
    assert get_standard_forex_pip_profile(symbol) == {
        "pip_size": 0.0001,
        "price_precision": 5,
    }

@pytest.mark.parametrize(
    "symbol",
    ["USDJPY", "EUR/JPY", "GBP-JPY"],
)
def test_get_standard_forex_pip_profile_for_jpy_quote_pair(symbol):
    assert get_standard_forex_pip_profile(symbol) == {
        "pip_size": 0.01,
        "price_precision": 3,
    }

@pytest.mark.parametrize(
    "symbol",
    ["EUR_XYZ", "ABC/USD", "EUR/US", "INVALID", "", None],
)
def test_get_standard_forex_pip_profile_rejects_unsupported_pairs(
    symbol,
):
    assert get_standard_forex_pip_profile(symbol) is None

def test_calculate_forex_pip_value_for_usd_quote_currency():
    result = calculate_forex_pip_value(0.0001, 1.0)

    assert result == pytest.approx(10.0)

def test_calculate_forex_pip_value_with_currency_conversion():
    result = calculate_forex_pip_value(0.01, 0.0067)

    assert result == pytest.approx(6.7)

def test_calculate_forex_pip_value_accepts_zero_conversion_rate():
    result = calculate_forex_pip_value(0.0001, 0.0)

    assert result == 0.0

def test_get_fx_conversion_rate_skips_lookup_for_matching_currencies(
    monkeypatch,
):
    def fail_if_called(*args):
        pytest.fail("Provider lookup should not be called")

    monkeypatch.setattr(
        markets,
        "_fx_provider_lookup",
        fail_if_called,
    )

    result = get_fx_conversion_rate(
        "USD", 
        "USD", 
        "2026-07-30T10:00",
    )

    assert result == (1.0, "not_required")

def test_get_fx_conversion_rate_returns_none_when_provider_has_no_quote(
        monkeypatch,
):
    monkeypatch.setattr(
        markets,
        "_fx_provider_lookup",
        lambda from_currency, to_currency, timestamp: None,
    )

    result = get_fx_conversion_rate(
        "JPY",
        "USD",
        "2026-07-30T10:00",
    )

    assert result == (None, None)

def test_get_fx_conversion_rate_returns_direct_provider_quote(
    monkeypatch,
):
    def fake_lookup(from_currency, to_currency, timestamp):
        assert from_currency == "EUR"
        assert to_currency == "CAD"
        assert timestamp == "2026-07-30T10:00"

        return (
            "EUR/CAD",
            1.50,
            "historical_market_data",
        )
    
    monkeypatch.setattr(
        markets,
        "_fx_provider_lookup",
        fake_lookup,
    )

    result = get_fx_conversion_rate(
        "EUR",
         "CAD",
        "2026-07-30T10:00",
    )

    assert result == (
        1.50,
        "historical_market_data",
    )

def test_get_fx_conversion_rate_inverts_opposite_provider_quote(
    monkeypatch,
):
    monkeypatch.setattr(
        markets,
        "_fx_provider_lookup",
        lambda from_currency, to_currency, timestamp: (
            "USD/JPY",
            150.0,
            "latest_market_data",
        ),
    )

    rate, source_label = get_fx_conversion_rate(
        "JPY",
        "USD",
        "2026-07-30T10:00",
    )

    assert rate == pytest.approx(1.0 / 150.0)
    assert source_label == "latest_market_data"

@pytest.mark.parametrize("rate", [0, None])
def test_get_fx_conversion_rate_rejects_unusable_inversion_rate(
    monkeypatch,
    rate,
):
    monkeypatch.setattr(
        markets,
        "_fx_provider_lookup",
        lambda from_currency, to_currency, timestamp: (
            "USD/JPY",
            rate,
            "latest_market_data",
        ),
    )

    result = get_fx_conversion_rate(
        "JPY",
        "USD",
        "2026-07-30T10:00",
    )

    assert result == (None, None)

def test_get_fx_conversion_rate_rejects_unrelates_provider_pair(
    monkeypatch,
):
    monkeypatch.setattr(
        markets,
        "_fx_provider_lookup",
        lambda from_currency, to_currency, timestamp: (
            "GBP/CHF",
            1.10,
            "historical_market_data",
        ),
    )

    result = get_fx_conversion_rate(
        "EUR",
        "CAD",
        "2026-07-30T10:00",
    )

    assert result == (None, None)