from datetime import date, datetime

import pytest


from journal.analytics import (
    build_combination_key,
    calculate_equity_drawdown_history,
    calculate_session_analysis,
    calculate_setup_analysis,
    calculate_strategy_method_analysis,
    calculate_streaks,
    calculate_time_based_analytics,
    compute_unit_performance_stats,
    dedupe_case_insensitive,
    determine_session,
    get_duration_range,
    get_entry_hour_range,
    get_setup_components,
    get_strategy_method,
    get_strategy_methods,
    get_trade_datetime,
    get_trade_weekday,
    normalize_session_name,
    normalize_setup_name,
    normalize_strategy_method,
    split_setup_components,
    split_strategy_methods,
    strip_setup_connector_words,
    trade_is_in_date_range,
)


MAINTENANCE = "Market Maintenance / Outside Sessions"

def make_trade(**overrides):
    trade = {
         "market_type": "futures",
        "symbol": "MES",
        "trade_date": "2026-07-27",
        "entry_time": "09:30",
        "duration": 30,
        "session": "New York/London Overlap",
        "strategy_method": "ICT",
        "setup": "FVG",
        "dollar_pnl": 100.0,
        "net_dollar_pnl": 95.0,
        "net_result": "Win",
        "risk_amount": 100.0,
        "realized_r": 1.0,
        "points_pnl": 20.0,
        "ticks_pnl": 80.0,
    }
    trade.update(overrides)
    return trade

def test_compute_unit_performance_stats_retuens_none_for_empty_buckets():
    result = compute_unit_performance_stats([])

    assert result == {
        "futures_points": None, 
        "futures_ticks": None,
        "forex_pips": None,
    }

def test_compute_unit_performance_stats_keeps_markets_seperate():
    futures_win = make_trade(points_pnl=10.0, ticks_pnl=40.0)
    futures_loss = make_trade(points_pnl=-4.0, ticks_pnl=-16.0)
    forex_win = make_trade(
        market_type="forex",
        symbol="EUR/USD",
        points_pnl=0.0015,
        ticks_pnl=None,
        pips_pnl=15.0,
    )

    forex_loss = make_trade(
        market_type="forex",
        symbol="USD/JPY",
        points_pnl=-0.08,
        ticks_pnl=None,
        pips_pnl=-8.0,
    )

    result = compute_unit_performance_stats(
        [
            (1, futures_win),
            (2, futures_loss),
            (3, forex_win),
            (4, forex_loss),
        ]
    )

    points = result["futures_points"]
    assert points["total"] == 6.0
    assert points["average"] == 3.0
    assert points["best_idx"] == 1
    assert points["best_trade"] is futures_win
    assert points["best_value"] == 10.0
    assert points["worst_idx"] == 2
    assert points["worst_trade"] is futures_loss
    assert points["worst_value"] == -4.0
    assert points["gross_profit"] == 10.0
    assert points["gross_loss"] == 4.0
    assert points["average_win"] == 10.0
    assert points["average_loss"] == 4.0
    assert points["profit_factor"] == 2.5
    assert points["expectancy"] == 3.0
    ticks = result["futures_ticks"]
    assert ticks["total"] == 24.0
    assert ticks["average"] == 12.0
    assert ticks["best_idx"] == 1
    assert ticks["worst_idx"] == 2
    assert ticks["profit_factor"] == 2.5

    pips = result["forex_pips"]
    assert pips["total"] == 7.0
    assert pips["average"] == 3.5
    assert pips["best_idx"] == 3
    assert pips["worst_idx"] == 4
    assert pips["gross_profit"] == 15.0
    assert pips["gross_loss"] == 8.0
    assert pips["profit_factor"] == pytest.approx(1.875)

def test_compute_unit_performance_stats_treats_legacy_trade_as_futures():
    legacy_trade = {
        "symbol": "MES",
        "points_pnl": 5.0,
        "ticks_pnl": 20.0,
    }

    result = compute_unit_performance_stats([(7, legacy_trade)])

    assert result["futures_points"]["total"] == 5.0
    assert result["futures_ticks"]["total"] == 20.0
    assert result["forex_pips"] is None

def test_compute_unit_performance_stats_has_no_profit_factor_without_losses():
    result = compute_unit_performance_stats(
        [(1, make_trade(points_pnl=3.0, ticks_pnl=12.0))]
    )

    points = result["futures_points"]
    assert points["average_loss"] == 0
    assert points["profit_factor"] is None

