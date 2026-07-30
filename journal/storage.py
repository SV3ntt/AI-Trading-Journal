import csv
import json
import os
import shutil
from datetime import datetime

from journal.constants import ACCOUNT_FILE, TRADES_FILE, data_dir
from journal.analytics import get_setup_components, get_strategy_method
from journal.validation import validate_and_normalize_account, validate_and_normalize_trade


def create_timestamped_backup(
            file_path, 
            label
): 
      if not os.path.exists(file_path):
            return None
      
      timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
      )
      
      file_root, file_extension = (
            os.path.splitext(file_path)
      )
      backup_path = (
            f"{file_root}_backup_{label}_{timestamp}"
            f"{file_extension}"
      )

      try:
            shutil.copy2(
                  file_path,
                  backup_path
            )

            return backup_path
      
      except OSError as error:
            print(
                  "Warning: a safety copy could not "
                  f"be created for {file_path}: "
                  f"{error}"
            )

            return None
      
def save_json_atomic(
            file_path,
            data
):
      
      directory = os.path.dirname(file_path)

      temporary_path = (
            f"{file_path}.tmp"
      )

      backup_path = (
            f"{os.path.splitext(file_path)[0]}"
            "_backup.json"
      )

      try:
            if directory:
                  os.makedirs(
                        directory,
                        exist_ok=True
                  )

            with open(
                  temporary_path,
                  "w",
                  encoding="utf-8"
            ) as file:
                  json.dump(
                        data,
                        file,
                        indent=4,
                        allow_nan=False
                  )

                  file.flush()
                  os.fsync(file.fileno())

            if os.path.exists(file_path):
                  try:
                        with open(
                              file_path,
                              "r",
                              encoding="utf-8"
                        ) as existing_file:
                              json.load(existing_file)

                        shutil.copy2(
                              file_path,
                              backup_path
                        )

                  except(
                        OSError,
                        json.JSONDecodeError
                  ):
                        pass

            os.replace(
                  temporary_path,
                  file_path
            )

            return True

      except (
            OSError,
            TypeError, 
            ValueError, 
      ) as error:
            print(
                  f"Error saving {file_path}: "
                  f"{error}"
            )

            try: 
                  if os.path.exists(
                        temporary_path
                  ):
                        os.remove(
                              temporary_path
                        )
                  
            except OSError: 
                  pass
            
            return False

def save_rejected_trades(
            rejected_trades
):
      
      timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
      )

      rejected_path = os.path.join(
            data_dir,
            f"rejected_trades_"
            f"{timestamp}.json"
      )

      if save_json_atomic(
            rejected_path,
            rejected_trades
      ):
            return rejected_path

      return None

