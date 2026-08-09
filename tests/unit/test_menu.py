import io
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import call, patch

import journal.menu as menu


def capture_output(function, *args, **kwargs):
    stream = io.StringIO()
    with redirect_stdout(stream):
        result = function(*args, **kwargs)
    return result, stream.getvalue()


def make_equity_data(**overrides):
    data = {
        "ending_balance": 1025.0,
        "net_change": 25.0,
        "high_water_mark": 1050.0,
        "current_drawdown": 25.0,
        "current_drawdown_percentage": 25 / 1050 * 100,
        "maximum_drawdown": 75.0,
        "maximum_drawdown_percentage": 7.5,
    }
    data.update(overrides)
    return data


def make_trade(**overrides):
    trade = {
        "symbol": "MES",
        "direction": "long",
        "market_type": "futures",
        "entry": 5000.0,
        "exit": 5010.0,
        "contracts": 1,
        "tick_size": 0.25,
        "tick_value": 1.25,
        "point_value": 5.0,
        "points_pnl": 10.0,
        "ticks_pnl": 40.0,
        "dollar_pnl": 50.0,
        "commission": 2.0,
        "net_dollar_pnl": 48.0,
        "result": "Win",
        "net_result": "Win",
        "risk_amount": 25.0,
        "realized_r": 2.0,
        "trade_date": "2026-07-27",
        "entry_time": "09:30",
        "exit_time": "09:45",
        "duration": 15,
        "strategy_methods": ["ICT"],
        "setup_components": ["Fair Value Gap (FVG)"],
        "session": "New York/London Overlap",
        "notes": "Test note",
        "mistake": "None",
    }
    trade.update(overrides)
    return trade


class AccountStatusTests(unittest.TestCase):
    def test_creates_account_when_none_and_save_succeeds(self):
        equity = make_equity_data(
            ending_balance=10000.0,
            net_change=0.0,
            high_water_mark=10000.0,
            current_drawdown=0.0,
            current_drawdown_percentage=0.0,
            maximum_drawdown=0.0,
            maximum_drawdown_percentage=0.0,
        )

        with (
            patch.object(menu, "prompt_required_text", return_value="Evaluation 1"),
            patch.object(menu, "prompt_choice", return_value="2"),
            patch.object(menu, "prompt_finite_number", return_value=10000.0),
            patch.object(menu, "save_account", return_value=True) as save_mock,
            patch.object(
                menu,
                "calculate_equity_drawdown_history",
                return_value=equity,
            ),
        ):
            account, output = capture_output(
                menu.handle_account_status,
                [],
                None,
            )

        self.assertEqual(account["name"], "Evaluation 1")
        self.assertEqual(account["type"], "Evaluation")
        self.assertEqual(account["starting_balance"], 10000.0)
        self.assertIn("created successfully", output)
        self.assertIn("ACCOUNT STATUS", output)
        save_mock.assert_called_once()

    def test_returns_none_when_new_account_cannot_be_saved(self):
        with (
            patch.object(menu, "prompt_required_text", return_value="Account"),
            patch.object(menu, "prompt_choice", return_value="1"),
            patch.object(menu, "prompt_finite_number", return_value=5000.0),
            patch.object(menu, "save_account", return_value=False),
            patch.object(
                menu,
                "calculate_equity_drawdown_history",
            ) as equity_mock,
        ):
            account, output = capture_output(
                menu.handle_account_status,
                [],
                None,
            )

        self.assertIsNone(account)
        self.assertIn("could not be saved", output)
        equity_mock.assert_not_called()

    def test_updates_changed_high_water_mark(self):
        account = {
            "name": "Funded",
            "type": "Funded",
            "starting_balance": 10000.0,
            "high_water_mark": 10000.0,
        }

        with (
            patch.object(
                menu,
                "calculate_equity_drawdown_history",
                return_value=make_equity_data(high_water_mark=1050.0),
            ),
            patch.object(menu, "save_account", return_value=True) as save_mock,
        ):
            result, _ = capture_output(
                menu.handle_account_status,
                [],
                account,
            )

        self.assertIs(result, account)
        self.assertEqual(account["high_water_mark"], 1050.0)
        save_mock.assert_called_once_with(account)

    def test_restores_high_water_mark_when_save_fails(self):
        account = {
            "name": "Funded",
            "type": "Funded",
            "starting_balance": 1000.0,
            "high_water_mark": 1000.0,
        }

        with (
            patch.object(
                menu,
                "calculate_equity_drawdown_history",
                return_value=make_equity_data(high_water_mark=1100.0),
            ),
            patch.object(menu, "save_account", return_value=False),
        ):
            capture_output(menu.handle_account_status, [], account)

        self.assertEqual(account["high_water_mark"], 1000.0)

    def test_displays_profit_growth_and_currency(self):
        account = {
            "name": "Personal",
            "type": "Personal",
            "starting_balance": 1000.0,
            "high_water_mark": 1050.0,
            "account_currency": "CAD",
        }

        with patch.object(
            menu,
            "calculate_equity_drawdown_history",
            return_value=make_equity_data(),
        ):
            _, output = capture_output(
                menu.handle_account_status,
                [],
                account,
            )

        self.assertIn("Account Currency: CAD", output)
        self.assertIn("Net Profit: $25.00", output)
        self.assertIn("Growth: 2.50%", output)

    def test_displays_net_loss(self):
        account = {
            "name": "Evaluation",
            "type": "Evaluation",
            "starting_balance": 1000.0,
            "high_water_mark": 1000.0,
        }
        equity = make_equity_data(
            ending_balance=900.0,
            net_change=-100.0,
            high_water_mark=1000.0,
            current_drawdown=100.0,
            current_drawdown_percentage=10.0,
        )

        with patch.object(
            menu,
            "calculate_equity_drawdown_history",
            return_value=equity,
        ):
            _, output = capture_output(
                menu.handle_account_status,
                [],
                account,
            )

        self.assertIn("Net Loss: -$100.00", output)
        self.assertIn("Growth: -10.00%", output)

    def test_zero_starting_balance_avoids_division_by_zero(self):
        account = {
            "name": "Demo",
            "type": "Personal",
            "starting_balance": 0.0,
            "high_water_mark": 0.0,
        }
        equity = make_equity_data(
            ending_balance=0.0,
            net_change=0.0,
            high_water_mark=0.0,
            current_drawdown=0.0,
            current_drawdown_percentage=0.0,
            maximum_drawdown=0.0,
            maximum_drawdown_percentage=0.0,
        )

        with patch.object(
            menu,
            "calculate_equity_drawdown_history",
            return_value=equity,
        ):
            _, output = capture_output(
                menu.handle_account_status,
                [],
                account,
            )

        self.assertIn("Net P/L: $0.00", output)
        self.assertIn("Growth: 0.00%", output)