def test_calculate_streaks_for_empty_trades():
    assert calculate_streaks([]) == {
        "current_type": "None", 
        "current_length": 0,
        "longest_winning": 0,
        "longest_losing": 0,        
    }   

@pytest.mark.parametrize(
    ("results", "expected"),
    [
        (
            ["Win"],
            {
                "current_type": "Win",
                "current_length": 1,
                "longest_winning": 1,
                "longest_losing": 0,
            },
        ),
        (
            ["Win", "Win", "Loss", "Loss", "Loss", "Win"],
            {
                "current_type": "Win",
                "current_length": 1,
                "longest_winning": 2,
                "longest_losing": 3,
            },
        ),
        (
            ["Win", "Break-even", "Loss"],
            {
                "current_type": "Loss",
                "current_length": 1,
                "longest_winning": 1,
                "longest_losing": 1,
            },
        ),
        (
            ["Win", "Break-even"],
            {
                "current_type": "None",
                "current_length": 0,
                "longest_winning": 1,
                "longest_losing": 0,
            },
        ),
    ],
)
def test_calculate_streaks(results, expected):
    trades = [{"net_result": result} for result in results]

    assert calculate_streaks(trades) == expected

def test_calculate_streaks_uses_legacy_result_when_net_rersult_is_missing():
    trades = [{"result": "Loss"}, {"result": "Loss"}]
    
    result = calculate_streaks(trades)

    assert result["current_type"] == "Loss"
    assert result["current_length"] == 2
    assert result["longest_losing"] == 2

def test_calculate_streaks_prefers_net_result_over_legacy_result():
    trade = {"net_result": "Win", "result": "Loss"}

    result = calculate_streaks([trade])

    assert result["current_type"] == "Win"

@pytest.mark.parametrize(
    ("session", "expected"),
    [
        (None, "Unspecified"),
        ("", "Unspecified"),
        ("   ", "Unspecified"),
        ("ny", "New York"),
        ("NY SESSION", "New York"),
        ("lon", "London"),
        ("asian", "Asia"),
        ("syd", "Sydney"),
        ("ny/lon", "New York/London Overlap"),
        ("london/new york", "New York/London Overlap"),
        ("as/lon", "Asia/London Overlap"),
        ("syd/as", "Sydney/Asia Overlap"),
        ("outside sessions", MAINTENANCE),
        ("custom session", "Custom Session"),
    ],
)
def test_normalize_session_name(session, expected):
    assert normalize_session_name(session) == expected


@pytest.mark.parametrize(
    ("entry_time", "expected"),
    [
        ("17:00", MAINTENANCE),
        ("17:59", MAINTENANCE),
        ("18:00", "Sydney"),
        ("19:59", "Sydney"),
        ("20:00", "Sydney/Asia Overlap"),
        ("00:00", "Sydney/Asia Overlap"),
        ("02:59", "Sydney/Asia Overlap"),
        ("03:00", "Asia/London Overlap"),
        ("04:59", "Asia/London Overlap"),
        ("05:00", "London"),
        ("07:59", "London"),
        ("08:00", "New York/London Overlap"),
        ("11:59", "New York/London Overlap"),
        ("12:00", "New York"),
        ("16:59", "New York"),
        (" 09:30 ", "New York/London Overlap"),
        ("", None),
        (None, None),
        ("24:00", None),
        ("not-a-time", None),
    ],
)
def test_determine_session(entry_time, expected):
    assert determine_session(entry_time) == expected

def test_calculate_session_analysis_retuens_empty_dictionary():
    assert calculate_session_analysis([]) == {}

def test_calcuulate_session_analysis_aggregates_results_and_financials():
    trades = [
        make_trade(
            session="ny",
            dollar_pnl=100.0,
            net_dollar_pnl=95.0,
            net_result="Win",
            risk_amount=50.0,
        ),
        make_trade(
            session="ny",
            dollar_pnl=-50.0,
            net_dollar_pnl=-55.0,
            net_result="Loss",
            risk_amount=100.0,
        ),
        make_trade(
            session="NY session",
            dollar_pnl=5.0,
            net_dollar_pnl=0.0,
            net_result="Break-even",
            risk_amount=0.0,
        ), 
    ]
    trades[0].pop("realized_r")
    trades[1].pop("realized_r")

    result = calculate_session_analysis(trades)["New York"]

    assert result["total_trades"] == 3
    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["breakevens"] == 1
    assert result["net_pnl"] == 40.0
    assert result["total_realized_r"] == pytest.approx(1.5)
    assert result["risk_trades"] == 2
    assert result["gross_net_profit"] == 95.0
    assert result["gross_net_loss"] == 55.0
    assert result["net_win_rate"] == pytest.approx(100 / 3)
    assert result["average_realized_r"] == pytest.approx(0.75)
    assert result["net_profit_factor"] == pytest.approx(95 / 55)


