import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import journal.display as display

def make_bucket(**overrides):
    bucket = {
        "total_trades": 2,
        "net_pnl": 40.0, 
        "net_win_rate": 50.0, 
        "average_realized_r": 0.25,
        "net_profit_factor": 1.75,
    }
    bucket.update(overrides)
    return bucket

def make_unit_stats(**overrides):
    stats = {
        "title": "FUTURES POINT PERFORMANCE",
        "unit_label": "points",
        "total": 6.0,
        "average": 3.0,
        "best_idx": 0,
        "best_trade": {"symbol": "MES"},
        "best_value": 10.0,
        "worst_idx": 1,
        "worst_trade": {"symbol": "MNQ"},
        "worst_value": -4.0,
        "gross_profit": 10.0,
        "gross_loss": 4.0,
        "average_win": 10.0,
        "average_loss": 4.0,
        "profit_factor": 2.5,
        "expectancy": 3.0,
    }
    stats.update(overrides)
    return stats

def capture_output(function, *args, **kwargs):
    stream = io.StringIO()
    with redirect_stdout(stream):
        function(*args, **kwargs)
    return stream.getvalue()

class BasicDisplaysTest(unittest.TestCase):
    def test_show_menu_prints_title_and_all_options(self):
        output = capture_output(display.show_menu)

        self.assertIn("AI TRADING JOURNAL", output)
        for option_number in range(1, 17): 
            self.assertIn(f"{option_number}.", output)
        self.assertIn("16. Quit", output)

    def test_show_menu_prints_main_sections(self):
        output = capture_output(display.show_menu)

        self.assertIn("1. Account Status", output)
        self.assertIn("3. Add Trade", output)
        self.assertIn("7. Trading Statistics", output)
        self.assertIn("10. Session Analytics", output)
        self.assertIn("14. Save Trades", output)

    def test_print_futures_instrument_ptofile_formats_values(self): 
        profile = {
            "root": "MES",
            "name": "Micro E-mini S&P 500",
            "tick_size": 0.25, 
            "tick_value": 1.25,
            "point_value": 5.0,
        }

        output = capture_output(
            display.print_futures_instrument_profile,
            profile,
        )

        self.assertIn("MES - Micro E-mini S&P 500", output)
        self.assertIn("Tick size: 0.25", output)
        self.assertIn("Tick value: $1.25", output)
        self.assertIn("Point value: $5.00", output)

    def test_format_trade_price_returns_na_for_missing_values(self): 
        self.assertEqual(
            display.format_trade_price({}, "entry"),
            "N/A",
        )

    def test_format_trade_price_uses_forex_precision(self):
        trade = {
            "market_type": "forex", 
            "entry": 1.1, 
            "price_precision": 5
        }

        self.assertEqual(
            display.format_trade_price(trade, "entry"),
            "1.10000",
        )

    def test_format_trade_price_uses_jpy_precision(self): 
        trade = {
            "market_type": "forex", 
            "exit": 145.2, 
            "price_precision": 3,
        }

        self.assertEqual(
            display.format_trade_price(trade, "exit"),
            "145.200",
        )

    def test_format_trade_price_uses_plain_string_without_precision(self): 
        trade = {
            "market_type": "forex", 
            "entry": 1.2345,
        }

        self.assertEqual(
            display.format_trade_price(trade, "entry"),
            "1.2345",
        )

    def test_format_trade_price_does_not_apply_precision_to_futures(self): 
        trade = {
            "market_type": "futures",
            "entry": 7560.75,
            "price_precision": 2,
        }

        self.assertEqual(
            display.format_trade_price(trade, "entry"),
            "7560.75",
        )

    def test_format_trade_unit_summary_formats_forex_pips(self):
        trade = {
            "market_type": "forex",
            "pips_pnl": 12.75,
        }

        self.assertEqual(
            display.format_trade_unit_summary(trade),
            "Forex: 12.8 pips",
        )

    def test_format_trade_unit_summary_handles_missing_forex_pips(self): 
        trade = {
            "market_type": "forex",
            "pips_pnl": None,
        }
        
        self.assertEqual(
            display.format_trade_unit_summary(trade),
            "Forex: N/A pips",
        )

    def test_format_trade_unit_summary_formats_futures_points_and_ticks(self):
        trade = {
            "market_type": "futures",
            "points_pnl": 10.25,
            "ticks_pnl": 41.0,
        }

        self.assertEqual(
            display.format_trade_unit_summary(trade),
            "Futures: 10.25 pts (41.0 ticks)",
        )

    def test_format_trade_unit_summary_handles_missing_ticks(self):
        trade = {
            "market_type": "futures",
            "points_pnl": -4.0,
            "ticks_pnl": None,
        }

        self.assertEqual(
            display.format_trade_unit_summary(trade),
            "Futures: -4.00 pts",
        )

    def test_format_trade_unit_summary_treats_legacy_trade_as_futures(self):
        self.assertEqual(
            display.format_trade_unit_summary({"points_pnl": 5}),
            "Futures: 5.00 pts",
        )

    def test_print_trade_unit_detail_formats_forex_fields(self):
        trade = {
            "market_type": "forex",
            "lot_size": 0.5,
            "pip_size": 0.0001,
            "pip_value": 10.0,
            "pips_pnl": 17.25,
        }

        output = capture_output(display.print_trade_unit_detail, trade)

        self.assertIn("Lot Size: 0.5", output)
        self.assertIn("Pip Size: 0.0001", output)
        self.assertIn("Pip Value: $10.00", output)
        self.assertIn("Pips P/L: 17.2 pips", output)

    def test_print_trade_unit_detail_handles_missing_forex_fields(self):
        output = capture_output(
            display.print_trade_unit_detail,
            {"market_type": "forex"},
        )

        self.assertIn("Lot Size: N/A", output)
        self.assertIn("Pip Size: N/A", output)
        self.assertIn("Pip Value: N/A", output)
        self.assertIn("Pips P/L: N/A", output)

    def test_print_trade_unit_detail_recognizes_futures_symbol(self):
        trade = {
            "market_type": "futures",
            "symbol": "MESZ26",
            "contracts": 2,
            "point_value": 5.0,
            "tick_size": 0.25,
            "tick_value": 1.25,
            "ticks_pnl": 40.0,
            "points_pnl": 10.0,
        }

        output = capture_output(display.print_trade_unit_detail, trade)

        self.assertIn("Instrument: MES - Micro E-mini S&P 500", output)
        self.assertIn("Contracts: 2", output)
        self.assertIn("Point Value: $5.00", output)
        self.assertIn("Tick Size: 0.25", output)
        self.assertIn("Tick Value: $1.25", output)
        self.assertIn("Ticks P/L: 40.0 ticks", output)
        self.assertIn("Points P/L: 10.00 pts", output)

    def test_print_trade_unit_detail_handles_unknown_futures_symbol(self):
        trade = {
            "symbol": "CUSTOM",
            "contracts": 1,
            "point_value": 12.5,
            "tick_size": 0.5,
            "tick_value": 6.25,
            "ticks_pnl": -4.0,
            "points_pnl": -2.0,
        }

        output = capture_output(display.print_trade_unit_detail, trade)

        self.assertNotIn("Instrument:", output)
        self.assertIn("Contracts: 1", output)
        self.assertIn("Points P/L: -2.00 pts", output)

    def test_print_trade_unit_detail_handles_missing_futures_metadata(self):
        output = capture_output(
            display.print_trade_unit_detail,
            {"symbol": "CUSTOM"},
        )

        self.assertIn("Contracts: N/A", output)
        self.assertIn("Point Value: N/A", output)
        self.assertIn("Tick Size: N/A", output)
        self.assertIn("Tick Value: N/A", output)
        self.assertIn("Ticks P/L: N/A", output)
        self.assertIn("Points P/L: 0.00 pts", output)

    def test_print_unit_performance_stats_skips_empty_buckets(self):
        unit_stats = {
            "futures_points": None,
            "futures_ticks": None,
            "forex_pips": None,
        }

        self.assertEqual(
            capture_output(display.print_unit_performance_stats, unit_stats),
            "",
        )

    def test_print_unit_performance_stats_formats_complete_bucket(self):
        unit_stats = {
            "futures_points": make_unit_stats(),
            "futures_ticks": None,
            "forex_pips": None,
        }

        output = capture_output(
            display.print_unit_performance_stats,
            unit_stats,
        )

        self.assertIn("FUTURES POINT PERFORMANCE", output)
        self.assertIn("Total:", output)
        self.assertIn("6.00 points", output)
        self.assertIn("#1 MES (10.00 points)", output)
        self.assertIn("#2 MNQ (-4.00 points)", output)
        self.assertIn("-4.00 points", output)
        self.assertIn("Profit Factor:", output)
        self.assertIn("2.50", output)
        self.assertIn("3.00 points", output)

    def test_print_unit_performance_stats_handles_no_losing_trades(self):
        unit_stats = {
            "futures_points": make_unit_stats(
                gross_loss=0,
                average_loss=0,
                profit_factor=None,
            ),
            "futures_ticks": None,
            "forex_pips": None,
        }

        output = capture_output(
            display.print_unit_performance_stats,
            unit_stats,
        )

        self.assertIn("N/A (no losing trades)", output)

    def test_print_unit_performance_stats_prints_multiple_markets(self):
        unit_stats = {
            "futures_points": make_unit_stats(),
            "futures_ticks": None,
            "forex_pips": make_unit_stats(
                title="FOREX PIP PERFORMANCE",
                unit_label="pips",
            ),
        }

        output = capture_output(
            display.print_unit_performance_stats,
            unit_stats,
        )

        self.assertLess(
            output.index("FUTURES POINT PERFORMANCE"),
            output.index("FOREX PIP PERFORMANCE"),
        )