class EditAccountTests(unittest.TestCase):
    def test_none_account_is_not_edited(self):
        result, output = capture_output(
            menu.handle_edit_account,
            None,
            [],
        )

        self.assertIsNone(result)
        self.assertIn("No account has been created", output)

    def test_blank_inputs_keep_current_values(self):
        account = {
            "name": "Current",
            "type": "Funded",
            "starting_balance": 25000.0,
            "high_water_mark": 25100.0,
            "account_currency": "USD",
        }

        with (
            patch("builtins.input", side_effect=["", ""]),
            patch.object(menu, "prompt_choice", return_value=""),
            patch.object(menu, "prompt_finite_number", return_value=25000.0),
            patch.object(
                menu,
                "calculate_equity_drawdown_history",
                return_value=make_equity_data(high_water_mark=25100.0),
            ),
            patch.object(menu, "save_account", return_value=True),
        ):
            result, output = capture_output(
                menu.handle_edit_account,
                account,
                [],
            )

        self.assertEqual(result["name"], "Current")
        self.assertEqual(result["type"], "Funded")
        self.assertEqual(result["account_currency"], "USD")
        self.assertIn("updated successfully", output)

    def test_accepts_changed_name_type_balance_and_currency(self):
        account = {
            "name": "Old",
            "type": "Personal",
            "starting_balance": 1000.0,
            "high_water_mark": 1000.0,
            "account_currency": "USD",
        }

        with (
            patch("builtins.input", side_effect=["New", "CAD"]),
            patch.object(menu, "prompt_choice", return_value="2"),
            patch.object(menu, "prompt_finite_number", return_value=2000.0),
            patch.object(
                menu,
                "calculate_equity_drawdown_history",
                return_value=make_equity_data(high_water_mark=2050.0),
            ),
            patch.object(menu, "save_account", return_value=True),
        ):
            result, _ = capture_output(
                menu.handle_edit_account,
                account,
                [],
            )

        self.assertEqual(result["name"], "New")
        self.assertEqual(result["type"], "Evaluation")
        self.assertEqual(result["starting_balance"], 2000.0)
        self.assertEqual(result["account_currency"], "CAD")
        self.assertEqual(result["high_water_mark"], 2050.0)

    def test_invalid_currency_retries(self):
        account = {
            "name": "Account",
            "type": "Personal",
            "starting_balance": 1000.0,
            "high_water_mark": 1000.0,
            "account_currency": "USD",
        }

        with (
            patch("builtins.input", side_effect=["", "US", "ABC", "CAD"]),
            patch.object(menu, "prompt_choice", return_value=""),
            patch.object(menu, "prompt_finite_number", return_value=1000.0),
            patch.object(
                menu,
                "calculate_equity_drawdown_history",
                return_value=make_equity_data(high_water_mark=1000.0),
            ),
            patch.object(menu, "save_account", return_value=True),
        ):
            result, output = capture_output(
                menu.handle_edit_account,
                account,
                [],
            )

        self.assertEqual(result["account_currency"], "CAD")
        self.assertEqual(output.count("recognized three-letter"), 2)

    def test_save_failure_preserves_original_account(self):
        account = {
            "name": "Original",
            "type": "Personal",
            "starting_balance": 1000.0,
            "high_water_mark": 1000.0,
            "account_currency": "USD",
        }

        with (
            patch("builtins.input", side_effect=["Changed", "CAD"]),
            patch.object(menu, "prompt_choice", return_value="3"),
            patch.object(menu, "prompt_finite_number", return_value=2000.0),
            patch.object(
                menu,
                "calculate_equity_drawdown_history",
                return_value=make_equity_data(high_water_mark=2000.0),
            ),
            patch.object(menu, "save_account", return_value=False),
        ):
            result, output = capture_output(
                menu.handle_edit_account,
                account,
                [],
            )

        self.assertIs(result, account)
        self.assertEqual(result["name"], "Original")
        self.assertIn("changes were not applied", output)