def test_calculate_session_analysis_uses_legacy_financial_fallbacks():
    trade = {
        "session": "London",
        "dollar_pnl": 25.0,
        "risk_amount": 0, 
    }

    result = calculate_session_analysis([trade])["London"]

    assert result["net_pnl"] == 25.0
    assert result ["wins"] == 1
    assert result["average_realized_r"] is None
    assert result["net_profit_factor"] is None

@pytest.mark.parametrize(
    ("setup", "expected"),
    [
        (None, "Unspecified"),
        ("", "Unspecified"),
        ("  ", "Unspecified"),
        ("fvg", "Fair Value Gap (FVG)"),
        ("IFVG", "Inverse Fair Value Gap (IFVG)"),
        ("ob", "Order Block"),
        ("ls", "Liquidity Sweep"),
        ("bos", "Break of Structure (BOS)"),
        ("choch", "Change of Character (CHOCH)"),
        ("cisd", "Change in State of Delivery (CISD)"),
        (
            "cvd divergence",
            "Cumulative Volume Delta (CVD) Divergence",
        ),
        ("s&d", "Supply and Demand"),
        ("po3", "Power of 3"),
        ("demand zone touched", "Demand Zone Tapped Into"),
        ("Fair Value Gap (FVG)", "Fair Value Gap (FVG)"),
        ("custom setup", "Custom Setup"),
    ],
)
def test_normalize_setup_name(setup, expected):
    assert normalize_setup_name(setup) == expected

def test_dedupe_case_insensitive_preserves_first_occurence_and_order():
    items = [
        "ICT",
        "ict",
        "Order Flow",
        "ORDER FLOW",
        "Price Action",
    ]

    assert dedupe_case_insensitive(items) == [
        "ICT",
        "Order Flow",
        "Price Action",
    ]
    
def test_build_combination_key_duplicates_and_sorts_names():
    names = [
        "Order Block", 
        "Liquidity Sweep",
        "order block",
    ]

    assert build_combination_key(
        names=names
    ) == "Liquidity Sweep + Order Block"

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("and FVG", "FVG"),
        ("FVG and", "FVG"),
        ("and FVG and", "FVG"),
        ("Supply and Demand", "Supply and Demand"),
        ("and", ""),
    ],
)
def test_strip_setup_connector_words(text, expected):
    assert strip_setup_connector_words(text) == expected

def test_get_setup_components_uses_and_normalize_stored_components():
    trade = {
        "setup": "This fallback should not be used",
        "setup_components": [
            "fvg",
            "OB", 
            "Fair Value Gap",
            "",
        ],
    }

    assert get_setup_components(trade) == [
        "Fair Value Gap (FVG)",
        "Order Block",
    ]

def test_get_setup_components_falls_back_to_setup_text():
    trade = {"setup": "FVG + and BOS, OB"}

    assert get_setup_components(trade) == [
        "Fair Value Gap (FVG)",
        "Break of Structure (BOS)",
        "Order Block",
    ]

@pytest.mark.parametrize(
    "trade",
    [
        {}, 
        {"setup": ""},
        {"setup_components": []},
    ], 
)
def test_get_setup_components_returns_unspecified_when_empty(trade):
    assert get_setup_components(trade) == ["Unspecified"]

@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        (None, []),
        ("", []),
        ("ICT", ["ICT"]),
        ("ICT + Order Flow", ["ICT", "Order Flow"]),
        ("ICT and Price Action", ["ICT", "Price Action"]),
        ("Supply and Demand", ["Supply and Demand"]),
        (
            "ICT + Supply & Demand",
            ["ICT", "Supply and Demand"],
        ),
        (
            "Supply and Demand and Order Flow",
            ["Supply and Demand", "Order Flow"],
        ),
    ],
)
def test_split_strategy_methods(raw_text, expected):
    assert split_strategy_methods(raw_text) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "Unspecified"),
        ("", "Unspecified"),
        ("ict", "ICT"),
        ("inner circle trader", "ICT"),
        ("orderflow", "Order Flow"),
        ("footprint trading", "Order Flow"),
        ("supply and demand", "Supply & Demand"),
        ("pa", "Price Action"),
        ("orb", "Opening Range Breakout"),
        ("Trend Following", "Trend Following"),
        ("custom method", "Custom Method"),
    ],
)
def test_normalize_strategy_method(value, expected):
    assert normalize_strategy_method(value) == expected