class CurrencyAndDrawdownFormattingTests(unittest.TestCase):
    def test_format_currency_formats_positive_value(self):
        self.assertEqual(display.format_currency(1234.5), "$1,234.50")

    def test_format_currency_formats_zero(self):
        self.assertEqual(display.format_currency(0), "$0.00")

    def test_format_currency_places_negative_sign_before_dollar(self):
        self.assertEqual(display.format_currency(-1234.5), "-$1,234.50")

    def test_format_drawdown_formats_positive_value_as_negative_amount(self):
        self.assertEqual(display.format_drawdown(250), "-$250.00")

    def test_format_drawdown_formats_zero(self):
        self.assertEqual(display.format_drawdown(0), "$0.00")

    def test_format_drawdown_treats_negative_value_as_zero(self):
        self.assertEqual(display.format_drawdown(-1), "$0.00")

    def test_format_drawdown_percentage_formats_positive_value(self):
        self.assertEqual(
            display.format_drawdown_percentage(2.345),
            "-2.35%",
        )

    def test_format_drawdown_percentage_formats_zero(self):
        self.assertEqual(
            display.format_drawdown_percentage(0),
            "0.00%",
        )


class SessionAnalyticsDisplayTests(unittest.TestCase):
    def test_display_session_analytics_handles_empty_trades(self):
        output = capture_output(display.display_session_analytics, [])

        self.assertEqual(
            output.strip(),
            "No trades to calculate session analytics.",
        )

    def test_display_session_analytics_prints_metrics_and_headings(self):
        analytics = {
            "New York": make_bucket(net_pnl=125.5),
            "New York/London Overlap": make_bucket(net_pnl=-20.0),
        }

        with patch.object(
            display,
            "calculate_session_analysis",
            return_value=analytics,
        ):
            output = capture_output(
                display.display_session_analytics,
                [{}],
            )

        self.assertIn("SESSION ANALYTICS", output)
        self.assertIn("NEW YORK/LONDON OVERLAP", output)
        self.assertIn("NEW YORK SESSION", output)
        self.assertIn("Total Trades:", output)
        self.assertIn("$125.50", output)
        self.assertIn("50.00%", output)
        self.assertIn("0.25R", output)
        self.assertIn("1.75", output)

    def test_display_session_analytics_uses_defined_display_order(self):
        analytics = {
            "New York": make_bucket(),
            "London": make_bucket(),
            "Sydney": make_bucket(),
        }

        with patch.object(
            display,
            "calculate_session_analysis",
            return_value=analytics,
        ):
            output = capture_output(
                display.display_session_analytics,
                [{}],
            )

        self.assertLess(output.index("SYDNEY SESSION"), output.index("LONDON SESSION"))
        self.assertLess(output.index("LONDON SESSION"), output.index("NEW YORK SESSION"))

    def test_display_session_analytics_handles_unavailable_r_and_profit_factor(self):
        analytics = {
            "London": make_bucket(
                average_realized_r=None,
                net_profit_factor=None,
            )
        }

        with patch.object(
            display,
            "calculate_session_analysis",
            return_value=analytics,
        ):
            output = capture_output(
                display.display_session_analytics,
                [{}],
            )

        self.assertIn("Average Realized R:", output)
        self.assertIn("Net Profit Factor:", output)
        self.assertIn("N/A (no losing trades)", output)

    def test_display_session_analytics_compares_best_and_worst(self):
        analytics = {
            "London": make_bucket(net_pnl=75.0),
            "New York": make_bucket(net_pnl=-25.0),
        }

        with patch.object(
            display,
            "calculate_session_analysis",
            return_value=analytics,
        ):
            output = capture_output(
                display.display_session_analytics,
                [{}],
            )

        self.assertIn("Best Session", output)
        self.assertIn("London ($75.00)", output)
        self.assertIn("Worst Session", output)
        self.assertIn("New York (-$25.00)", output)

    def test_display_session_analytics_excludes_maintenance_from_comparison(self):
        analytics = {
            display.MAINTENANCE_SESSION_NAME: make_bucket(net_pnl=999.0),
            "London": make_bucket(net_pnl=25.0),
        }

        with patch.object(
            display,
            "calculate_session_analysis",
            return_value=analytics,
        ):
            output = capture_output(
                display.display_session_analytics,
                [{}],
            )

        comparison = output.split("SESSION COMPARISON", 1)[1]
        self.assertIn("London ($25.00)", comparison)
        self.assertNotIn("$999.00", comparison)

    def test_display_session_analytics_handles_only_maintenance(self):
        analytics = {
            display.MAINTENANCE_SESSION_NAME: make_bucket(),
        }

        with patch.object(
            display,
            "calculate_session_analysis",
            return_value=analytics,
        ):
            output = capture_output(
                display.display_session_analytics,
                [{}],
            )

        self.assertIn("N/A (no comparable sessions)", output)


