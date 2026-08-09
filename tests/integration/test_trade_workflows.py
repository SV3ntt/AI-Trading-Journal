import csv
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import journal.storage as storage
from journal.analytics import (
    calculate_equity_drawdown_history,
    calculate_session_analysis,
    calculate_setup_analysis,
    calculate_strategy_method_analysis,
    calculate_streaks,
    calculate_time_based_analytics,
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
        "notes": "Patient entry",
        "mistake": "",
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
        "strategy_method": "Order Flow",
        "setup": "OB",
        "notes": "Forex trade",
        "mistake": "",
        "account_currency": "USD",
    }
    trade.update(overrides)
    return trade


def normalize_trade(trade):
    normalized, errors = validate_and_normalize_trade(trade)
    if errors:
        raise AssertionError(
            f"Sample trade did not validate: {errors}"
        )
    return normalized


class TradeWorkflowIntegrationTests(unittest.TestCase):
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

    def write_json(self, path, data):
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def read_json(self, path):
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def test_futures_trade_validates_saves_and_reloads(self):
        trade = normalize_trade(make_futures_trade())

        self.assertTrue(storage.save_trades([trade]))
        loaded = storage.load_trades()

        self.assertEqual(loaded, [trade])
        self.assertEqual(loaded[0]["symbol"], "mes")
        self.assertEqual(loaded[0]["ticks_pnl"], 41.0)
        self.assertEqual(loaded[0]["dollar_pnl"], 102.5)
        self.assertEqual(loaded[0]["net_dollar_pnl"], 98.5)
        self.assertEqual(loaded[0]["session"], "New York/London Overlap")

    def test_forex_trade_validates_saves_and_reloads(self):
        trade = normalize_trade(make_forex_trade())

        self.assertTrue(storage.save_trades([trade]))
        loaded = storage.load_trades()

        self.assertEqual(loaded, [trade])
        self.assertEqual(loaded[0]["symbol"], "eur/usd")
        self.assertEqual(loaded[0]["pip_size"], 0.0001)
        self.assertEqual(loaded[0]["price_precision"], 5)
        self.assertEqual(loaded[0]["pips_pnl"], 15.0)
        self.assertAlmostEqual(loaded[0]["dollar_pnl"], 150.0)
        self.assertAlmostEqual(loaded[0]["net_dollar_pnl"], 148.0)

    def test_mixed_saved_trades_feed_all_analytics(self):
        futures_win = normalize_trade(make_futures_trade())
        futures_loss = normalize_trade(
            make_futures_trade(
                direction="short",
                entry=7510.25,
                exit=7520.25,
                contracts=1,
                commission=2.0,
                trade_date="2026-07-31",
                strategy_method="Order Flow",
                setup="OB",
            )
        )
        forex_win = normalize_trade(
            make_forex_trade(
                trade_date="2026-08-03",
                entry_time="13:00",
                exit_time="13:20",
            )
        )

        self.assertTrue(
            storage.save_trades(
                [futures_win, futures_loss, forex_win]
            )
        )
        loaded = storage.load_trades()

        sessions = calculate_session_analysis(loaded)
        setups, setup_combinations = calculate_setup_analysis(loaded)
        strategies, strategy_combinations = (
            calculate_strategy_method_analysis(loaded)
        )
        weekdays, hours, durations = calculate_time_based_analytics(loaded)
        streaks = calculate_streaks(loaded)

        self.assertEqual(len(loaded), 3)
        self.assertEqual(
            sessions["New York/London Overlap"]["total_trades"],
            2,
        )
        self.assertEqual(sessions["New York"]["total_trades"], 1)
        self.assertEqual(setups["Fair Value Gap (FVG)"]["total_trades"], 1)
        self.assertEqual(setups["Order Block"]["total_trades"], 2)
        self.assertEqual(setup_combinations, {})
        self.assertEqual(strategies["ICT"]["wins"], 1)
        self.assertEqual(strategies["Order Flow"]["total_trades"], 2)
        self.assertEqual(strategy_combinations, {})
        self.assertEqual(weekdays["Thursday"]["total_trades"], 1)
        self.assertEqual(hours["09:00 - 09:59"]["total_trades"], 2)
        self.assertEqual(durations["16 - 30 minutes"]["total_trades"], 3)
        self.assertEqual(streaks["current_type"], "Win")
        self.assertEqual(streaks["current_length"], 1)

    def test_account_and_trades_reload_into_equity_history(self):
        account, errors = validate_and_normalize_account(
            {
                "name": "Main Account",
                "type": "Funded",
                "starting_balance": 25000,
                "high_water_mark": 25000,
                "account_currency": "USD",
            }
        )
        self.assertEqual(errors, [])

        win = normalize_trade(make_futures_trade())
        loss = normalize_trade(
            make_futures_trade(
                direction="short",
                entry=7510.25,
                exit=7520.25,
                contracts=1,
                commission=2.0,
                trade_date="2026-07-31",
            )
        )

        self.assertTrue(storage.save_account(account))
        self.assertTrue(storage.save_trades([win, loss]))

        loaded_account = storage.load_account()
        loaded_trades = storage.load_trades()
        result = calculate_equity_drawdown_history(
            loaded_trades,
            loaded_account["starting_balance"],
        )

        self.assertEqual(loaded_account, account)
        self.assertAlmostEqual(result["ending_balance"], 25046.5)
        self.assertAlmostEqual(result["net_change"], 46.5)
        self.assertAlmostEqual(result["high_water_mark"], 25098.5)
        self.assertAlmostEqual(result["maximum_drawdown"], 52.0)
        self.assertEqual(result["maximum_drawdown_peak"], "Trade #1")
        self.assertEqual(result["maximum_drawdown_trough"], "Trade 2")

    def test_editing_recalculates_then_persists_trade_results(self):
        original = normalize_trade(make_futures_trade())
        self.assertTrue(storage.save_trades([original]))

        loaded = storage.load_trades()
        edited_input = dict(loaded[0])
        edited_input["exit"] = 7495.25

        edited = normalize_trade(edited_input)
        loaded[0] = edited
        self.assertTrue(storage.save_trades(loaded))

        reloaded = storage.load_trades()
        self.assertEqual(reloaded[0]["result"], "Loss")
        self.assertEqual(reloaded[0]["net_result"], "Loss")
        self.assertEqual(reloaded[0]["points_pnl"], -5.0)
        self.assertEqual(reloaded[0]["ticks_pnl"], -20.0)
        self.assertEqual(reloaded[0]["dollar_pnl"], -50.0)
        self.assertEqual(reloaded[0]["net_dollar_pnl"], -54.0)

    def test_custom_futures_profile_survives_save_reload_and_edit(self):
        # Release-candidate audit gap: a symbol not in the built-in
        # profile table (as resolve_futures_tick_metadata's manual-entry
        # path would produce) must persist its custom tick_size/tick_value
        # through a save/reload/edit round trip exactly like a
        # built-in-profile trade does.
        custom = normalize_trade(
            make_futures_trade(
                symbol="ZB",  # not in FUTURES_INSTRUMENT_PROFILES
                entry=120.00,
                exit=120.50,
                contracts=2,
                tick_size=0.03125,
                tick_value=31.25,
                commission=4.0,
            )
        )
        # Explicit tick_size/tick_value always derive point_value, whether
        # or not the symbol matches a built-in profile.
        self.assertAlmostEqual(custom["point_value"], 1000.0)

        self.assertTrue(storage.save_trades([custom]))
        reloaded = storage.load_trades()

        self.assertEqual(reloaded[0]["symbol"], "zb")
        self.assertEqual(reloaded[0]["tick_size"], 0.03125)
        self.assertEqual(reloaded[0]["tick_value"], 31.25)
        self.assertAlmostEqual(reloaded[0]["point_value"], 1000.0)
        self.assertAlmostEqual(reloaded[0]["dollar_pnl"], 1000.0)
        self.assertAlmostEqual(reloaded[0]["net_dollar_pnl"], 996.0)

        # Now edit an unrelated field and confirm the custom tick
        # metadata is still intact afterward.
        edited_input = dict(reloaded[0])
        edited_input["notes"] = "Edited after custom profile save"
        edited = normalize_trade(edited_input)
        reloaded[0] = edited
        self.assertTrue(storage.save_trades(reloaded))

        final = storage.load_trades()
        self.assertEqual(final[0]["tick_size"], 0.03125)
        self.assertEqual(final[0]["tick_value"], 31.25)
        self.assertAlmostEqual(final[0]["point_value"], 1000.0)
        self.assertAlmostEqual(final[0]["dollar_pnl"], 1000.0)
        self.assertEqual(final[0]["notes"], "Edited after custom profile save")

    def test_deleting_trade_persists_and_updates_analytics(self):
        win = normalize_trade(make_futures_trade())
        loss = normalize_trade(
            make_futures_trade(
                direction="short",
                entry=7510.25,
                exit=7520.25,
                contracts=1,
                commission=2.0,
                trade_date="2026-07-31",
            )
        )
        self.assertTrue(storage.save_trades([win, loss]))

        loaded = storage.load_trades()
        del loaded[1]
        self.assertTrue(storage.save_trades(loaded))

        reloaded = storage.load_trades()
        sessions = calculate_session_analysis(reloaded)
        streaks = calculate_streaks(reloaded)

        self.assertEqual(reloaded, [win])
        self.assertEqual(
            sessions["New York/London Overlap"]["total_trades"],
            1,
        )
        self.assertEqual(sessions["New York/London Overlap"]["wins"], 1)
        self.assertEqual(streaks["current_type"], "Win")
        self.assertEqual(streaks["current_length"], 1)

    def test_loading_legacy_trade_normalizes_and_rewrites_file(self):
        legacy_trade = make_futures_trade()
        legacy_trade.pop("market_type")
        self.write_json(self.trades_file, [legacy_trade])

        loaded = storage.load_trades()
        rewritten = self.read_json(self.trades_file)

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["market_type"], "futures")
        self.assertEqual(loaded[0]["symbol"], "mes")
        self.assertEqual(rewritten, loaded)
        self.assertTrue(
            list(
                self.data_directory.glob(
                    "trades_backup_before_validation_*.json"
                )
            )
        )

    def test_loading_mixed_valid_and_invalid_records_rejects_only_invalid(self):
        self.write_json(
            self.trades_file,
            [make_futures_trade(), "not a trade object"],
        )

        loaded = storage.load_trades()
        rewritten = self.read_json(self.trades_file)
        rejected_files = list(
            self.data_directory.glob("rejected_trades_*.json")
        )

        self.assertEqual(len(loaded), 1)
        self.assertEqual(rewritten, loaded)
        self.assertEqual(len(rejected_files), 1)

        rejected = self.read_json(rejected_files[0])
        self.assertEqual(rejected[0]["trade_number"], 2)
        self.assertEqual(
            rejected[0]["errors"],
            ["Trade record must be a JSON object."],
        )
        self.assertEqual(rejected[0]["original_record"], "not a trade object")

    def test_corrupted_trade_file_is_backed_up_and_returns_empty_list(self):
        self.trades_file.write_text("{invalid json", encoding="utf-8")

        loaded = storage.load_trades()

        self.assertEqual(loaded, [])
        backups = list(
            self.data_directory.glob(
                "trades_backup_corrupted_*.json"
            )
        )
        self.assertEqual(len(backups), 1)
        self.assertEqual(
            backups[0].read_text(encoding="utf-8"),
            "{invalid json",
        )

    def test_mixed_trades_export_to_csv_with_market_specific_fields(self):
        futures_trade = normalize_trade(make_futures_trade())
        forex_trade = normalize_trade(make_forex_trade())
        self.assertTrue(
            storage.save_trades([futures_trade, forex_trade])
        )
        loaded = storage.load_trades()

        with patch.object(storage, "datetime") as mocked_datetime:
            mocked_datetime.now.return_value.strftime.return_value = (
                "2026-08-06_14-30"
            )
            storage.export_trades_to_csv(loaded)

        export_path = (
            self.data_directory
            / "trades_export_2026-08-06_14-30.csv"
        )
        with open(
            export_path,
            "r",
            newline="",
            encoding="utf-8",
        ) as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Market Type"], "futures")
        self.assertEqual(rows[0]["Symbol"], "MES")
        self.assertEqual(rows[0]["Ticks P/L"], "41.0")
        self.assertEqual(rows[0]["Pips P/L"], "")
        self.assertEqual(rows[1]["Market Type"], "forex")
        self.assertEqual(rows[1]["Symbol"], "EUR/USD")
        self.assertEqual(rows[1]["Entry"], "1.10000")
        self.assertEqual(rows[1]["Pips P/L"], "15.0")
        self.assertEqual(rows[1]["Ticks P/L"], "")

    def test_overnight_trade_duration_survives_save_and_reload(self):
        overnight = normalize_trade(
            make_futures_trade(
                entry_time="23:50",
                exit_time="00:10",
            )
        )

        self.assertTrue(storage.save_trades([overnight]))
        loaded = storage.load_trades()

        self.assertEqual(loaded[0]["duration"], 20)
        self.assertEqual(loaded[0]["entry_time"], "23:50")
        self.assertEqual(loaded[0]["exit_time"], "00:10")

    def test_second_save_preserves_previous_valid_file_as_backup(self):
        first_trade = normalize_trade(make_futures_trade())
        second_trade = normalize_trade(make_forex_trade())

        self.assertTrue(storage.save_trades([first_trade]))
        self.assertTrue(storage.save_trades([second_trade]))

        current = self.read_json(self.trades_file)
        backup = self.read_json(
            self.data_directory / "trades_backup.json"
        )

        self.assertEqual(current, [second_trade])
        self.assertEqual(backup, [first_trade])

    def test_equity_history_sorts_reloaded_trades_without_reordering_storage(self):
        later_trade = normalize_trade(
            make_futures_trade(trade_date="2026-07-31")
        )
        earlier_trade = normalize_trade(
            make_futures_trade(
                trade_date="2026-07-29",
                exit=7505.25,
            )
        )
        self.assertTrue(
            storage.save_trades([later_trade, earlier_trade])
        )

        loaded = storage.load_trades()
        original_order = [trade["trade_date"] for trade in loaded]
        result = calculate_equity_drawdown_history(loaded, 25000)

        self.assertEqual(
            [row["trade_date"] for row in result["history"]],
            ["2026-07-29", "2026-07-31"],
        )
        self.assertEqual(
            [trade["trade_date"] for trade in loaded],
            original_order,
        )

    def test_missing_data_files_produce_clean_empty_startup_state(self):
        self.assertFalse(self.trades_file.exists())
        self.assertFalse(self.account_file.exists())

        self.assertEqual(storage.load_trades(), [])
        self.assertIsNone(storage.load_account())
        self.assertFalse(self.trades_file.exists())
        self.assertFalse(self.account_file.exists())

    def test_legacy_account_normalizes_rewrites_and_loads_with_trades(self):
        self.write_json(
            self.account_file,
            {
                "name": "  Evaluation Account  ",
                "type": "evaluation",
                "starting_balance": "25000",
            },
        )
        trade = normalize_trade(make_futures_trade())
        self.assertTrue(storage.save_trades([trade]))

        account = storage.load_account()
        trades = storage.load_trades()

        self.assertEqual(account["name"], "Evaluation Account")
        self.assertEqual(account["type"], "Evaluation")
        self.assertEqual(account["starting_balance"], 25000.0)
        self.assertEqual(account["high_water_mark"], 25000.0)
        self.assertIsNone(account["account_currency"])
        self.assertEqual(self.read_json(self.account_file), account)
        self.assertEqual(trades, [trade])


if __name__ == "__main__":
    unittest.main()