def test_get_strategy_methods_uses_stored_methods_and_deduplicates():
    trade = {
        "strategy_method": "fallback",
        "strategy_methods": [
            "ict",
            "ICT",
            "footprint",
            "",
        ],
    }

    assert get_strategy_methods(trade) == [
        "ICT",
        "Order Flow",
    ]


def test_get_strategy_methods_falls_back_to_legacy_text():
    trade = {
        "strategy_method": (
            "ICT and Supply & Demand + Order Flow"
        )
    }

    assert get_strategy_methods(trade) == [
        "ICT",
        "Supply & Demand",
        "Order Flow",
    ]


@pytest.mark.parametrize(
    "trade",
    [
        {},
        {"strategy_method": ""},
        {"strategy_methods": []},
    ],
)
def test_get_strategy_methods_returns_unspecified_when_empty(trade):
    assert get_strategy_methods(trade) == ["Unspecified"]

def test_get_strategy_method_joins_normalized_methods():
    trade = {
        "strategy_methods": [
            "ict", 
            "orderflow",      
        ]
    }

    assert get_strategy_method(trade) == "ICT, Order Flow"

def test_calculate_setup_analysis_aggregates_components_and_combinations():
    trades = [
          make_trade(
            setup_components=["FVG", "OB"],
            dollar_pnl=100.0,
            net_dollar_pnl=90.0,
            net_result="Win",
            risk_amount=100.0,
        ),
        make_trade(
            setup="OB + LS",
            setup_components=[],
            dollar_pnl=-50.0,
            net_dollar_pnl=-55.0,
            net_result="Loss",
            risk_amount=100.0,
        ),
        make_trade(
            setup="FVG",
            setup_components=[],
            dollar_pnl=0.0,
            net_dollar_pnl=0.0,
            net_result="Break-even",
            risk_amount=0.0,
        ),
    ]

    components, combinations = calculate_setup_analysis(
        trades
    )

    order_block = components["Order Block"]

    assert order_block["total_trades"] == 2
    assert order_block["wins"] == 1
    assert order_block["losses"] == 1
    assert order_block["breakevens"] == 0
    assert order_block["net_pnl"] == 35.0
    assert order_block["total_realized_r"] == pytest.approx(
        0.5
    )
    assert order_block["risk_trades"] == 2
    assert order_block["gross_net_profit"] == 90.0
    assert order_block["gross_net_loss"] == 55.0
    assert order_block["net_win_rate"] == 50.0
    assert order_block["average_realized_r"] == pytest.approx(
        0.25
    )
    assert order_block["net_profit_factor"] == pytest.approx(
        90 / 55
    )

    fvg = components["Fair Value Gap (FVG)"]

    assert fvg["total_trades"] == 2
    assert fvg["wins"] == 1
    assert fvg["breakevens"] == 1
    assert fvg["net_pnl"] == 90.0

    assert set(combinations) == {
        "Fair Value Gap (FVG) + Order Block",
        "Liquidity Sweep + Order Block",
    }

    assert combinations[
        "Fair Value Gap (FVG) + Order Block"
    ]["total_trades"] == 1

def test_calculate_setup_analysis_returns_empty_dictionaries():
    assert calculate_setup_analysis([]) == ({}, {})

def test_calculate_strategy_analysis_aggregates_methods_and_combinations():
    trades = [
        make_trade(
            strategy_methods=["ICT", "Order Flow"],
            dollar_pnl=100.0,
            net_dollar_pnl=95.0,
            net_result="Win",
            risk_amount=100.0,
        ),
        make_trade(
            strategy_method="ICT and Supply and Demand",
            strategy_methods=[],
            dollar_pnl=-50.0,
            net_dollar_pnl=-55.0,
            net_result="Loss",
            risk_amount=100.0,
        ),
        make_trade(
            strategy_method="Order Flow",
            strategy_methods=[],
            dollar_pnl=0.0,
            net_dollar_pnl=0.0,
            net_result="Break-even",
            risk_amount=0.0,
        ),
    ]

    strategies, combinations, = (
        calculate_strategy_method_analysis(trades)
    )

    ict = strategies ["ICT"]

    assert ict["total_trades"] == 2
    assert ict["wins"] == 1
    assert ict["losses"] == 1
    assert ict["net_pnl"] == 40.0
    assert ict["average_realized_r"] == pytest.approx(
        0.25
    )
    assert ict["net_profit_factor"] == pytest.approx(
        95 / 55
    )

    order_flow = strategies["Order Flow"]

    assert order_flow["total_trades"] == 2
    assert order_flow["wins"] == 1
    assert order_flow["breakevens"] == 1

    assert set(combinations) == {
        "ICT + Order Flow",
        "ICT + Supply & Demand",
    }