class SetupAndStrategyDisplayTests(unittest.TestCase):
    def test_display_setup_buckets_sorts_names_case_insensitively(self):
        buckets = {
            "Order Block": make_bucket(),
            "Fair Value Gap": make_bucket(),
        }

        output = capture_output(display._display_setup_buckets, buckets)

        self.assertLess(
            output.index("FAIR VALUE GAP"),
            output.index("ORDER BLOCK"),
        )

    def test_display_setup_buckets_formats_missing_metrics(self):
        buckets = {
            "Liquidity Sweep": make_bucket(
                average_realized_r=None,
                net_profit_factor=None,
            )
        }

        output = capture_output(display._display_setup_buckets, buckets)

        self.assertIn("Average Realized R:", output)
        self.assertIn("N/A", output)
        self.assertIn("N/A (no losing trades)", output)

    def test_display_setup_analytics_handles_empty_trades(self):
        output = capture_output(display.display_setup_analytics, [])

        self.assertEqual(
            output.strip(),
            "No trades to calculate setup analytics.",
        )

    def test_display_setup_analytics_prints_components_and_combinations(self):
        components = {
            "Order Block": make_bucket(net_pnl=50.0),
            "Liquidity Sweep": make_bucket(net_pnl=-10.0),
        }
        combinations = {
            "Liquidity Sweep + Order Block": make_bucket(net_pnl=40.0),
        }

        with patch.object(
            display,
            "calculate_setup_analysis",
            return_value=(components, combinations),
        ):
            output = capture_output(display.display_setup_analytics, [{}])

        self.assertIn("SETUP COMPONENT ANALYTICS", output)
        self.assertIn("EXACT MULTI-COMPONENT COMBINATION ANALYTICS", output)
        self.assertIn("LIQUIDITY SWEEP + ORDER BLOCK", output)
        self.assertIn("Best Component", output)
        self.assertIn("Order Block ($50.00)", output)
        self.assertIn("Worst Component", output)
        self.assertIn("Liquidity Sweep (-$10.00)", output)

    def test_display_setup_analytics_handles_no_combinations(self):
        with patch.object(
            display,
            "calculate_setup_analysis",
            return_value=({"Order Block": make_bucket()}, {}),
        ):
            output = capture_output(display.display_setup_analytics, [{}])

        self.assertIn(
            "No trades contain two or more setup components yet.",
            output,
        )

    def test_display_setup_analytics_excludes_unspecified_from_comparison(self):
        components = {
            "Unspecified": make_bucket(net_pnl=500.0),
            "Order Block": make_bucket(net_pnl=10.0),
        }

        with patch.object(
            display,
            "calculate_setup_analysis",
            return_value=(components, {}),
        ):
            output = capture_output(display.display_setup_analytics, [{}])

        comparison = output.split("SETUP COMPONENT COMPARISON", 1)[1]
        self.assertIn("Order Block ($10.00)", comparison)
        self.assertNotIn("$500.00", comparison)

    def test_display_setup_analytics_handles_only_unspecified_component(self):
        with patch.object(
            display,
            "calculate_setup_analysis",
            return_value=({"Unspecified": make_bucket()}, {}),
        ):
            output = capture_output(display.display_setup_analytics, [{}])

        self.assertIn("N/A (no specified components)", output)

    def test_display_strategy_analytics_prints_nothing_for_empty_trades(self):
        self.assertEqual(
            capture_output(display.display_strategy_method_analytics, []),
            "",
        )

    def test_display_strategy_analytics_prints_methods_and_combinations(self):
        strategies = {
            "ICT": make_bucket(net_pnl=100.0),
            "Order Flow": make_bucket(net_pnl=-20.0),
        }
        combinations = {
            "ICT + Order Flow": make_bucket(net_pnl=80.0),
        }

        with patch.object(
            display,
            "calculate_strategy_method_analysis",
            return_value=(strategies, combinations),
        ):
            output = capture_output(
                display.display_strategy_method_analytics,
                [{}],
            )

        self.assertIn("STRATEGY / METHOD ANALYTICS", output)
        self.assertIn("STRATEGY / METHOD COMBINATION ANALYTICS", output)
        self.assertIn("ICT + ORDER FLOW", output)
        self.assertIn("ICT ($100.00)", output)
        self.assertIn("Order Flow (-$20.00)", output)

    def test_display_strategy_analytics_handles_no_combinations(self):
        with patch.object(
            display,
            "calculate_strategy_method_analysis",
            return_value=({"ICT": make_bucket()}, {}),
        ):
            output = capture_output(
                display.display_strategy_method_analytics,
                [{}],
            )

        self.assertIn(
            "No trades contain two or more strategies/methods yet.",
            output,
        )

    def test_display_strategy_analytics_excludes_unspecified_from_comparison(self):
        strategies = {
            "Unspecified": make_bucket(net_pnl=500.0),
            "ICT": make_bucket(net_pnl=25.0),
        }

        with patch.object(
            display,
            "calculate_strategy_method_analysis",
            return_value=(strategies, {}),
        ):
            output = capture_output(
                display.display_strategy_method_analytics,
                [{}],
            )

        comparison = output.split("STRATEGY / METHOD COMPARISON", 1)[1]
        self.assertIn("ICT ($25.00)", comparison)
        self.assertNotIn("$500.00", comparison)

    def test_display_strategy_analytics_handles_only_unspecified_strategy(self):
        with patch.object(
            display,
            "calculate_strategy_method_analysis",
            return_value=({"Unspecified": make_bucket()}, {}),
        ):
            output = capture_output(
                display.display_strategy_method_analytics,
                [{}],
            )

        self.assertIn("N/A (no specified strategies)", output)