def load_trades(): 
      try:
            with open(
                  TRADES_FILE, 
                  "r", 
                  encoding="utf-8"
            ) as file:
                  stored_data = json.load(file)

      except FileNotFoundError:
            return []
      
      except json.JSONDecodeError: 
            backup_path = (
                  create_timestamped_backup(
                        TRADES_FILE,
                        "corrupted"
                  )
            )

            print(
                  "Warning: trades.json contains "
                  "invalid JSON. The journal started "
                  "with no loaded trades."

            )

            if backup_path is not None: 
                  print(
                        "A safety copy was saved to "
                        f"{backup_path}"
                  )

            return []
      
      except OSError as error:
            print(
                  f"Error reading trades.json: "
                  f"{error}"
            )

            return []


      if not isinstance(stored_data, list): 
            backup_path = (
                  create_timestamped_backup(
                        TRADES_FILE,
                        "invalid_structure"
                  )
            )

            print(
                  "Warning: trades.json does not contain"
                  "a list of trades. The journal "
                  "started with no loaded trades."
            )

            if backup_path is not None:
                  print(
                        "A safety copy was saved to "
                        f"{backup_path}"
                  )

            return []
      
      valid_trades = []
      rejected_trades = []
      data_changed = False

      for (
            trade_number, 
            stored_trade
      ) in enumerate(
            stored_data, 
            start=1
      ):
            (
                  normalized_trade,
                  errors
            )= validate_and_normalize_trade(
                  stored_trade
            )

            if errors:
                  rejected_trades.append({
                        "trade_number": (
                              trade_number
                        ), 

                        "errors": errors,

                        "original_record": (
                              stored_trade
                        ), 

                  })

                  continue

            valid_trades.append(
                  normalized_trade
            )

            if normalized_trade != stored_trade:
                  data_changed = True

      if rejected_trades: 
            data_changed = True

            rejected_path = (
                  save_rejected_trades(
                        rejected_trades
                  )
            )

            print(
                  "Warning: "
                  f"{len(rejected_trades)} invalid "
                  "trade(s) were excluded from the "
                  "active journal."
            )

            if rejected_path is not None:
                  print(
                        "The rejected records and their "
                        "errors were saved to "
                        f"{rejected_path}"
                  )

      if data_changed:
            backup_path = (
                  create_timestamped_backup(
                        TRADES_FILE,
                        "before_validation"
                  )
            )

            if save_trades(valid_trades): 
                  print(
                        "Trade data was validated " 
                        "and normalized."
                  )

                  if backup_path is not None: 
                        print(
                              "The original file was " 
                              "backed up to "
                              f"{backup_path}"
                        )

            else:
                  print(
                        "Warning: normalized trade" 
                        "data could not be saved."
                        "The validated data will only "
                        "be available during this "
                        "session."
                  )

      return valid_trades

def save_trades(trades):
      return save_json_atomic(
            TRADES_FILE,
            trades
      )

def load_account():
      try: 
            with open(
                  ACCOUNT_FILE, 
                  "r", 
                  encoding="utf-8"
            ) as file: 
                  stored_account = json.load(file)

      except FileNotFoundError:
            return None
      
      except json.JSONDecodeError:
            backup_path = (
                  create_timestamped_backup(
                        ACCOUNT_FILE,
                        "corrupted"
                  )
            )

            print(
                  "Warning: account.json contains "
                  "invalid JSON."
            )

            if backup_path is not None: 
                  print(
                        "A safety copy was saved to "
                        f"{backup_path}"
                  )

            return None

      except OSError as error:
            print(
                  f"Error reading account.json: "
                  f"{error}"
            )

            return None

      (
            normalized_account,
            errors
      ) = validate_and_normalize_account(
            stored_account
      )

      if errors: 
            backup_path = (
                  create_timestamped_backup(
                        ACCOUNT_FILE,
                        "invalid"
                  )
            )

            print(
                  "Warning: account.json contains "
                  "invalid data."
            )

            for error in errors: 
                  print(f"- {error}")

            if backup_path is not None:
                  print(
                        "A safety copy was saved to "
                        f"{backup_path}"
                  )

            return None

      if normalized_account != stored_account:
            backup_path = (
                  create_timestamped_backup(
                        ACCOUNT_FILE,
                        "before_validation"
                  )
            )

            if save_account(normalized_account): 
                  print(
                        "Account data was validated "
                        "and normalized."
                  )

                  if backup_path is not None: 
                        print(
                              "The original file was "
                              "backed up to "
                              f"{backup_path}"
                        )

      return normalized_account

def save_account(account):
      return save_json_atomic(
            ACCOUNT_FILE,
            account
      )