def test_calculate_stretagy_analysis_returns_empty_dictionaries():
    assert calculate_strategy_method_analysis([]) == ({}, {})

@pytest.mark.parametrize(
    ("trade", "expected"),
    [
         (
            {
                "trade_date": "2026-07-30",
                "entry_time": "09:45",
            },
            datetime(2026, 7, 30, 9, 45),
        ),
        (
            {
                "trade_date": "2026 07 30",
                "entry_time": " 09:45 ",
            },
            datetime(2026, 7, 30, 9, 45),
        ),
        (
            {
                "trade_date": "invalid",
                "entry_time": "09:45",
            },
            None,
        ),
        (
            {
                "trade_date": "2026-07-30",
                "entry_time": "25:00",
            },
            None,
        ),
        ({}, None),
    ], 
)
def test_get_trade_datetime(trade, expected):
    assert get_trade_datetime(trade) == expected

def test_calculate_equity_drawdown_history_sorts_and_tracks_drawdown():
    trades = [
        make_trade(
            symbol="mes",
            trade_date="2026-01-03",
            entry_time="09:30",
            net_dollar_pnl=-50.0,
        ),
        make_trade(
            symbol="mnq",
            trade_date="2026-01-01",
            entry_time="10:00",
            net_dollar_pnl=100.0,
        ),
        make_trade(
            symbol="eur/usd",
            trade_date="invalid",
            entry_time="bad",
            net_dollar_pnl=-30.0,
        ),
        make_trade(
            symbol="mgc",
            trade_date="2026-01-02",
            entry_time="11:00",
            net_dollar_pnl=-200.0,
        ),
    ]

    original_order = [
        trade["symbol"] for trade in trades
    ]
    
    result = calculate_equity_drawdown_history(
        trades,
        1000.0,
    )

    assert [ 
        row["trade_number"] for row in result["history"]
    ] == [2, 4, 1, 3]
    
    assert [
        row["equity"] for row in result["history"]
    ] == [
        1100.0,
        900.0,
        850.0,
        820.0,
    ]

    assert [
        row["drawdown"] for row in result["history"]
    ] == [
        0.0,
        200.0,
        250.0,
        280.0,
    ]

    assert result["starting_balance"] == 1000.0
    assert result["ending_balance"] == 820.0
    assert result["net_change"] == -180.0
    assert result["high_water_mark"] == 1100.0
    assert result["current_drawdown"] == 280.0

    assert result[
        "current_drawdown_percentage"
    ] == pytest.approx(280 / 1100 * 100)

    assert result["maximum_drawdown"] == 280.0

    assert result[
        "maximum_drawdown_percentage"
    ] == pytest.approx(280 / 1100 * 100)

    assert result["maximum_drawdown_peak"] == "Trade #2"
    assert result["maximum_drawdown_trough"] == "Trade 3"
    assert result["unspecified_datetime_trades"] == 1
    assert result["history"][-1]["trade_date"] == "Unspecified"
    assert result["history"][-1]["entry_time"] == "N/A"
    assert result["history"][-1]["symbol"] == "EUR/USD"

    assert [
        trade["symbol"] for trade in trades
    ] == original_order


def test_calculate_equity_drawdown_history_for_empty_trades():
    result = calculate_equity_drawdown_history(
        [],
        25000,
    )

    assert result["history"] == []
    assert result["starting_balance"] == 25000.0
    assert result["ending_balance"] == 25000.0
    assert result["net_change"] == 0.0
    assert result["high_water_mark"] == 25000.0
    assert result["current_drawdown"] == 0.0
    assert result["maximum_drawdown"] == 0.0
    assert (
        result["maximum_drawdown_peak"]
        == "Starting Balance"
    )
    assert result["maximum_drawdown_trough"] == "N/A"
    assert result["unspecified_datetime_trades"] == 0