class AddTradeTests(unittest.TestCase):
    def futures_patches(self, normalized, errors=None, save_result=True):
        if errors is None:
            errors = []
        return (
            patch.object(menu, "prompt_choice", side_effect=["futures", "long"]),
            patch.object(menu, "prompt_required_text", return_value="MES"),
            patch.object(menu, "prompt_positive_integer", return_value=2),
            patch.object(menu, "resolve_futures_tick_metadata", return_value=(0.25, 1.25)),
            patch.object(menu, "prompt_futures_price", side_effect=[5000.0, 5010.0]),
            patch.object(menu, "prompt_finite_number", side_effect=[100.0, 4.0]),
            patch.object(menu, "prompt_date", return_value="2026-07-27"),
            patch.object(menu, "prompt_time", side_effect=["09:30", "09:45"]),
            patch("builtins.input", side_effect=["ICT", "FVG", "note", "none"]),
            patch.object(menu, "validate_and_normalize_trade", return_value=(normalized, errors)),
            patch.object(menu, "save_trades", return_value=save_result),
        )

    def test_adds_and_saves_valid_futures_trade(self):
        trades = []
        normalized = make_trade(contracts=2)
        patchers = self.futures_patches(normalized)

        with patchers[0], patchers[1], patchers[2], patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9] as validate_mock, patchers[10] as save_mock:
            _, output = capture_output(
                menu.handle_add_trade,
                trades,
                {"account_currency": "USD"},
            )

        self.assertEqual(trades, [normalized])
        self.assertIn("Trade added successfully", output)
        validate_mock.assert_called_once()
        save_mock.assert_called_once_with(trades)

    def test_rolls_back_futures_trade_when_save_fails(self):
        trades = []
        normalized = make_trade()
        patchers = self.futures_patches(
            normalized,
            save_result=False,
        )

        with patchers[0], patchers[1], patchers[2], patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9], patchers[10]:
            _, output = capture_output(
                menu.handle_add_trade,
                trades,
                {"account_currency": "USD"},
            )

        self.assertEqual(trades, [])
        self.assertIn("could not be saved", output)

    def test_validation_errors_prevent_add_and_save(self):
        trades = []
        patchers = self.futures_patches(
            None,
            errors=["Entry price is invalid.", "Risk amount is invalid."],
        )

        with patchers[0], patchers[1], patchers[2], patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9], patchers[10] as save_mock:
            _, output = capture_output(
                menu.handle_add_trade,
                trades,
                {"account_currency": "USD"},
            )

        self.assertEqual(trades, [])
        self.assertIn("Trade was not added", output)
        self.assertIn("Entry price is invalid", output)
        self.assertIn("Risk amount is invalid", output)
        save_mock.assert_not_called()

    def test_adds_valid_forex_trade_with_conversion_metadata(self):
        trades = []
        account = {"account_currency": "CAD"}
        normalized = make_trade(
            market_type="forex",
            symbol="EUR/USD",
            contracts=None,
            tick_size=None,
            tick_value=None,
            lot_size=0.5,
            pip_size=0.0001,
            pip_value=13.5,
            price_precision=5,
            pips_pnl=10.0,
        )
        pip_info = {
            "pip_value": 13.5,
            "conversion_rate": 1.35,
            "conversion_pair": "USD/CAD",
            "conversion_timestamp": "2026-07-27 09:45",
            "conversion_rate_source": "manual",
        }

        with (
            patch.object(menu, "prompt_choice", side_effect=["forex", "short"]),
            patch.object(menu, "prompt_required_text", return_value="EUR/USD"),
            patch.object(menu, "ensure_account_currency") as ensure_mock,
            patch.object(menu, "prompt_finite_number", side_effect=[0.5, 100.0, 4.0]),
            patch.object(menu, "resolve_forex_pair_profile", return_value=(0.0001, 5, True)),
            patch.object(menu, "prompt_forex_price", side_effect=[1.1, 1.099]),
            patch.object(menu, "prompt_date", return_value="2026-07-27"),
            patch.object(menu, "prompt_time", side_effect=["09:30", "09:45"]),
            patch.object(menu, "resolve_forex_pip_value", return_value=pip_info) as pip_mock,
            patch("builtins.input", side_effect=["Order Flow", "CVD", "note", "none"]),
            patch.object(menu, "validate_and_normalize_trade", return_value=(normalized, [])) as validate_mock,
            patch.object(menu, "save_trades", return_value=True),
        ):
            _, output = capture_output(
                menu.handle_add_trade,
                trades,
                account,
            )

        self.assertEqual(trades, [normalized])
        self.assertIn("Trade added successfully", output)
        ensure_mock.assert_called_once_with(account)
        pip_mock.assert_called_once()
        raw_trade = validate_mock.call_args.args[0]
        self.assertEqual(raw_trade["account_currency"], "CAD")
        self.assertEqual(raw_trade["conversion_pair"], "USD/CAD")

    def test_unrecognized_entry_time_records_unspecified_session(self):
        trades = []
        normalized = make_trade(session="Unspecified")
        patchers = self.futures_patches(normalized)

        with patchers[0], patchers[1], patchers[2], patchers[3], patchers[4], patchers[5], patchers[6], patchers[7], patchers[8], patchers[9] as validate_mock, patchers[10], patch.object(menu, "determine_session", return_value=None):
            _, output = capture_output(
                menu.handle_add_trade,
                trades,
                {"account_currency": "USD"},
            )

        self.assertIn("Session automatically assigned: Unspecified", output)
        self.assertEqual(
            validate_mock.call_args.args[0]["session"] if "session" in validate_mock.call_args.args[0] else "Unspecified",
            "Unspecified",
        )