class EquityDrawdownDisplayTests(unittest.TestCase):
    def test_display_equity_history_requires_account(self):
        output = capture_output(
            display.display_equity_drawdown_history,
            [],
            None,
        )

        self.assertIn("No account has been created yet", output)
        self.assertIn("Account Status", output)

    def test_display_equity_history_handles_no_trades(self):
        equity_data = {
            "history": [],
            "starting_balance": 25000.0,
            "ending_balance": 25000.0,
            "net_change": 0.0,
            "high_water_mark": 25000.0,
            "current_drawdown": 0.0,
            "current_drawdown_percentage": 0.0,
            "maximum_drawdown": 0.0,
            "maximum_drawdown_percentage": 0.0,
            "maximum_drawdown_peak": "Starting Balance",
            "maximum_drawdown_trough": "N/A",
            "unspecified_datetime_trades": 0,
        }

        with patch.object(
            display,
            "calculate_equity_drawdown_history",
            return_value=equity_data,
        ) as mocked_calculation:
            output = capture_output(
                display.display_equity_drawdown_history,
                [],
                {"starting_balance": 25000},
            )

        mocked_calculation.assert_called_once_with([], 25000)
        self.assertIn("EQUITY & DRAWDOWN HISTORY", output)
        self.assertIn("No trades to display.", output)
        self.assertIn("Starting Balance:", output)
        self.assertIn("$25,000.00", output)
        self.assertIn("Maximum Drawdown Peak:", output)
        self.assertIn("Starting Balance", output)

    def test_display_equity_history_prints_rows_and_summary(self):
        equity_data = {
            "history": [
                {
                    "trade_number": 2,
                    "trade_date": "2026-07-30",
                    "entry_time": "09:30",
                    "symbol": "MES",
                    "net_dollar_pnl": -50.0,
                    "equity": 1050.0,
                    "high_water_mark": 1100.0,
                    "drawdown": 50.0,
                    "drawdown_percentage": 4.545,
                }
            ],
            "starting_balance": 1000.0,
            "ending_balance": 1050.0,
            "net_change": 50.0,
            "high_water_mark": 1100.0,
            "current_drawdown": 50.0,
            "current_drawdown_percentage": 4.545,
            "maximum_drawdown": 50.0,
            "maximum_drawdown_percentage": 4.545,
            "maximum_drawdown_peak": "Trade #1",
            "maximum_drawdown_trough": "Trade #2",
            "unspecified_datetime_trades": 0,
        }

        with patch.object(
            display,
            "calculate_equity_drawdown_history",
            return_value=equity_data,
        ):
            output = capture_output(
                display.display_equity_drawdown_history,
                [{"symbol": "MES"}],
                {"starting_balance": 1000},
            )

        self.assertIn("2026-07-30", output)
        self.assertIn("MES", output)
        self.assertIn("-$50.00", output)
        self.assertIn("$1,050.00", output)
        self.assertIn("-$50.00", output)
        self.assertIn("-4.54%", output)
        self.assertIn("Ending Balance:", output)
        self.assertIn("Maximum Drawdown Trough:", output)
        self.assertIn("Trade #2", output)
        self.assertIn("closed-trade equity after commission", output)

    def test_display_equity_history_warns_about_unspecified_datetimes(self):
        equity_data = {
            "history": [],
            "starting_balance": 1000.0,
            "ending_balance": 1000.0,
            "net_change": 0.0,
            "high_water_mark": 1000.0,
            "current_drawdown": 0.0,
            "current_drawdown_percentage": 0.0,
            "maximum_drawdown": 0.0,
            "maximum_drawdown_percentage": 0.0,
            "maximum_drawdown_peak": "Starting Balance",
            "maximum_drawdown_trough": "N/A",
            "unspecified_datetime_trades": 2,
        }

        with patch.object(
            display,
            "calculate_equity_drawdown_history",
            return_value=equity_data,
        ):
            output = capture_output(
                display.display_equity_drawdown_history,
                [{}],
                {"starting_balance": 1000},
            )

        self.assertIn("Warning: 2 trade(s)", output)
        self.assertIn("placed at the end in original order", output)

    def test_display_equity_history_omits_warning_when_dates_are_valid(self):
        equity_data = {
            "history": [],
            "starting_balance": 1000.0,
            "ending_balance": 1000.0,
            "net_change": 0.0,
            "high_water_mark": 1000.0,
            "current_drawdown": 0.0,
            "current_drawdown_percentage": 0.0,
            "maximum_drawdown": 0.0,
            "maximum_drawdown_percentage": 0.0,
            "maximum_drawdown_peak": "Starting Balance",
            "maximum_drawdown_trough": "N/A",
            "unspecified_datetime_trades": 0,
        }

        with patch.object(
            display,
            "calculate_equity_drawdown_history",
            return_value=equity_data,
        ):
            output = capture_output(
                display.display_equity_drawdown_history,
                [],
                {"starting_balance": 1000},
            )

        self.assertNotIn("Warning:", output)