def test_calculate_equity_drawdown_history_uses_dollar_pnl_fallback():
    trades = [
        {
            "trade_date": "2026-07-30",
            "entry_time": "09:30",
            "symbol": "MES",
            "dollar_pnl": 50.0,
        }
    ]

    result = calculate_equity_drawdown_history(
        trades,
        1000,
    )

    assert result["ending_balance"] == 1050.0
    assert result["high_water_mark"] == 1050.0


@pytest.mark.parametrize(
    "invalid_pnl",
    [
        None,
        "not-a-number",
    ],
)
def test_calculate_equity_drawdown_history_treats_invalid_pnl_as_zero(
    invalid_pnl,
):
    trade = make_trade(net_dollar_pnl=invalid_pnl)

    result = calculate_equity_drawdown_history(
        [trade],
        1000,
    )

    assert result["ending_balance"] == 1000.0
    assert result["history"][0]["net_dollar_pnl"] == 0.0


# Sprint 29 regression suite: high-water-mark / drawdown reconstruction
# after editing or deleting a trade. All expected figures below are
# hand-derived from starting_balance + cumulative net_dollar_pnl, never
# by calling calculate_equity_drawdown_history itself.
#
# Investigation note (Sprint 29 bug report): a real-account scenario
# reported "high water mark == current balance, $0.00 drawdown" after
# editing a winning M2K trade into a loss, and expected a non-zero
# drawdown instead. Reproducing it against the real (untouched) trade
# data confirmed the existing chronological algorithm was already
# correct: three trades dated *after* the edited one were collectively
# profitable enough to not only recover its loss but set a brand-new
# all-time high by the most recent trade, so $0.00 drawdown was the
# mathematically correct answer for that specific dataset. No production
# code changed as a result -- these tests instead pin down the general
# rebuild behavior with clean, unambiguous synthetic scenarios.

def test_editing_a_winning_trade_into_a_final_loss_shows_real_drawdown():
    # Trade 1 sets a peak; trade 2 (originally a win, edited to a loss)
    # is the last trade chronologically, so nothing recovers it.
    trades = [
        make_trade(
            symbol="mes", trade_date="2026-01-01",
            entry_time="09:30", net_dollar_pnl=200.0,
        ),
        make_trade(
            symbol="m2k", trade_date="2026-01-02",
            entry_time="09:30", net_dollar_pnl=-121.0,
        ),
    ]

    result = calculate_equity_drawdown_history(trades, 1000.0)

    assert result["ending_balance"] == pytest.approx(1079.0)
    assert result["high_water_mark"] == pytest.approx(1200.0)
    assert result["current_drawdown"] == pytest.approx(121.0)
    assert result["current_drawdown_percentage"] == pytest.approx(
        121.0 / 1200.0 * 100
    )


def test_loss_recovered_by_larger_later_trades_shows_zero_drawdown():
    # Mirrors the confirmed-correct Sprint 29 investigation: a loss sits
    # between two peaks, but a trade dated *after* it is large enough to
    # both recover the loss and set a brand-new high water mark. Current
    # drawdown is correctly zero, not the pre-loss peak.
    trades = [
        make_trade(
            symbol="mes", trade_date="2026-01-01",
            entry_time="09:30", net_dollar_pnl=1000.0,
        ),
        make_trade(
            symbol="m2k", trade_date="2026-01-02",
            entry_time="09:30", net_dollar_pnl=-121.0,
        ),
        make_trade(
            symbol="mes", trade_date="2026-01-03",
            entry_time="09:30", net_dollar_pnl=300.0,
        ),
    ]

    result = calculate_equity_drawdown_history(trades, 1000.0)

    assert result["ending_balance"] == pytest.approx(2179.0)
    assert result["high_water_mark"] == pytest.approx(2179.0)
    assert result["current_drawdown"] == 0.0
    assert result["current_drawdown_percentage"] == 0.0


def test_editing_a_losing_trade_into_a_win_clears_drawdown():
    trades = [
        make_trade(
            symbol="mes", trade_date="2026-01-01",
            entry_time="09:30", net_dollar_pnl=500.0,
        ),
        make_trade(
            symbol="mnq", trade_date="2026-01-02",
            entry_time="09:30", net_dollar_pnl=100.0,  # was a loss, edited to a win
        ),
    ]

    result = calculate_equity_drawdown_history(trades, 1000.0)

    assert result["ending_balance"] == pytest.approx(1600.0)
    assert result["high_water_mark"] == pytest.approx(1600.0)
    assert result["current_drawdown"] == 0.0
    assert result["current_drawdown_percentage"] == 0.0