class ViewTradeTests(unittest.TestCase):
    def test_empty_trade_list_prints_message(self):
        _, output = capture_output(menu.handle_view_trades, [])
        self.assertIn("No trades yet", output)

    def test_blank_selection_returns_after_summary(self):
        trades = [make_trade()]

        with patch("builtins.input", return_value=""):
            _, output = capture_output(menu.handle_view_trades, trades)

        self.assertIn("Trades (1 total)", output)
        self.assertIn("MES", output)
        self.assertNotIn("Trade #1", output)

    def test_non_numeric_selection_is_rejected(self):
        with patch("builtins.input", return_value="abc"):
            _, output = capture_output(
                menu.handle_view_trades,
                [make_trade()],
            )

        self.assertIn("Invalid trade number", output)

    def test_out_of_range_selection_is_rejected(self):
        with patch("builtins.input", return_value="2"):
            _, output = capture_output(
                menu.handle_view_trades,
                [make_trade()],
            )

        self.assertIn("Invalid trade number", output)

    def test_valid_selection_prints_full_trade_details(self):
        trade = make_trade()

        with (
            patch("builtins.input", return_value="1"),
            patch.object(menu, "print_trade_unit_detail") as detail_mock,
        ):
            _, output = capture_output(
                menu.handle_view_trades,
                [trade],
            )

        self.assertIn("Trade #1", output)
        self.assertIn("Gross Dollar P/L: $50.00", output)
        self.assertIn("Net Dollar P/L: $48.00", output)
        self.assertIn("Realized R: 2.00R", output)
        self.assertIn("Strategy / Method: ICT", output)
        detail_mock.assert_called_once_with(trade)