def export_trades_to_csv(trades): 
      if len(trades) == 0:
            print("No trades to export.")
            return
      
      filename = os.path.join(
            data_dir, 
            (
                  "trades_export_"
                  f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
            )
      )
      
      headers = [
            "Trade Number",
            "Symbol",
            "Direction",
            "Entry",
            "Exit",
            "Contracts",
            "Point Value",
            "Risk Amount",
            "Points P/L",
            "Gross Dollar P/L",
            "Commission",
            "Net Dollar P/L",
            "Realized R",
            "Result",
            "Net Result",
            "Trade Date",
            "Entry Time",
            "Exit Time",
            "Duration (minutes)",
            "Strategy / Method",
            "Setup Components",
            "Session",
            "Notes",
            "Mistake",
            "Market Type",
            "Tick Size",
            "Tick Value",
            "Ticks P/L",
            "Lot Size",
            "Pip Size",
            "Pip Value",
            "Pips P/L",
            "Price Precision"
      ]

      try:
            with open(filename, "w", newline="", encoding="utf-8") as file:
                  writer = csv.writer(file)

                  writer.writerow(headers)

                  for i, trade in enumerate(trades):
                        market_type = trade.get(
                              "market_type",
                              "futures"
                        )
                        price_precision = trade.get(
                              "price_precision"
                        )

                        if (
                              market_type == "forex"
                              and price_precision is not None
                        ):
                              entry_display = (
                                    f"{trade.get('entry', 0):.{price_precision}f}"
                              )
                              exit_display = (
                                    f"{trade.get('exit', 0):.{price_precision}f}"
                              )
                        else:
                              entry_display = round(
                                    trade.get("entry", 0), 4
                              )
                              exit_display = round(
                                    trade.get("exit", 0), 4
                              )

                        point_value = trade.get("point_value")
                        tick_size = trade.get("tick_size")
                        tick_value = trade.get("tick_value")
                        ticks_pnl = trade.get("ticks_pnl")
                        lot_size = trade.get("lot_size")
                        pip_size = trade.get("pip_size")
                        pip_value = trade.get("pip_value")
                        pips_pnl = trade.get("pips_pnl")

                        writer.writerow([
                              i + 1,
                              trade.get("symbol", "").upper(),
                              trade.get("direction", ""),
                              entry_display,
                              exit_display,
                              trade.get("contracts", ""),
                              (
                                    round(point_value, 2)
                                    if point_value is not None
                                    else ""
                              ),
                              trade.get("risk_amount", ""),
                              (
                                    round(trade.get("points_pnl", 0), 2)
                                    if market_type == "futures"
                                    else ""
                              ),
                              round(trade.get("dollar_pnl", 0), 2),
                              round(trade.get("commission", 0), 2),
                              round(
                                    trade.get(
                                          "net_dollar_pnl",
                                          trade.get("dollar_pnl", 0)
                                    ),
                                    2
                              ),
                              round(trade.get("realized_r", 0), 2),
                              trade.get("result", ""),
                              trade.get(
                                    "net_result",
                                    trade.get("result", "")
                              ),
                              trade.get("trade_date", "").replace("-", " "),
                              trade.get("entry_time", ""),
                              trade.get("exit_time", ""),
                              trade.get("duration", ""),
                              get_strategy_method(trade),
                              " + ".join(get_setup_components(trade)),
                              trade.get("session", ""),
                              trade.get("notes", ""),
                              trade.get("mistake", ""),
                              market_type,
                              (
                                    tick_size
                                    if tick_size is not None
                                    else ""
                              ),
                              (
                                    round(tick_value, 4)
                                    if tick_value is not None
                                    else ""
                              ),
                              (
                                    round(ticks_pnl, 2)
                                    if ticks_pnl is not None
                                    else ""
                              ),
                              (
                                    lot_size
                                    if lot_size is not None
                                    else ""
                              ),
                              (
                                    pip_size
                                    if pip_size is not None
                                    else ""
                              ),
                              (
                                    round(pip_value, 4)
                                    if pip_value is not None
                                    else ""
                              ),
                              (
                                    round(pips_pnl, 2)
                                    if pips_pnl is not None
                                    else ""
                              ),
                              (
                                    price_precision
                                    if price_precision is not None
                                    else ""
                              )
                        ])

                  print(f"Trades exported to {filename} successfully.")
            
      except OSError as e:
            print(f"Error exporting trades: {e}")