def test_editing_an_earlier_historical_trade_rebuilds_all_later_balances():
    # Trade 1 (the earliest) is edited into a much bigger loss than
    # before; every later balance must shift by the same delta and the
    # high water mark must fall back to the starting balance, since the
    # edited loss now exceeds every later trade's recovery.
    trades = [
        make_trade(
            symbol="mes", trade_date="2026-01-01",
            entry_time="09:30", net_dollar_pnl=-2000.0,
        ),
        make_trade(
            symbol="mnq", trade_date="2026-01-02",
            entry_time="09:30", net_dollar_pnl=300.0,
        ),
        make_trade(
            symbol="mgc", trade_date="2026-01-03",
            entry_time="09:30", net_dollar_pnl=300.0,
        ),
    ]

    result = calculate_equity_drawdown_history(trades, 5000.0)

    assert [row["equity"] for row in result["history"]] == [
        3000.0, 3300.0, 3600.0,
    ]
    assert result["ending_balance"] == pytest.approx(3600.0)
    assert result["high_water_mark"] == pytest.approx(5000.0)
    assert result["maximum_drawdown_peak"] == "Starting Balance"
    assert result["current_drawdown"] == pytest.approx(1400.0)


def test_deleting_a_winning_trade_rebuilds_a_lower_peak():
    # Simulates the post-delete trades list (the big winner that used to
    # set the peak is simply absent) -- the peak must be recomputed from
    # what remains, not carried over from the deleted trade.
    remaining_trades = [
        make_trade(
            symbol="mes", trade_date="2026-01-01",
            entry_time="09:30", net_dollar_pnl=100.0,
        ),
        make_trade(
            symbol="mgc", trade_date="2026-01-03",
            entry_time="09:30", net_dollar_pnl=-50.0,
        ),
    ]

    result = calculate_equity_drawdown_history(remaining_trades, 1000.0)

    assert result["ending_balance"] == pytest.approx(1050.0)
    assert result["high_water_mark"] == pytest.approx(1100.0)
    assert result["current_drawdown"] == pytest.approx(50.0)


def test_deleting_a_losing_trade_removes_its_drawdown_contribution():
    remaining_trades = [
        make_trade(
            symbol="mes", trade_date="2026-01-01",
            entry_time="09:30", net_dollar_pnl=500.0,
        ),
        make_trade(
            symbol="mgc", trade_date="2026-01-03",
            entry_time="09:30", net_dollar_pnl=200.0,
        ),
    ]

    result = calculate_equity_drawdown_history(remaining_trades, 1000.0)

    assert result["ending_balance"] == pytest.approx(1700.0)
    assert result["high_water_mark"] == pytest.approx(1700.0)
    assert result["current_drawdown"] == 0.0


def test_final_losing_trade_below_previous_peak_shows_nonzero_drawdown():
    trades = [
        make_trade(
            symbol="mes", trade_date="2026-01-01",
            entry_time="09:30", net_dollar_pnl=800.0,
        ),
        make_trade(
            symbol="mnq", trade_date="2026-01-02",
            entry_time="09:30", net_dollar_pnl=-300.0,
        ),
    ]

    result = calculate_equity_drawdown_history(trades, 1000.0)

    assert result["ending_balance"] == pytest.approx(1500.0)
    assert result["high_water_mark"] == pytest.approx(1800.0)
    assert result["current_drawdown"] == pytest.approx(300.0)
    assert result["current_drawdown_percentage"] == pytest.approx(
        300.0 / 1800.0 * 100
    )


def test_starting_balance_remains_high_water_mark_when_all_trades_lose():
    trades = [
        make_trade(
            symbol="mes", trade_date="2026-01-01",
            entry_time="09:30", net_dollar_pnl=-100.0,
        ),
        make_trade(
            symbol="mnq", trade_date="2026-01-02",
            entry_time="09:30", net_dollar_pnl=-50.0,
        ),
        make_trade(
            symbol="mgc", trade_date="2026-01-03",
            entry_time="09:30", net_dollar_pnl=-25.0,
        ),
    ]

    result = calculate_equity_drawdown_history(trades, 1000.0)

    assert result["ending_balance"] == pytest.approx(825.0)
    assert result["high_water_mark"] == 1000.0
    assert result["maximum_drawdown_peak"] == "Starting Balance"
    assert result["current_drawdown"] == pytest.approx(175.0)
    assert result["current_drawdown_percentage"] == pytest.approx(17.5)