class EditTradeGuardTests(unittest.TestCase):
    def test_empty_trade_list_prints_message(self):
        _, output = capture_output(
            menu.handle_edit_trade,
            [],
            None,
        )
        self.assertIn("No trades to edit", output)

    def test_non_numeric_trade_number_is_rejected(self):
        with patch("builtins.input", return_value="abc"):
            _, output = capture_output(
                menu.handle_edit_trade,
                [make_trade()],
                None,
            )
        self.assertIn("Invalid trade number", output)

    def test_out_of_range_trade_number_leaves_trade_unchanged(self):
        trades = [make_trade()]
        original = dict(trades[0])

        with patch("builtins.input", return_value="2"):
            _, output = capture_output(
                menu.handle_edit_trade,
                trades,
                None,
            )

        self.assertEqual(trades[0], original)
        self.assertNotIn("updated successfully", output)

    def run_existing_futures_edit(
        self,
        *,
        normalized_trade,
        validation_errors=None,
        save_result=True,
    ):
        if validation_errors is None:
            validation_errors = []

        current = make_trade()
        trades = [current]
        profile = {
            "root": "MES",
            "name": "Micro E-mini S&P 500",
            "tick_size": 0.25,
            "tick_value": 1.25,
            "point_value": 5.0,
        }

        with (
            patch(
                "builtins.input",
                side_effect=["1", "", "", "", "", ""],
            ),
            patch.object(
                menu,
                "prompt_choice",
                side_effect=["long", "futures"],
            ),
            patch.object(
                menu,
                "prompt_positive_integer",
                return_value=1,
            ),
            patch.object(
                menu,
                "get_known_futures_profile",
                return_value=profile,
            ),
            patch.object(
                menu,
                "print_futures_instrument_profile",
            ),
            patch.object(
                menu,
                "prompt_futures_price",
                side_effect=[5000.0, 5010.0],
            ),
            patch.object(
                menu,
                "prompt_finite_number",
                side_effect=[25.0, 2.0],
            ),
            patch.object(
                menu,
                "prompt_date",
                return_value="2026-07-27",
            ),
            patch.object(
                menu,
                "prompt_time",
                side_effect=["09:30", "09:45"],
            ),
            patch.object(menu, "calculate_duration", return_value=15),
            patch.object(
                menu,
                "validate_and_normalize_trade",
                return_value=(normalized_trade, validation_errors),
            ) as validate_mock,
            patch.object(
                menu,
                "save_trades",
                return_value=save_result,
            ) as save_mock,
        ):
            _, output = capture_output(
                menu.handle_edit_trade,
                trades,
                {"account_currency": "USD"},
            )

        return current, trades, output, validate_mock, save_mock

    def test_successful_futures_edit_replaces_and_saves_trade(self):
        updated = make_trade(notes="Updated")

        current, trades, output, validate_mock, save_mock = (
            self.run_existing_futures_edit(
                normalized_trade=updated,
            )
        )

        self.assertIsNot(trades[0], current)
        self.assertEqual(trades, [updated])
        self.assertIn("Trade updated successfully", output)
        validate_mock.assert_called_once()
        save_mock.assert_called_once_with(trades)

    def test_failed_edit_save_restores_original_trade(self):
        updated = make_trade(notes="Updated")

        current, trades, output, _, _ = self.run_existing_futures_edit(
            normalized_trade=updated,
            save_result=False,
        )

        self.assertIs(trades[0], current)
        self.assertIn("changes were not applied", output)

    def test_edit_validation_errors_leave_original_trade_unchanged(self):
        current, trades, output, _, save_mock = (
            self.run_existing_futures_edit(
                normalized_trade=None,
                validation_errors=["Invalid edited trade."],
            )
        )

        self.assertIs(trades[0], current)
        self.assertIn("Trade was not updated", output)
        self.assertIn("Invalid edited trade", output)
        save_mock.assert_not_called()

    def test_inconsistent_builtin_futures_profile_blocks_edit(self):
        current = make_trade(point_value=5.0)
        trades = [current]
        inconsistent_profile = {
            "root": "MES",
            "name": "Changed contract",
            "tick_size": 0.25,
            "tick_value": 5.0,
            "point_value": 20.0,
        }

        with (
            patch("builtins.input", side_effect=["1", ""]),
            patch.object(
                menu,
                "prompt_choice",
                side_effect=["long", "futures"],
            ),
            patch.object(
                menu,
                "prompt_positive_integer",
                return_value=1,
            ),
            patch.object(
                menu,
                "get_known_futures_profile",
                return_value=inconsistent_profile,
            ),
            patch.object(menu, "save_trades") as save_mock,
        ):
            _, output = capture_output(
                menu.handle_edit_trade,
                trades,
                None,
            )

        self.assertIs(trades[0], current)
        self.assertIn("inconsistent", output)
        self.assertIn("edit was not applied", output)
        save_mock.assert_not_called()