class TimeAnalyticsDisplayTests(unittest.TestCase):
    def test_display_time_buckets_sorts_names_without_display_order(self):
        buckets = {
            "10:00 - 10:59": make_bucket(),
            "09:00 - 09:59": make_bucket(),
        }

        output = capture_output(display._display_time_buckets, buckets)

        self.assertLess(
            output.index("09:00 - 09:59"),
            output.index("10:00 - 10:59"),
        )

    def test_display_time_buckets_uses_supplied_order_then_extras(self):
        buckets = {
            "Wednesday": make_bucket(),
            "Monday": make_bucket(),
            "Custom": make_bucket(),
        }

        output = capture_output(
            display._display_time_buckets,
            buckets,
            ("Monday", "Wednesday"),
        )

        self.assertLess(output.index("MONDAY"), output.index("WEDNESDAY"))
        self.assertLess(output.index("WEDNESDAY"), output.index("CUSTOM"))

    def test_display_time_comparison_handles_only_unspecified_bucket(self):
        output = capture_output(
            display._display_time_comparison,
            "Weekday",
            {"Unspecified": make_bucket()},
        )

        self.assertIn("Best Weekday", output)
        self.assertIn("N/A", output)
        self.assertNotIn("Worst Weekday", output)

    def test_display_time_comparison_prints_singular_trade_word(self):
        buckets = {
            "Monday": make_bucket(total_trades=1, net_pnl=100.0),
            "Tuesday": make_bucket(total_trades=1, net_pnl=-50.0),
        }

        output = capture_output(
            display._display_time_comparison,
            "Weekday",
            buckets,
        )

        self.assertIn("Monday ($100.00, 1 trade)", output)
        self.assertIn("Tuesday (-$50.00, 1 trade)", output)

    def test_display_time_comparison_prints_plural_trade_word(self):
        buckets = {
            "09:00 - 09:59": make_bucket(total_trades=2, net_pnl=100.0),
            "10:00 - 10:59": make_bucket(total_trades=3, net_pnl=-50.0),
        }

        output = capture_output(
            display._display_time_comparison,
            "Entry Hour",
            buckets,
        )

        self.assertIn("2 trades", output)
        self.assertIn("3 trades", output)

    def test_display_time_comparison_excludes_unspecified_bucket(self):
        buckets = {
            "Unspecified": make_bucket(net_pnl=999.0),
            "Monday": make_bucket(net_pnl=20.0),
            "Tuesday": make_bucket(net_pnl=-10.0),
        }

        output = capture_output(
            display._display_time_comparison,
            "Weekday",
            buckets,
        )

        self.assertIn("Monday ($20.00", output)
        self.assertIn("Tuesday (-$10.00", output)
        self.assertNotIn("$999.00", output)

    def test_display_time_based_analytics_handles_empty_trades(self):
        output = capture_output(display.display_time_based_analytics, [])

        self.assertEqual(
            output.strip(),
            "No trades to calculate time-based analytics.",
        )

    def test_display_time_based_analytics_prints_all_sections(self):
        weekdays = {
            "Monday": make_bucket(total_trades=2, net_pnl=50.0),
            "Tuesday": make_bucket(total_trades=1, net_pnl=-10.0),
        }
        hours = {
            "09:00 - 09:59": make_bucket(total_trades=2, net_pnl=50.0),
            "10:00 - 10:59": make_bucket(total_trades=1, net_pnl=-10.0),
        }
        durations = {
            "0 - 15 minutes": make_bucket(total_trades=2, net_pnl=50.0),
            "16 - 30 minutes": make_bucket(total_trades=1, net_pnl=-10.0),
        }

        with patch.object(
            display,
            "calculate_time_based_analytics",
            return_value=(weekdays, hours, durations),
        ) as mocked_calculation:
            output = capture_output(
                display.display_time_based_analytics,
                [{}],
            )

        mocked_calculation.assert_called_once_with([{}])
        self.assertIn("DAY-OF-WEEK ANALYTICS", output)
        self.assertIn("ENTRY-HOUR ANALYTICS", output)
        self.assertIn("TRADE-DURATION ANALYTICS", output)
        self.assertIn("TIME-BASED COMPARISONS", output)
        self.assertIn("Best Weekday", output)
        self.assertIn("Worst Entry Hour", output)
        self.assertIn("Best Trade Duration", output)
        self.assertIn("Always consider the trade count", output)


if __name__ == "__main__":
    unittest.main()