@pytest.mark.parametrize(
    ("trade", "expected"),
    [
        (
            {"trade_date": "2026-07-27"},
            "Monday",
        ),
        (
            {"trade_date": "2026 07 31"},
            "Friday",
        ),
        (
            {"trade_date": "invalid"},
            "Unspecified",
        ),
        (
            {},
            "Unspecified",
        ),
    ],
)
def test_get_trade_weekday(trade, expected):
    assert get_trade_weekday(trade) == expected


@pytest.mark.parametrize(
    ("trade", "expected"),
    [
        (
            {"entry_time": "09:00"},
            "09:00 - 09:59",
        ),
        (
            {"entry_time": "09:59"},
            "09:00 - 09:59",
        ),
        (
            {"entry_time": " 23:15 "},
            "23:00 - 23:59",
        ),
        (
            {"entry_time": "invalid"},
            "Unspecified",
        ),
        (
            {},
            "Unspecified",
        ),
    ],
)
def test_get_entry_hour_range(trade, expected):
    assert get_entry_hour_range(trade) == expected


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (0, "0 - 15 minutes"),
        (15, "0 - 15 minutes"),
        (16, "16 - 30 minutes"),
        (30, "16 - 30 minutes"),
        (31, "31 - 60 minutes"),
        (60, "31 - 60 minutes"),
        (61, "61 - 120 minutes"),
        (120, "61 - 120 minutes"),
        (121, "121 - 240 minutes"),
        (240, "121 - 240 minutes"),
        (241, "241+ minutes"),
        ("30", "16 - 30 minutes"),
        (-1, "Unspecified"),
        (True, "Unspecified"),
        (None, "Unspecified"),
        ("invalid", "Unspecified"),
    ],
)
def test_get_duration_range(duration, expected):
    assert get_duration_range(
        {"duration": duration}
    ) == expected


def test_calculate_time_based_analytics_aggregates_each_category():
    trades = [
        make_trade(
            trade_date="2026-07-27",
            entry_time="09:15",
            duration=10,
            dollar_pnl=100.0,
            net_dollar_pnl=95.0,
            net_result="Win",
            risk_amount=100.0,
        ),
        make_trade(
            trade_date="2026-07-27",
            entry_time="09:45",
            duration=15,
            dollar_pnl=-50.0,
            net_dollar_pnl=-55.0,
            net_result="Loss",
            risk_amount=100.0,
        ),
    ]

    weekdays, hours, durations = (
        calculate_time_based_analytics(trades)
    )

    for bucket in (
        weekdays["Monday"],
        hours["09:00 - 09:59"],
        durations["0 - 15 minutes"],
    ):
        assert bucket["total_trades"] == 2
        assert bucket["wins"] == 1
        assert bucket["losses"] == 1
        assert bucket["net_pnl"] == 40.0

        assert bucket[
            "average_realized_r"
        ] == pytest.approx(0.25)

        assert bucket[
            "net_profit_factor"
        ] == pytest.approx(95 / 55)


def test_calculate_time_based_analytics_returns_empty_dictionaries():
    assert calculate_time_based_analytics([]) == (
        {},
        {},
        {},
    )


@pytest.mark.parametrize(
    ("start_date", "end_date", "expected"),
    [
        (None, None, True),
        (date(2026, 7, 27), None, True),
        (date(2026, 7, 28), None, False),
        (None, date(2026, 7, 27), True),
        (None, date(2026, 7, 26), False),
        (
            date(2026, 7, 27),
            date(2026, 7, 27),
            True,
        ),
    ],
)
def test_trade_is_in_date_range(
    start_date,
    end_date,
    expected,
):
    trade = {"trade_date": "2026-07-27"}

    assert trade_is_in_date_range(
        trade,
        start_date,
        end_date,
    ) is expected


@pytest.mark.parametrize(
    "trade_date",
    [
        "invalid",
        "2026-02-30",
        "",
    ],
)
def test_trade_is_in_date_range_rejects_invalid_trade_date(
    trade_date,
):
    trade = {"trade_date": trade_date}

    assert trade_is_in_date_range(
        trade,
        date(2026, 1, 1),
        date(2026, 12, 31),
    ) is False