class DeleteTradeTests(unittest.TestCase):
    def test_empty_trade_list_prints_message(self):
        _, output = capture_output(menu.handle_delete_trade, [])
        self.assertIn("No trades to delete", output)

    def test_non_numeric_trade_number_is_rejected(self):
        with patch("builtins.input", return_value="abc"):
            _, output = capture_output(
                menu.handle_delete_trade,
                [make_trade()],
            )
        self.assertIn("Invalid trade number", output)

    def test_out_of_range_trade_number_is_rejected(self):
        with patch("builtins.input", return_value="9"):
            _, output = capture_output(
                menu.handle_delete_trade,
                [make_trade()],
            )
        self.assertIn("Invalid trade number", output)

    def test_no_confirmation_cancels_delete(self):
        trades = [make_trade()]

        with patch("builtins.input", side_effect=["1", "no"]):
            _, output = capture_output(
                menu.handle_delete_trade,
                trades,
            )

        self.assertEqual(len(trades), 1)
        self.assertIn("Delete cancelled", output)

    def test_confirmed_delete_saves_change(self):
        trades = [make_trade(symbol="MES"), make_trade(symbol="MNQ")]

        with (
            patch("builtins.input", side_effect=["1", "yes"]),
            patch.object(menu, "save_trades", return_value=True) as save_mock,
        ):
            _, output = capture_output(
                menu.handle_delete_trade,
                trades,
            )

        self.assertEqual([trade["symbol"] for trade in trades], ["MNQ"])
        self.assertIn("Deleted trade MES", output)
        save_mock.assert_called_once_with(trades)

    def test_failed_save_restores_deleted_trade_at_original_index(self):
        first = make_trade(symbol="MES")
        second = make_trade(symbol="MNQ")
        trades = [first, second]

        with (
            patch("builtins.input", side_effect=["1", "yes"]),
            patch.object(menu, "save_trades", return_value=False),
        ):
            _, output = capture_output(
                menu.handle_delete_trade,
                trades,
            )

        self.assertEqual(trades, [first, second])
        self.assertIn("was not deleted", output)

    def test_delete_confirmation_uses_legacy_net_result_fallback(self):
        trade = make_trade()
        trade.pop("net_result")
        prompts = iter(["1", "no"])
        seen_prompts = []

        def fake_input(prompt_text):
            seen_prompts.append(prompt_text)
            return next(prompts)

        with (
            patch("builtins.input", side_effect=fake_input),
            patch.object(menu, "calculate_net_result", return_value="Win") as result_mock,
        ):
            capture_output(menu.handle_delete_trade, [trade])

        self.assertIn("Win", seen_prompts[-1])
        result_mock.assert_called_once_with(48.0)


class StatisticsTests(unittest.TestCase):
    def test_trading_statistics_rejects_empty_list(self):
        _, output = capture_output(
            menu.handle_trading_statistics,
            [],
        )
        self.assertIn("No trades to calculate statistics", output)

    def test_trading_statistics_prints_core_sections(self):
        trades = [
            make_trade(),
            make_trade(
                symbol="MNQ",
                dollar_pnl=-25.0,
                commission=2.0,
                net_dollar_pnl=-27.0,
                result="Loss",
                net_result="Loss",
                realized_r=-1.0,
                entry_time="10:00",
                duration=30,
            ),
            make_trade(
                symbol="MGC",
                dollar_pnl=0.0,
                commission=0.0,
                net_dollar_pnl=0.0,
                result="Break-even",
                net_result="Break-even",
                risk_amount=0.0,
                realized_r=0.0,
                entry_time="11:00",
                duration=None,
            ),
        ]

        with (
            patch.object(menu, "compute_unit_performance_stats", return_value={}),
            patch.object(menu, "print_unit_performance_stats"),
        ):
            _, output = capture_output(
                menu.handle_trading_statistics,
                trades,
            )

        self.assertIn("PERFORMANCE STATISTICS", output)
        self.assertIn("Total Trades:", output)
        self.assertIn("Win Rate:", output)
        self.assertIn("COMMISSION & NET PERFORMANCE", output)
        self.assertIn("RISK ANALYTICS", output)
        self.assertIn("TRADE DURATION", output)
        self.assertIn("STREAK ANALYTICS", output)

    def test_statistics_handles_no_losing_or_timed_trades(self):
        trade = make_trade(
            entry_time=None,
            duration=None,
            risk_amount=0.0,
            realized_r=0.0,
        )

        with (
            patch.object(menu, "compute_unit_performance_stats", return_value={}),
            patch.object(menu, "print_unit_performance_stats"),
        ):
            _, output = capture_output(
                menu.handle_trading_statistics,
                [trade],
            )

        self.assertIn("N/A (no losing trades)", output)
        self.assertIn("Longest trade duration:", output)
        self.assertIn("Earliest entry time:", output)


