import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import journal.menu as menu
import journal.storage as storage


def capture_output(function, *args, **kwargs):
    stream = io.StringIO()
    with redirect_stdout(stream):
        result = function(*args, **kwargs)
    return result, stream.getvalue()


def futures_answers(**overrides):
    values = {
        "market_type": "futures",
        "symbol": "MES",
        "direction": "long",
        "contracts": "2",
        "entry": "7500.25",
        "exit": "7510.50",
        "risk": "100",
        "commission": "4",
        "trade_date": "2026-07-30",
        "entry_time": "09:30",
        "exit_time": "10:00",
        "strategy": "ICT",
        "setup": "FVG",
        "notes": "Patient entry",
        "mistake": "",
    }
    values.update(overrides)
    return [
        values["market_type"],
        values["symbol"],
        values["direction"],
        values["contracts"],
        values["entry"],
        values["exit"],
        values["risk"],
        values["commission"],
        values["trade_date"],
        values["entry_time"],
        values["exit_time"],
        values["strategy"],
        values["setup"],
        values["notes"],
        values["mistake"],
    ]


def forex_answers(*, include_account_currency=False, **overrides):
    values = {
        "market_type": "forex",
        "symbol": "EURUSD",
        "direction": "long",
        "account_currency": "USD",
        "lot_size": "1",
        "entry": "1.10000",
        "exit": "1.10150",
        "risk": "100",
        "commission": "2",
        "trade_date": "2026-07-30",
        "entry_time": "09:30",
        "exit_time": "10:00",
        "strategy": "Order Flow",
        "setup": "OB",
        "notes": "Forex trade",
        "mistake": "",
    }
    values.update(overrides)

    answers = [
        values["market_type"],
        values["symbol"],
        values["direction"],
    ]

    if include_account_currency:
        answers.append(values["account_currency"])

    answers.extend(
        [
            values["lot_size"],
            values["entry"],
            values["exit"],
            values["risk"],
            values["commission"],
            values["trade_date"],
            values["entry_time"],
            values["exit_time"],
            values["strategy"],
            values["setup"],
            values["notes"],
            values["mistake"],
        ]
    )
    return answers


class MenuWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.data_directory = Path(self.temporary_directory.name)
        self.trades_file = self.data_directory / "trades.json"
        self.account_file = self.data_directory / "account.json"

        patches = [
            patch.object(
                storage,
                "data_dir",
                str(self.data_directory),
            ),
            patch.object(
                storage,
                "TRADES_FILE",
                str(self.trades_file),
            ),
            patch.object(
                storage,
                "ACCOUNT_FILE",
                str(self.account_file),
            ),
        ]

        for active_patch in patches:
            active_patch.start()
            self.addCleanup(active_patch.stop)

    def add_futures_trade(self, trades, account=None, **overrides):
        if account is None:
            account = {"account_currency": "USD"}

        with patch(
            "builtins.input",
            side_effect=futures_answers(**overrides),
        ):
            _, output = capture_output(
                menu.handle_add_trade,
                trades,
                account,
            )

        return output

    def add_forex_trade(
        self,
        trades,
        account,
        *,
        include_account_currency=False,
        **overrides,
    ):
        with patch(
            "builtins.input",
            side_effect=forex_answers(
                include_account_currency=include_account_currency,
                **overrides,
            ),
        ):
            _, output = capture_output(
                menu.handle_add_trade,
                trades,
                account,
            )

        return output

    def test_account_creation_persists_and_reloads(self):
        with patch(
            "builtins.input",
            side_effect=["Integration Account", "3", "25000"],
        ):
            account, output = capture_output(
                menu.handle_account_status,
                [],
                None,
            )

        reloaded = storage.load_account()

        self.assertEqual(account["name"], "Integration Account")
        self.assertEqual(account["type"], "Funded")
        self.assertEqual(account["starting_balance"], 25000.0)
        self.assertEqual(reloaded["name"], "Integration Account")
        self.assertEqual(reloaded["account_currency"], None)
        self.assertIn("created successfully", output)
        self.assertIn("ACCOUNT STATUS", output)

    def test_account_edit_persists_currency_and_name(self):
        account = {
            "name": "Original",
            "type": "Personal",
            "starting_balance": 10000.0,
            "high_water_mark": 10000.0,
            "account_currency": "USD",
        }
        self.assertTrue(storage.save_account(account))

        with patch(
            "builtins.input",
            side_effect=["Updated Account", "3", "12000", "CAD"],
        ):
            updated, output = capture_output(
                menu.handle_edit_account,
                account,
                [],
            )

        reloaded = storage.load_account()

        self.assertEqual(updated["name"], "Updated Account")
        self.assertEqual(updated["type"], "Funded")
        self.assertEqual(updated["starting_balance"], 12000.0)
        self.assertEqual(updated["account_currency"], "CAD")
        self.assertEqual(reloaded, updated)
        self.assertIn("updated successfully", output)

    def test_futures_add_workflow_saves_normalized_trade(self):
        trades = []

        output = self.add_futures_trade(trades)
        reloaded = storage.load_trades()

        self.assertEqual(len(trades), 1)
        self.assertEqual(reloaded, trades)
        self.assertEqual(reloaded[0]["symbol"], "mes")
        self.assertEqual(reloaded[0]["market_type"], "futures")
        self.assertEqual(reloaded[0]["ticks_pnl"], 41.0)
        self.assertEqual(reloaded[0]["dollar_pnl"], 102.5)
        self.assertEqual(reloaded[0]["net_dollar_pnl"], 98.5)
        self.assertEqual(
            reloaded[0]["session"],
            "New York/London Overlap",
        )
        self.assertIn("Trade added successfully", output)

    def test_forex_add_workflow_saves_normalized_trade(self):
        trades = []
        account = {
            "name": "Forex Account",
            "type": "Personal",
            "starting_balance": 10000.0,
            "high_water_mark": 10000.0,
            "account_currency": "USD",
        }

        output = self.add_forex_trade(trades, account)
        reloaded = storage.load_trades()

        self.assertEqual(reloaded, trades)
        self.assertEqual(reloaded[0]["symbol"], "eur/usd")
        self.assertEqual(reloaded[0]["market_type"], "forex")
        self.assertEqual(reloaded[0]["pip_size"], 0.0001)
        self.assertEqual(reloaded[0]["price_precision"], 5)
        self.assertEqual(reloaded[0]["pips_pnl"], 15.0)
        self.assertAlmostEqual(reloaded[0]["dollar_pnl"], 150.0)
        self.assertAlmostEqual(reloaded[0]["net_dollar_pnl"], 148.0)
        self.assertIn("Standard pair detected", output)
        self.assertIn("Trade added successfully", output)

    def test_forex_add_sets_and_persists_missing_account_currency(self):
        trades = []
        account = {
            "name": "No Currency",
            "type": "Personal",
            "starting_balance": 10000.0,
            "high_water_mark": 10000.0,
        }

        output = self.add_forex_trade(
            trades,
            account,
            include_account_currency=True,
        )
        reloaded_account = storage.load_account()

        self.assertEqual(account["account_currency"], "USD")
        self.assertEqual(reloaded_account["account_currency"], "USD")
        self.assertEqual(len(storage.load_trades()), 1)
        self.assertIn("account currency is required", output)

    def test_saved_trade_can_be_reloaded_and_viewed(self):
        trades = []
        self.add_futures_trade(trades)
        reloaded = storage.load_trades()

        with patch("builtins.input", return_value="1"):
            _, output = capture_output(
                menu.handle_view_trades,
                reloaded,
            )

        self.assertIn("Trades (1 total)", output)
        self.assertIn("Trade #1", output)
        self.assertIn("Symbol: mes", output)
        self.assertIn("Gross Dollar P/L: $102.50", output)
        self.assertIn("Net Dollar P/L: $98.50", output)
        self.assertIn("Fair Value Gap (FVG)", output)

    def test_futures_edit_recalculates_and_persists(self):
        trades = []
        self.add_futures_trade(trades)
        reloaded = storage.load_trades()

        edit_answers = [
            "1",
            "",
            "",
            "",
            "",
            "",
            "7495.25",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Edited outcome",
            "",
        ]

        with patch("builtins.input", side_effect=edit_answers):
            _, output = capture_output(
                menu.handle_edit_trade,
                reloaded,
                {"account_currency": "USD"},
            )

        edited = storage.load_trades()[0]

        self.assertEqual(edited["exit"], 7495.25)
        self.assertEqual(edited["result"], "Loss")
        self.assertEqual(edited["net_result"], "Loss")
        self.assertEqual(edited["points_pnl"], -5.0)
        self.assertEqual(edited["ticks_pnl"], -20.0)
        self.assertEqual(edited["dollar_pnl"], -50.0)
        self.assertEqual(edited["net_dollar_pnl"], -54.0)
        self.assertEqual(edited["notes"], "Edited outcome")
        self.assertIn("Trade updated successfully", output)

    def test_delete_workflow_removes_trade_from_disk(self):
        trades = []
        self.add_futures_trade(trades)
        reloaded = storage.load_trades()

        with patch("builtins.input", side_effect=["1", "yes"]):
            _, output = capture_output(
                menu.handle_delete_trade,
                reloaded,
            )

        self.assertEqual(reloaded, [])
        self.assertEqual(storage.load_trades(), [])
        self.assertIn("Deleted trade mes", output)

    def test_account_status_uses_saved_trade_and_persists_high_water_mark(self):
        account = {
            "name": "Funded",
            "type": "Funded",
            "starting_balance": 25000.0,
            "high_water_mark": 25000.0,
            "account_currency": "USD",
        }
        self.assertTrue(storage.save_account(account))

        trades = []
        self.add_futures_trade(trades, account)
        loaded_trades = storage.load_trades()
        loaded_account = storage.load_account()

        updated, output = capture_output(
            menu.handle_account_status,
            loaded_trades,
            loaded_account,
        )
        reloaded_account = storage.load_account()

        self.assertEqual(updated["high_water_mark"], 25098.5)
        self.assertEqual(reloaded_account["high_water_mark"], 25098.5)
        self.assertIn("Current Balance: $25,098.50", output)
        self.assertIn("Net Profit: $98.50", output)
        self.assertIn("Current Drawdown: $0.00", output)

    def test_editing_a_winner_into_a_loser_fully_rebuilds_high_water_mark(self):
        # Sprint 29 regression: two trades, both originally winners (each
        # sets a new peak). The second (later-dated) trade is then edited
        # into a loss through the real handle_edit_trade -> save_trades ->
        # storage round trip. Because nothing follows it chronologically,
        # the account must show a genuine, non-zero drawdown afterward --
        # not the stale/incorrect "high water mark == current balance,
        # $0.00 drawdown" that prompted this investigation.
        account = {
            "name": "Funded",
            "type": "Funded",
            "starting_balance": 25000.0,
            "high_water_mark": 25000.0,
            "account_currency": "USD",
        }
        self.assertTrue(storage.save_account(account))

        trades = []
        self.add_futures_trade(trades, account)  # trade 1: 2026-07-30, net +98.50
        self.add_futures_trade(
            trades, account, trade_date="2026-07-31"
        )  # trade 2: net +98.50 (about to be edited into a loss)

        reloaded_trades = storage.load_trades()
        self.assertEqual(len(reloaded_trades), 2)

        edit_answers = [
            "2",         # trade number
            "",          # symbol keep
            "",          # direction keep
            "",          # market_type keep
            "",          # contracts keep
            "",          # entry keep
            "7495.25",   # exit -- turns trade 2 into a loss
            "",          # risk keep
            "",          # commission keep
            "",          # trade_date keep
            "",          # entry_time keep
            "",          # exit_time keep
            "",          # strategy keep
            "",          # setup keep
            "",          # notes keep
            "",          # mistake keep
        ]

        with patch("builtins.input", side_effect=edit_answers):
            capture_output(
                menu.handle_edit_trade,
                reloaded_trades,
                account,
            )

        edited_trades = storage.load_trades()
        self.assertEqual(edited_trades[1]["net_dollar_pnl"], -54.0)

        reloaded_account = storage.load_account()
        updated, output = capture_output(
            menu.handle_account_status,
            edited_trades,
            reloaded_account,
        )

        # Peak was 25,098.50 after trade 1; trade 2 (now -$54.00) brings
        # the balance to 25,044.50 -- a real $54.00 drawdown, not $0.00.
        self.assertEqual(updated["high_water_mark"], 25098.5)
        self.assertIn("Current Balance: $25,044.50", output)
        self.assertIn("High Water Mark: $25,098.50", output)
        self.assertIn("Current Drawdown: -$54.00", output)
        self.assertNotIn("Current Drawdown: $0.00", output)

        reloaded_account_after = storage.load_account()
        self.assertEqual(
            reloaded_account_after["high_water_mark"], 25098.5
        )

    def test_saved_mixed_trades_feed_statistics_and_analytics_displays(self):
        trades = []
        account = {
            "name": "Mixed",
            "type": "Personal",
            "starting_balance": 10000.0,
            "high_water_mark": 10000.0,
            "account_currency": "USD",
        }
        self.add_futures_trade(trades, account)
        self.add_forex_trade(
            trades,
            account,
            trade_date="2026-07-31",
            entry_time="13:00",
            exit_time="13:20",
        )
        reloaded = storage.load_trades()

        _, statistics_output = capture_output(
            menu.handle_trading_statistics,
            reloaded,
        )
        _, session_output = capture_output(
            menu.handle_session_analytics,
            reloaded,
        )
        _, setup_output = capture_output(
            menu.handle_setup_and_strategy_analytics,
            reloaded,
        )
        _, time_output = capture_output(
            menu.handle_time_based_analytics,
            reloaded,
        )

        self.assertIn("PERFORMANCE STATISTICS", statistics_output)
        self.assertIn("Total Trades:", statistics_output)
        self.assertIn("2", statistics_output)
        self.assertIn("SESSION ANALYTICS", session_output)
        self.assertIn("New York/London Overlap", session_output)
        self.assertIn("New York", session_output)
        self.assertIn("SETUP COMPONENT ANALYTICS", setup_output)
        self.assertIn("Fair Value Gap (FVG)", setup_output)
        self.assertIn("Order Block", setup_output)
        self.assertIn("TIME-BASED COMPARISONS", time_output)
        self.assertIn("Thursday", time_output)
        self.assertIn("Friday", time_output)

    def test_export_handler_writes_csv_from_saved_trade(self):
        trades = []
        self.add_futures_trade(trades)
        reloaded = storage.load_trades()

        _, output = capture_output(
            menu.handle_export_csv,
            reloaded,
        )

        exports = list(
            self.data_directory.glob("trades_export_*.csv")
        )
        self.assertEqual(len(exports), 1)

        with open(
            exports[0],
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Symbol"], "MES")
        self.assertEqual(rows[0]["Market Type"], "futures")
        self.assertEqual(rows[0]["Net Dollar P/L"], "98.5")
        self.assertIn("exported", output.lower())

    def test_real_prompt_validation_retries_then_saves_trade(self):
        trades = []
        answers = [
            "stocks",
            "futures",
            "",
            "MES",
            "up",
            "long",
            "0",
            "2",
            "7500.30",
            "7500.25",
            "7510.50",
            "-1",
            "100",
            "-1",
            "4",
            "invalid",
            "2026-07-30",
            "25:00",
            "09:30",
            "10:00",
            "ICT",
            "FVG",
            "Validated entry",
            "",
        ]

        with patch("builtins.input", side_effect=answers):
            _, output = capture_output(
                menu.handle_add_trade,
                trades,
                {"account_currency": "USD"},
            )

        self.assertEqual(len(storage.load_trades()), 1)
        self.assertIn("Market type must be futures or forex", output)
        self.assertIn("Symbol cannot be blank", output)
        self.assertIn("Direction must be long or short", output)
        self.assertIn(
            "Contracts must be a whole number greater than 0",
            output,
        )
        self.assertIn("must align with a tick size", output)
        self.assertIn("Trade added successfully", output)

    def test_run_menu_completes_add_view_statistics_save_and_quit(self):
        trades = []
        account = {
            "name": "Menu Account",
            "type": "Personal",
            "starting_balance": 10000.0,
            "high_water_mark": 10000.0,
            "account_currency": "USD",
        }
        answers = [
            "3",
            *futures_answers(),
            "4",
            "",
            "7",
            "14",
            "16",
        ]

        with patch("builtins.input", side_effect=answers):
            _, output = capture_output(
                menu.run_menu,
                trades,
                account,
            )

        reloaded = storage.load_trades()

        self.assertEqual(len(reloaded), 1)
        self.assertIn("Trade added successfully", output)
        self.assertIn("Trades (1 total)", output)
        self.assertIn("PERFORMANCE STATISTICS", output)
        self.assertIn("Trades saved", output)
        self.assertIn("Goodbye", output)


if __name__ == "__main__":
    unittest.main()
    