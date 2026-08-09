import csv
import json
import math
import os
import tempfile
import unittest
from unittest.mock import mock_open, patch

import journal.storage as storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.data_directory = self.temporary_directory.name
        self.trades_file = os.path.join(
            self.data_directory,
            "trades.json",
        )
        self.account_file = os.path.join(
            self.data_directory,
            "account.json",
        )

        patches = [
            patch.object(
                storage,
                "data_dir",
                self.data_directory,
            ),
            patch.object(
                storage,
                "TRADES_FILE",
                self.trades_file,
            ),
            patch.object(
                storage,
                "ACCOUNT_FILE",
                self.account_file,
            ),
        ]

        for active_patch in patches:
            active_patch.start()
            self.addCleanup(active_patch.stop)

    def write_json(self, file_path, data):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file)

    def read_json(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def fixed_datetime(self, timestamp):
        datetime_patch = patch.object(storage, "datetime")
        mocked_datetime = datetime_patch.start()
        self.addCleanup(datetime_patch.stop)
        mocked_datetime.now.return_value.strftime.return_value = timestamp
        return mocked_datetime

    def test_create_timestamped_backup_returns_none_when_source_is_missing(self):
        missing_path = os.path.join(
            self.data_directory,
            "missing.json",
        )

        result = storage.create_timestamped_backup(
            missing_path,
            "corrupted",
        )

        self.assertIsNone(result)

    def test_create_timestamped_backup_copies_the_original_file(self):
        self.fixed_datetime("2026-08-01_10-20-30")
        original_data = {"starting_balance": 25000}
        self.write_json(self.account_file, original_data)

        result = storage.create_timestamped_backup(
            self.account_file,
            "before_validation",
        )

        expected_path = os.path.join(
            self.data_directory,
            (
                "account_backup_before_validation_"
                "2026-08-01_10-20-30.json"
            ),
        )
        self.assertEqual(result, expected_path)
        self.assertEqual(
            self.read_json(expected_path),
            original_data,
        )

    def test_create_timestamped_backup_preserves_the_file_extension(self):
        self.fixed_datetime("2026-08-01_10-20-30")
        source_path = os.path.join(
            self.data_directory,
            "journal.data.json",
        )
        self.write_json(source_path, [1, 2, 3])

        result = storage.create_timestamped_backup(
            source_path,
            "safe",
        )

        self.assertTrue(
            result.endswith(
                "journal.data_backup_safe_"
                "2026-08-01_10-20-30.json"
            )
        )

    def test_create_timestamped_backup_handles_copy_errors(self):
        self.write_json(self.trades_file, [])

        with (
            patch.object(
                storage.shutil,
                "copy2",
                side_effect=OSError("copy blocked"),
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.create_timestamped_backup(
                self.trades_file,
                "corrupted",
            )

        self.assertIsNone(result)
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertIn("safety copy could not be created", printed_text)
        self.assertIn("copy blocked", printed_text)

    def test_save_json_atomic_creates_parent_directories_and_file(self):
        file_path = os.path.join(
            self.data_directory,
            "nested",
            "saved.json",
        )
        data = {"trades": [1, 2], "active": True}

        result = storage.save_json_atomic(file_path, data)

        self.assertTrue(result)
        self.assertEqual(self.read_json(file_path), data)
        self.assertFalse(os.path.exists(f"{file_path}.tmp"))

    def test_save_json_atomic_writes_indented_json(self):
        data = {"symbol": "MES", "contracts": 2}

        result = storage.save_json_atomic(
            self.trades_file,
            data,
        )

        self.assertTrue(result)
        with open(
            self.trades_file,
            "r",
            encoding="utf-8",
        ) as file:
            saved_text = file.read()
        self.assertIn('\n    "symbol": "MES"', saved_text)

    def test_save_json_atomic_backs_up_valid_existing_json(self):
        original_data = [{"symbol": "MES"}]
        replacement_data = [{"symbol": "MNQ"}]
        self.write_json(self.trades_file, original_data)

        result = storage.save_json_atomic(
            self.trades_file,
            replacement_data,
        )

        backup_path = os.path.join(
            self.data_directory,
            "trades_backup.json",
        )
        self.assertTrue(result)
        self.assertEqual(
            self.read_json(self.trades_file),
            replacement_data,
        )
        self.assertEqual(
            self.read_json(backup_path),
            original_data,
        )

    def test_save_json_atomic_does_not_back_up_corrupted_existing_json(self):
        with open(
            self.trades_file,
            "w",
            encoding="utf-8",
        ) as file:
            file.write("not valid json")

        result = storage.save_json_atomic(
            self.trades_file,
            [{"symbol": "MES"}],
        )

        backup_path = os.path.join(
            self.data_directory,
            "trades_backup.json",
        )
        self.assertTrue(result)
        self.assertFalse(os.path.exists(backup_path))
        self.assertEqual(
            self.read_json(self.trades_file),
            [{"symbol": "MES"}],
        )

    def test_save_json_atomic_rejects_non_serializable_data(self):
        with patch("builtins.print") as mocked_print:
            result = storage.save_json_atomic(
                self.trades_file,
                {"invalid": {1, 2, 3}},
            )

        self.assertFalse(result)
        self.assertFalse(os.path.exists(self.trades_file))
        self.assertFalse(os.path.exists(f"{self.trades_file}.tmp"))
        self.assertIn(
            "Error saving",
            str(mocked_print.call_args.args[0]),
        )

    def test_save_json_atomic_rejects_nan(self):
        result = storage.save_json_atomic(
            self.trades_file,
            {"invalid": math.nan},
        )

        self.assertFalse(result)
        self.assertFalse(os.path.exists(self.trades_file))
        self.assertFalse(os.path.exists(f"{self.trades_file}.tmp"))

    def test_save_json_atomic_removes_temporary_file_after_replace_error(self):
        with (
            patch.object(
                storage.os,
                "replace",
                side_effect=OSError("replace failed"),
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.save_json_atomic(
                self.trades_file,
                [],
            )

        self.assertFalse(result)
        self.assertFalse(os.path.exists(f"{self.trades_file}.tmp"))
        self.assertIn(
            "replace failed",
            str(mocked_print.call_args.args[0]),
        )

    def test_save_json_atomic_handles_directory_creation_errors(self):
        nested_path = os.path.join(
            self.data_directory,
            "blocked",
            "saved.json",
        )

        with (
            patch.object(
                storage.os,
                "makedirs",
                side_effect=OSError("directory blocked"),
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.save_json_atomic(
                nested_path,
                [],
            )

        self.assertFalse(result)
        self.assertIn(
            "directory blocked",
            str(mocked_print.call_args.args[0]),
        )

    def test_save_rejected_trades_returns_timestamped_path_on_success(self):
        self.fixed_datetime("2026-08-01_11-22-33")
        rejected = [{"trade_number": 2, "errors": ["bad"]}]

        with patch.object(
            storage,
            "save_json_atomic",
            return_value=True,
        ) as mocked_save:
            result = storage.save_rejected_trades(rejected)

        expected_path = os.path.join(
            self.data_directory,
            "rejected_trades_2026-08-01_11-22-33.json",
        )
        self.assertEqual(result, expected_path)
        mocked_save.assert_called_once_with(
            expected_path,
            rejected,
        )

    def test_save_rejected_trades_returns_none_when_save_fails(self):
        with patch.object(
            storage,
            "save_json_atomic",
            return_value=False,
        ):
            result = storage.save_rejected_trades([{"bad": True}])

        self.assertIsNone(result)

    def test_load_trades_returns_empty_list_when_file_is_missing(self):
        self.assertEqual(storage.load_trades(), [])

    def test_load_trades_handles_corrupted_json_and_creates_backup(self):
        with open(
            self.trades_file,
            "w",
            encoding="utf-8",
        ) as file:
            file.write("{not-json")

        backup_path = os.path.join(
            self.data_directory,
            "corrupted-copy.json",
        )

        with (
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=backup_path,
            ) as mocked_backup,
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_trades()

        self.assertEqual(result, [])
        mocked_backup.assert_called_once_with(
            self.trades_file,
            "corrupted",
        )
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertIn("invalid JSON", printed_text)
        self.assertIn(backup_path, printed_text)

    def test_load_trades_handles_read_errors(self):
        with (
            patch(
                "builtins.open",
                side_effect=OSError("read blocked"),
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_trades()

        self.assertEqual(result, [])
        self.assertIn(
            "read blocked",
            str(mocked_print.call_args.args[0]),
        )

    def test_load_trades_rejects_non_list_top_level_data(self):
        self.write_json(self.trades_file, {"symbol": "MES"})
        backup_path = os.path.join(
            self.data_directory,
            "invalid-structure-copy.json",
        )

        with (
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=backup_path,
            ) as mocked_backup,
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_trades()

        self.assertEqual(result, [])
        mocked_backup.assert_called_once_with(
            self.trades_file,
            "invalid_structure",
        )
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertIn("does not containa list", printed_text)
        self.assertIn(backup_path, printed_text)

    def test_load_trades_returns_valid_normalized_records(self):
        stored_trades = [
            {"symbol": "MES"},
            {"symbol": "EUR/USD"},
        ]
        self.write_json(self.trades_file, stored_trades)

        with (
            patch.object(
                storage,
                "validate_and_normalize_trade",
                side_effect=[
                    (stored_trades[0].copy(), []),
                    (stored_trades[1].copy(), []),
                ],
            ) as mocked_validation,
            patch.object(storage, "save_trades") as mocked_save,
        ):
            result = storage.load_trades()

        self.assertEqual(result, stored_trades)
        self.assertEqual(mocked_validation.call_count, 2)
        mocked_save.assert_not_called()

    def test_load_trades_saves_normalized_changes_and_original_backup(self):
        stored_trade = {"symbol": "mes"}
        normalized_trade = {
            "symbol": "mes",
            "market_type": "futures",
        }
        self.write_json(self.trades_file, [stored_trade])
        backup_path = os.path.join(
            self.data_directory,
            "before-validation-copy.json",
        )

        with (
            patch.object(
                storage,
                "validate_and_normalize_trade",
                return_value=(normalized_trade, []),
            ),
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=backup_path,
            ) as mocked_backup,
            patch.object(
                storage,
                "save_trades",
                return_value=True,
            ) as mocked_save,
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_trades()

        self.assertEqual(result, [normalized_trade])
        mocked_backup.assert_called_once_with(
            self.trades_file,
            "before_validation",
        )
        mocked_save.assert_called_once_with([normalized_trade])
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertIn("validated and normalized", printed_text)
        self.assertIn(backup_path, printed_text)

    def test_load_trades_excludes_and_records_invalid_trades(self):
        valid_trade = {"symbol": "MES"}
        invalid_trade = {"symbol": ""}
        self.write_json(
            self.trades_file,
            [valid_trade, invalid_trade],
        )
        rejected_path = os.path.join(
            self.data_directory,
            "rejected.json",
        )

        with (
            patch.object(
                storage,
                "validate_and_normalize_trade",
                side_effect=[
                    (valid_trade.copy(), []),
                    (None, ["Symbol cannot be blank."]),
                ],
            ),
            patch.object(
                storage,
                "save_rejected_trades",
                return_value=rejected_path,
            ) as mocked_rejected_save,
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=None,
            ),
            patch.object(
                storage,
                "save_trades",
                return_value=True,
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_trades()

        self.assertEqual(result, [valid_trade])
        mocked_rejected_save.assert_called_once_with([
            {
                "trade_number": 2,
                "errors": ["Symbol cannot be blank."],
                "original_record": invalid_trade,
            }
        ])
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertIn("1 invalid trade(s)", printed_text)
        self.assertIn(rejected_path, printed_text)

    def test_load_trades_does_not_claim_rejected_path_when_save_fails(self):
        invalid_trade = {"symbol": ""}
        self.write_json(self.trades_file, [invalid_trade])

        with (
            patch.object(
                storage,
                "validate_and_normalize_trade",
                return_value=(None, ["bad trade"]),
            ),
            patch.object(
                storage,
                "save_rejected_trades",
                return_value=None,
            ),
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=None,
            ),
            patch.object(
                storage,
                "save_trades",
                return_value=True,
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_trades()

        self.assertEqual(result, [])
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertNotIn("rejected records and their errors", printed_text)

    def test_load_trades_warns_when_normalized_data_cannot_be_saved(self):
        stored_trade = {"symbol": "mes"}
        normalized_trade = {
            "symbol": "mes",
            "market_type": "futures",
        }
        self.write_json(self.trades_file, [stored_trade])

        with (
            patch.object(
                storage,
                "validate_and_normalize_trade",
                return_value=(normalized_trade, []),
            ),
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=None,
            ),
            patch.object(
                storage,
                "save_trades",
                return_value=False,
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_trades()

        self.assertEqual(result, [normalized_trade])
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertIn("could not be saved", printed_text)
        self.assertIn("only be available during this session", printed_text)

    def test_save_trades_delegates_to_atomic_save(self):
        trades = [{"symbol": "MES"}]

        with patch.object(
            storage,
            "save_json_atomic",
            return_value=True,
        ) as mocked_save:
            result = storage.save_trades(trades)

        self.assertTrue(result)
        mocked_save.assert_called_once_with(
            self.trades_file,
            trades,
        )

    def test_load_account_returns_none_when_file_is_missing(self):
        self.assertIsNone(storage.load_account())

    def test_load_account_handles_corrupted_json_and_creates_backup(self):
        with open(
            self.account_file,
            "w",
            encoding="utf-8",
        ) as file:
            file.write("[broken")
        backup_path = os.path.join(
            self.data_directory,
            "account-corrupted-copy.json",
        )

        with (
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=backup_path,
            ) as mocked_backup,
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_account()

        self.assertIsNone(result)
        mocked_backup.assert_called_once_with(
            self.account_file,
            "corrupted",
        )
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertIn("invalid JSON", printed_text)
        self.assertIn(backup_path, printed_text)

    def test_load_account_handles_read_errors(self):
        with (
            patch(
                "builtins.open",
                side_effect=OSError("account read blocked"),
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_account()

        self.assertIsNone(result)
        self.assertIn(
            "account read blocked",
            str(mocked_print.call_args.args[0]),
        )

    def test_load_account_rejects_invalid_data_and_prints_each_error(self):
        stored_account = {"starting_balance": -1}
        self.write_json(self.account_file, stored_account)
        errors = [
            "Starting balance must be positive.",
            "Account type is invalid.",
        ]
        backup_path = os.path.join(
            self.data_directory,
            "invalid-account-copy.json",
        )

        with (
            patch.object(
                storage,
                "validate_and_normalize_account",
                return_value=(None, errors),
            ),
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=backup_path,
            ) as mocked_backup,
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_account()

        self.assertIsNone(result)
        mocked_backup.assert_called_once_with(
            self.account_file,
            "invalid",
        )
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertIn("invalid data", printed_text)
        self.assertIn(errors[0], printed_text)
        self.assertIn(errors[1], printed_text)
        self.assertIn(backup_path, printed_text)

    def test_load_account_returns_unchanged_valid_account_without_saving(self):
        stored_account = {
            "starting_balance": 25000.0,
            "account_type": "Funded",
        }
        self.write_json(self.account_file, stored_account)

        with (
            patch.object(
                storage,
                "validate_and_normalize_account",
                return_value=(stored_account.copy(), []),
            ) as mocked_validation,
            patch.object(storage, "save_account") as mocked_save,
            patch.object(
                storage,
                "create_timestamped_backup",
            ) as mocked_backup,
        ):
            result = storage.load_account()

        self.assertEqual(result, stored_account)
        mocked_validation.assert_called_once_with(stored_account)
        mocked_save.assert_not_called()
        mocked_backup.assert_not_called()

    def test_load_account_saves_normalized_changes_and_original_backup(self):
        stored_account = {"starting_balance": 25000}
        normalized_account = {
            "starting_balance": 25000.0,
            "account_type": "Personal",
            "account_currency": "USD",
        }
        self.write_json(self.account_file, stored_account)
        backup_path = os.path.join(
            self.data_directory,
            "account-before-validation-copy.json",
        )

        with (
            patch.object(
                storage,
                "validate_and_normalize_account",
                return_value=(normalized_account, []),
            ),
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=backup_path,
            ) as mocked_backup,
            patch.object(
                storage,
                "save_account",
                return_value=True,
            ) as mocked_save,
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_account()

        self.assertEqual(result, normalized_account)
        mocked_backup.assert_called_once_with(
            self.account_file,
            "before_validation",
        )
        mocked_save.assert_called_once_with(normalized_account)
        printed_text = " ".join(
            str(call.args[0]) for call in mocked_print.call_args_list
        )
        self.assertIn("validated and normalized", printed_text)
        self.assertIn(backup_path, printed_text)

    def test_load_account_returns_normalized_data_when_save_fails(self):
        stored_account = {"starting_balance": 25000}
        normalized_account = {
            "starting_balance": 25000.0,
            "account_type": "Personal",
        }
        self.write_json(self.account_file, stored_account)

        with (
            patch.object(
                storage,
                "validate_and_normalize_account",
                return_value=(normalized_account, []),
            ),
            patch.object(
                storage,
                "create_timestamped_backup",
                return_value=None,
            ),
            patch.object(
                storage,
                "save_account",
                return_value=False,
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.load_account()

        self.assertEqual(result, normalized_account)
        mocked_print.assert_not_called()

    def test_save_account_delegates_to_atomic_save(self):
        account = {"starting_balance": 25000.0}

        with patch.object(
            storage,
            "save_json_atomic",
            return_value=True,
        ) as mocked_save:
            result = storage.save_account(account)

        self.assertTrue(result)
        mocked_save.assert_called_once_with(
            self.account_file,
            account,
        )

    def test_export_trades_to_csv_stops_when_there_are_no_trades(self):
        with patch("builtins.print") as mocked_print:
            result = storage.export_trades_to_csv([])

        self.assertIsNone(result)
        mocked_print.assert_called_once_with("No trades to export.")
        self.assertEqual(os.listdir(self.data_directory), [])

    def test_export_trades_to_csv_writes_futures_trade(self):
        self.fixed_datetime("2026-08-01_12-34")
        trade = {
            "symbol": "mes",
            "direction": "long",
            "entry": 7500.12567,
            "exit": 7510.37567,
            "contracts": 2,
            "point_value": 5.0,
            "risk_amount": 100.0,
            "points_pnl": 10.25,
            "dollar_pnl": 102.5,
            "commission": 4.0,
            "net_dollar_pnl": 98.5,
            "realized_r": 1.025,
            "result": "Win",
            "net_result": "Win",
            "trade_date": "2026-07-31",
            "entry_time": "09:30",
            "exit_time": "10:00",
            "duration": 30,
            "strategy_method": "ICT",
            "setup": "FVG",
            "session": "New York/London Overlap",
            "notes": "Good patience",
            "mistake": "None",
            "market_type": "futures",
            "tick_size": 0.25,
            "tick_value": 1.25,
            "ticks_pnl": 41.0,
        }

        with (
            patch.object(
                storage,
                "get_strategy_method",
                return_value="ICT",
            ),
            patch.object(
                storage,
                "get_setup_components",
                return_value=["Fair Value Gap (FVG)"],
            ),
            patch("builtins.print") as mocked_print,
        ):
            result = storage.export_trades_to_csv([trade])

        self.assertIsNone(result)
        csv_path = os.path.join(
            self.data_directory,
            "trades_export_2026-08-01_12-34.csv",
        )
        with open(
            csv_path,
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["Trade Number"], "1")
        self.assertEqual(row["Symbol"], "MES")
        self.assertEqual(row["Entry"], "7500.1257")
        self.assertEqual(row["Exit"], "7510.3757")
        self.assertEqual(row["Points P/L"], "10.25")
        self.assertEqual(row["Gross Dollar P/L"], "102.5")
        self.assertEqual(row["Net Dollar P/L"], "98.5")
        self.assertEqual(row["Strategy / Method"], "ICT")
        self.assertEqual(
            row["Setup Components"],
            "Fair Value Gap (FVG)",
        )
        self.assertEqual(row["Market Type"], "futures")
        self.assertEqual(row["Tick Size"], "0.25")
        self.assertEqual(row["Tick Value"], "1.25")
        self.assertEqual(row["Ticks P/L"], "41.0")
        self.assertEqual(row["Pips P/L"], "")
        mocked_print.assert_called_once_with(
            f"Trades exported to {csv_path} successfully."
        )

    def test_export_trades_to_csv_formats_forex_prices_and_fields(self):
        self.fixed_datetime("2026-08-01_13-45")
        trade = {
            "symbol": "eur/usd",
            "direction": "short",
            "entry": 1.09005,
            "exit": 1.08988,
            "risk_amount": 100.0,
            "dollar_pnl": 17.0,
            "commission": 2.0,
            "net_dollar_pnl": 15.0,
            "realized_r": 0.17,
            "result": "Win",
            "net_result": "Win",
            "trade_date": "2026-07-30",
            "entry_time": "10:00",
            "exit_time": "10:20",
            "duration": 20,
            "strategy_methods": ["ICT", "Order Flow"],
            "setup_components": ["FVG", "CVD Divergence"],
            "session": "New York/London Overlap",
            "notes": "",
            "mistake": "",
            "market_type": "forex",
            "lot_size": 0.1,
            "pip_size": 0.0001,
            "pip_value": 1.0,
            "pips_pnl": 1.7,
            "price_precision": 5,
        }

        with (
            patch.object(
                storage,
                "get_strategy_method",
                return_value="ICT, Order Flow",
            ),
            patch.object(
                storage,
                "get_setup_components",
                return_value=[
                    "Fair Value Gap (FVG)",
                    "Cumulative Volume Delta (CVD) Divergence",
                ],
            ),
        ):
            storage.export_trades_to_csv([trade])

        csv_path = os.path.join(
            self.data_directory,
            "trades_export_2026-08-01_13-45.csv",
        )
        with open(
            csv_path,
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            row = next(csv.DictReader(file))

        self.assertEqual(row["Symbol"], "EUR/USD")
        self.assertEqual(row["Entry"], "1.09005")
        self.assertEqual(row["Exit"], "1.08988")
        self.assertEqual(row["Contracts"], "")
        self.assertEqual(row["Points P/L"], "")
        self.assertEqual(row["Lot Size"], "0.1")
        self.assertEqual(row["Pip Size"], "0.0001")
        self.assertEqual(row["Pip Value"], "1.0")
        self.assertEqual(row["Pips P/L"], "1.7")
        self.assertEqual(row["Price Precision"], "5")
        self.assertEqual(
            row["Strategy / Method"],
            "ICT, Order Flow",
        )
        self.assertEqual(
            row["Setup Components"],
            (
                "Fair Value Gap (FVG) + "
                "Cumulative Volume Delta (CVD) Divergence"
            ),
        )

    def test_export_trades_to_csv_uses_legacy_fallbacks(self):
        self.fixed_datetime("2026-08-01_14-00")
        legacy_trade = {
            "symbol": "MES",
            "entry": 5000,
            "exit": 5001,
            "dollar_pnl": -5.0,
            "result": "Loss",
            "trade_date": "2026-08-01",
        }

        with (
            patch.object(
                storage,
                "get_strategy_method",
                return_value="Unspecified",
            ),
            patch.object(
                storage,
                "get_setup_components",
                return_value=["Unspecified"],
            ),
        ):
            storage.export_trades_to_csv([legacy_trade])

        csv_path = os.path.join(
            self.data_directory,
            "trades_export_2026-08-01_14-00.csv",
        )
        with open(
            csv_path,
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            row = next(csv.DictReader(file))

        self.assertEqual(row["Market Type"], "futures")
        self.assertEqual(row["Net Dollar P/L"], "-5.0")
        self.assertEqual(row["Net Result"], "Loss")
        self.assertEqual(row["Trade Date"], "2026 08 01")

    def test_export_trades_to_csv_numbers_multiple_trades_in_order(self):
        self.fixed_datetime("2026-08-01_15-00")
        trades = [
            {"symbol": "MES", "entry": 1, "exit": 2},
            {"symbol": "MNQ", "entry": 3, "exit": 4},
        ]

        with (
            patch.object(
                storage,
                "get_strategy_method",
                return_value="Unspecified",
            ),
            patch.object(
                storage,
                "get_setup_components",
                return_value=["Unspecified"],
            ),
        ):
            storage.export_trades_to_csv(trades)

        csv_path = os.path.join(
            self.data_directory,
            "trades_export_2026-08-01_15-00.csv",
        )
        with open(
            csv_path,
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(
            [row["Trade Number"] for row in rows],
            ["1", "2"],
        )
        self.assertEqual(
            [row["Symbol"] for row in rows],
            ["MES", "MNQ"],
        )

    def test_export_trades_to_csv_handles_write_errors(self):
        with (
            patch(
                "builtins.open",
                mock_open(),
            ) as mocked_open,
            patch("builtins.print") as mocked_print,
        ):
            mocked_open.side_effect = OSError("csv blocked")
            result = storage.export_trades_to_csv([
                {"symbol": "MES"}
            ])

        self.assertIsNone(result)
        mocked_print.assert_called_once_with(
            "Error exporting trades: csv blocked"
        )


if __name__ == "__main__":
    unittest.main()