class SearchTradeTests(unittest.TestCase):
    def test_empty_trade_list_prints_message(self):
        _, output = capture_output(menu.handle_search_trades, [])
        self.assertIn("No trades to search", output)

    def test_end_date_before_start_date_is_rejected(self):
        answers = ["", "", "", "", "", "", "", ""]

        with (
            patch("builtins.input", side_effect=answers),
            patch.object(
                menu,
                "get_optional_date",
                side_effect=[date(2026, 7, 28), date(2026, 7, 27)],
            ),
        ):
            _, output = capture_output(
                menu.handle_search_trades,
                [make_trade()],
            )

        self.assertIn("End date cannot be earlier", output)

    def test_invalid_market_filter_retries_then_matches(self):
        answers = ["", "", "stocks", "futures", "", "", "", "", ""]

        with (
            patch("builtins.input", side_effect=answers),
            patch.object(menu, "get_optional_date", side_effect=[None, None]),
        ):
            _, output = capture_output(
                menu.handle_search_trades,
                [make_trade()],
            )

        self.assertIn("Market type must be futures or forex", output)
        self.assertIn("1 trade(s) found", output)

    def test_matching_filters_print_trade_details(self):
        answers = [
            "mes",
            "long",
            "futures",
            "win",
            "win",
            "fvg",
            "ict",
            "new york/london overlap",
        ]

        with (
            patch("builtins.input", side_effect=answers),
            patch.object(menu, "get_optional_date", side_effect=[None, None]),
            patch.object(menu, "print_trade_unit_detail") as detail_mock,
        ):
            _, output = capture_output(
                menu.handle_search_trades,
                [make_trade()],
            )

        self.assertIn("Trade #1", output)
        self.assertIn("1 trade(s) found", output)
        detail_mock.assert_called_once()

    def test_nonmatching_filters_print_no_matches(self):
        answers = ["MNQ", "", "", "", "", "", "", ""]

        with (
            patch("builtins.input", side_effect=answers),
            patch.object(menu, "get_optional_date", side_effect=[None, None]),
        ):
            _, output = capture_output(
                menu.handle_search_trades,
                [make_trade()],
            )

        self.assertIn("No matching trades found", output)


class FilteredStatisticsTests(unittest.TestCase):
    def test_empty_trade_list_prints_message(self):
        _, output = capture_output(
            menu.handle_filtered_statistics,
            [],
        )
        self.assertIn("No trades to calculate filtered statistics", output)

    def test_end_date_before_start_date_is_rejected(self):
        answers = ["", "", "", "", "", "", ""]

        with (
            patch("builtins.input", side_effect=answers),
            patch.object(
                menu,
                "get_optional_date",
                side_effect=[date(2026, 7, 28), date(2026, 7, 27)],
            ),
        ):
            _, output = capture_output(
                menu.handle_filtered_statistics,
                [make_trade()],
            )

        self.assertIn("End date cannot be earlier", output)

    def test_invalid_market_filter_retries(self):
        answers = ["", "", "stocks", "forex", "", "", "", ""]

        with (
            patch("builtins.input", side_effect=answers),
            patch.object(menu, "get_optional_date", side_effect=[None, None]),
        ):
            _, output = capture_output(
                menu.handle_filtered_statistics,
                [make_trade()],
            )

        self.assertIn("Market type must be futures or forex", output)
        self.assertIn("No trades matched those filters", output)

    def test_no_matching_trades_prints_message(self):
        answers = ["MNQ", "", "", "", "", "", ""]

        with (
            patch("builtins.input", side_effect=answers),
            patch.object(menu, "get_optional_date", side_effect=[None, None]),
        ):
            _, output = capture_output(
                menu.handle_filtered_statistics,
                [make_trade()],
            )

        self.assertIn("No trades matched those filters", output)

    def test_matching_trade_prints_filtered_statistics(self):
        answers = ["MES", "long", "futures", "win", "win", "FVG", "new york/london overlap"]

        with (
            patch("builtins.input", side_effect=answers),
            patch.object(menu, "get_optional_date", side_effect=[None, None]),
            patch.object(menu, "compute_unit_performance_stats", return_value={}) as unit_mock,
            patch.object(menu, "print_unit_performance_stats"),
        ):
            _, output = capture_output(
                menu.handle_filtered_statistics,
                [make_trade()],
            )

        self.assertIn("PERFORMANCE STATISTICS", output)
        self.assertIn("Total Trades:", output)
        self.assertIn("STREAK ANALYTICS", output)
        unit_mock.assert_called_once()
        self.assertEqual(unit_mock.call_args.args[0][0][0], 0)


class WrapperHandlerTests(unittest.TestCase):
    def test_session_analytics_delegates_to_display(self):
        trades = [make_trade()]
        with patch.object(menu, "display_session_analytics") as mock:
            menu.handle_session_analytics(trades)
        mock.assert_called_once_with(trades)

    def test_setup_and_strategy_analytics_delegates_to_both_displays(self):
        trades = [make_trade()]
        with (
            patch.object(menu, "display_setup_analytics") as setup_mock,
            patch.object(menu, "display_strategy_method_analytics") as strategy_mock,
        ):
            menu.handle_setup_and_strategy_analytics(trades)

        setup_mock.assert_called_once_with(trades)
        strategy_mock.assert_called_once_with(trades)

    def test_time_analytics_delegates_to_display(self):
        trades = [make_trade()]
        with patch.object(menu, "display_time_based_analytics") as mock:
            menu.handle_time_based_analytics(trades)
        mock.assert_called_once_with(trades)

    def test_equity_history_delegates_with_account(self):
        trades = [make_trade()]
        account = {"starting_balance": 1000.0}
        with patch.object(menu, "display_equity_drawdown_history") as mock:
            menu.handle_equity_drawdown_history(trades, account)
        mock.assert_called_once_with(trades, account)

    def test_manual_save_success_message(self):
        trades = [make_trade()]
        with patch.object(menu, "save_trades", return_value=True):
            _, output = capture_output(menu.handle_save_trades, trades)
        self.assertIn("Trades saved", output)
        self.assertIn("automatically", output)

    def test_manual_save_failure_message(self):
        with patch.object(menu, "save_trades", return_value=False):
            _, output = capture_output(menu.handle_save_trades, [])
        self.assertIn("could not be saved", output)

    def test_export_csv_delegates_to_storage(self):
        trades = [make_trade()]
        with patch.object(menu, "export_trades_to_csv") as mock:
            menu.handle_export_csv(trades)
        mock.assert_called_once_with(trades)

    def test_quit_prints_goodbye(self):
        _, output = capture_output(menu.handle_quit)
        self.assertEqual(output.strip(), "Goodbye.")


class RunMenuTests(unittest.TestCase):
    def test_run_menu_dispatches_all_sixteen_options(self):
        trades = [make_trade()]
        original_account = {"name": "Original"}
        created_account = {"name": "Created"}
        edited_account = {"name": "Edited"}

        with (
            patch("builtins.input", side_effect=[str(i) for i in range(1, 17)]),
            patch.object(menu, "show_menu") as show_mock,
            patch.object(menu, "handle_account_status", return_value=created_account) as status_mock,
            patch.object(menu, "handle_edit_account", return_value=edited_account) as edit_account_mock,
            patch.object(menu, "handle_add_trade") as add_mock,
            patch.object(menu, "handle_view_trades") as view_mock,
            patch.object(menu, "handle_edit_trade") as edit_trade_mock,
            patch.object(menu, "handle_delete_trade") as delete_mock,
            patch.object(menu, "handle_trading_statistics") as stats_mock,
            patch.object(menu, "handle_search_trades") as search_mock,
            patch.object(menu, "handle_filtered_statistics") as filtered_mock,
            patch.object(menu, "handle_session_analytics") as session_mock,
            patch.object(menu, "handle_setup_and_strategy_analytics") as setup_mock,
            patch.object(menu, "handle_time_based_analytics") as time_mock,
            patch.object(menu, "handle_equity_drawdown_history") as equity_mock,
            patch.object(menu, "handle_save_trades") as save_mock,
            patch.object(menu, "handle_export_csv") as export_mock,
            patch.object(menu, "handle_quit") as quit_mock,
        ):
            menu.run_menu(trades, original_account)

        self.assertEqual(show_mock.call_count, 16)
        status_mock.assert_called_once_with(trades, original_account)
        edit_account_mock.assert_called_once_with(created_account, trades)
        add_mock.assert_called_once_with(trades, edited_account)
        view_mock.assert_called_once_with(trades)
        edit_trade_mock.assert_called_once_with(trades, edited_account)
        delete_mock.assert_called_once_with(trades)
        stats_mock.assert_called_once_with(trades)
        search_mock.assert_called_once_with(trades)
        filtered_mock.assert_called_once_with(trades)
        session_mock.assert_called_once_with(trades)
        setup_mock.assert_called_once_with(trades)
        time_mock.assert_called_once_with(trades)
        equity_mock.assert_called_once_with(trades, edited_account)
        save_mock.assert_called_once_with(trades)
        export_mock.assert_called_once_with(trades)
        quit_mock.assert_called_once_with()

    def test_invalid_choice_prints_error_then_continues(self):
        with (
            patch("builtins.input", side_effect=["99", "16"]),
            patch.object(menu, "show_menu"),
            patch.object(menu, "handle_quit") as quit_mock,
        ):
            _, output = capture_output(
                menu.run_menu,
                [],
                None,
            )

        self.assertIn("Invalid choice", output)
        quit_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()