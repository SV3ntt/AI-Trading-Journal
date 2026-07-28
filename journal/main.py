import csv
import json
import math
import os
import shutil
from datetime import datetime, timedelta, time as dt_time

valid_directions = ("long", "short")
PROJECT_ROOT = os.path.dirname(
      os.path.dirname(os.path.abspath(__file__))
)

data_dir = os.path.join(
      PROJECT_ROOT,
      "data"
)

TRADES_FILE = os.path.join(
      data_dir,
      "trades.json"
)

ACCOUNT_FILE = os.path.join(
      data_dir,
      "account.json"
)

VALID_ACCOUNT_TYPES = (
      "Personal",
      "Evaluation",
      "Funded",
)

MAINTENANCE_SESSION_NAME = (
      "Market Maintenance / Outside Sessions"
)

SESSION_DISPLAY_ORDER = (
      "Sydney",
      "Sydney/Asia Overlap",
      "Asia/London Overlap",
      "London",
      "New York/London Overlap",
      "New York",
      MAINTENANCE_SESSION_NAME,
)

WEEKLY_DISPLAY_ORDER = (
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
      "Sunday",
      "Unspecified",
)

DURATION_DISPLAY_ORDER = (
      "0 - 15 minutes",
      "16 - 30 minutes",
      "31 - 60 minutes",
      "61 - 120 minutes",
      "121 - 240 minutes",
      "241+ minutes",
      "Unspecified",
)

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

def show_menu():
      print("\n========== AI TRADING JOURNAL ==========")
      print()
      print("1. Account Status")
      print("2. Edit Account")
      print()
      print("3. Add Trade")
      print("4. View Trades")
      print("5. Edit Trade")
      print("6. Delete Trade")
      print()
      print("7. Trading Statistics")
      print("8. Search / Filter Trades")
      print("9. Filtered Statistics")
      print()
      print("10. Session Analytics")
      print("11. Setup Component Analytics")
      print("12. Time Based Analytics")
      print("13. Equity and Drawdown History")
      print()
      print("14. Save Trades")
      print("15. Export Trades to CSV")
      print()
      print("16. Quit")

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
            "Mistake"
      ]

      try:
            with open(filename, "w", newline="", encoding="utf-8") as file:
                  writer = csv.writer(file)

                  writer.writerow(headers)

                  for i, trade in enumerate(trades):
                        writer.writerow([
                              i + 1,
                              trade.get("symbol", "").upper(),
                              trade.get("direction", ""),
                              round(trade.get("entry", 0), 4),
                              round(trade.get("exit", 0), 4),
                              trade.get("contracts", ""),
                              round(trade.get("point_value", 0), 2),
                              trade.get("risk_amount", ""),
                              round(trade.get("points_pnl", 0), 2),
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
                              trade.get("mistake", "")
                        ])
                  
                  print(f"Trades exported to {filename} successfully.")
            
      except OSError as e:
            print(f"Error exporting trades: {e}")

def calculate_points_pnl(direction, entry, exit_price):
      if direction == "long":
            return exit_price - entry
      else:
            return entry - exit_price
      
def calculate_dollar_pnl(points_pnl, point_value, contracts):
      return points_pnl * point_value * contracts

def calculate_net_dollar_pnl(dollar_pnl, commission):
      return dollar_pnl - commission

def calculate_realized_r(dollar_pnl, risk_amount):
      if risk_amount > 0:
            return dollar_pnl / risk_amount
      else:
            return 0

def calculate_result(points_pnl):
      if points_pnl > 0:
            return "Win"
      elif points_pnl < 0:
            return "Loss"
      else:
            return "Break-even"

def calculate_net_result(net_dollar_pnl):
      if net_dollar_pnl > 0:
            return "Win"
      elif net_dollar_pnl < 0:
            return "Loss"
      else:
            return "Break-even"

def calculate_streaks(trades):
      if len(trades) == 0:
            return {
                  "current_type": "None",
                  "current_length": 0,
                  "longest_winning": 0,
                  "longest_losing": 0
            }

      current_streak_type = None
      current_streak_length = 0
      longest_winning = 0
      longest_losing = 0

      for trade in trades:
            result = trade.get("net_result", trade.get("result", "Break-even"))

            if result == "Win":
                  if current_streak_type == "Win":
                        current_streak_length += 1
                  else:
                        current_streak_type = "Win"
                        current_streak_length = 1

                  if current_streak_length > longest_winning:
                        longest_winning = current_streak_length

            elif result == "Loss":
                  if current_streak_type == "Loss":
                        current_streak_length += 1
                  else:
                        current_streak_type = "Loss"
                        current_streak_length = 1

                  if current_streak_length > longest_losing:
                        longest_losing = current_streak_length

            else:
                  current_streak_type = None
                  current_streak_length = 0

      return {
            "current_type": current_streak_type if current_streak_type is not None else "None",
            "current_length": current_streak_length,
            "longest_winning": longest_winning,
            "longest_losing": longest_losing
      }

def normalize_session_name(session):
      if session is None:
            return "Unspecified"

      session_text = str(session).strip().lower()

      if session_text == "":
            return "Unspecified"

      session_aliases = {
            "ny": "New York",
            "ny session": "New York",
            "new york": "New York",
            "new york session": "New York",

            "lon": "London",
            "london": "London",
            "london session": "London",

            "as": "Asia",
            "asia": "Asia",
            "asian": "Asia",
            "asia session": "Asia",
            "asian session": "Asia",

            "sydney": "Sydney",
            "syd": "Sydney",
            "sydney session": "Sydney",

            "london/new york": "New York/London Overlap",
            "new york/london": "New York/London Overlap",
            "ny/lon": "New York/London Overlap",
            "lon/ny": "New York/London Overlap",
            "london/ny": "New York/London Overlap",
            "ny/london": "New York/London Overlap",
            "new york/lon": "New York/London Overlap",
            "new york/lon overlap": "New York/London Overlap",
            "new york/london overlap": "New York/London Overlap",
            "ny/london overlap": "New York/London Overlap",
            "london new york overlap": "New York/London Overlap",

            "asia/london": "Asia/London Overlap",
            "london/asia": "Asia/London Overlap",
            "lon/as": "Asia/London Overlap",
            "as/lon": "Asia/London Overlap",
            "asia/london overlap": "Asia/London Overlap",

            "sydney/asia": "Sydney/Asia Overlap",
            "asia/sydney": "Sydney/Asia Overlap",
            "as/syd": "Sydney/Asia Overlap",
            "syd/as": "Sydney/Asia Overlap",
            "sydney/asia overlap": "Sydney/Asia Overlap",

            "market maintenance": MAINTENANCE_SESSION_NAME,
            "outside sessions": MAINTENANCE_SESSION_NAME,
            "market maintenance / outside sessions": MAINTENANCE_SESSION_NAME
      }

      return session_aliases.get(
            session_text,
            session_text.title()
      )

def determine_session(entry_time):
      if not entry_time:
            return None

      try:
            parsed_time = datetime.strptime(entry_time.strip(), "%H:%M").time()
      except (ValueError, TypeError, AttributeError):
            return None

      if dt_time(17, 0) <= parsed_time < dt_time(18, 0):
            return MAINTENANCE_SESSION_NAME
      elif dt_time(18, 0) <= parsed_time < dt_time(20, 0):
            return "Sydney"
      elif parsed_time >= dt_time(20, 0) or parsed_time < dt_time(3, 0):
            return "Sydney/Asia Overlap"
      elif dt_time(3, 0) <= parsed_time < dt_time(5, 0):
            return "Asia/London Overlap"
      elif dt_time(5, 0) <= parsed_time < dt_time(8, 0):
            return "London"
      elif dt_time(8, 0) <= parsed_time < dt_time(12, 0):
            return "New York/London Overlap"
      elif dt_time(12, 0) <= parsed_time < dt_time(17, 0):
            return "New York"
      else:
            return None

def calculate_session_analysis(trades):
      session_analytics = {}

      for trade in trades:
            session_name = normalize_session_name(
                  trade.get("session", "")
            )

            if session_name not in session_analytics:
                  session_analytics[session_name] = {
                        "total_trades": 0,
                        "wins": 0,
                        "losses": 0,
                        "breakevens": 0,
                        "net_pnl": 0,
                        "total_realized_r": 0,
                        "risk_trades": 0,
                        "gross_net_profit": 0,
                        "gross_net_loss": 0,
                  }

            session = session_analytics[session_name]

            net_dollar_pnl = trade.get(
                  "net_dollar_pnl",
                  trade.get("dollar_pnl", 0)
            )

            net_result = trade.get(
                  "net_result",
                  calculate_net_result(net_dollar_pnl)
            )

            session["total_trades"] += 1
            session["net_pnl"] += net_dollar_pnl

            if net_result == "Win":
                  session["wins"] += 1
            elif net_result == "Loss":
                  session["losses"] += 1
            else:
                  session["breakevens"] += 1

            risk_amount = trade.get("risk_amount", 0)

            if risk_amount > 0:
                  gross_dollar_pnl = trade.get("dollar_pnl", 0)

                  realized_r = trade.get(
                        "realized_r",
                        calculate_realized_r(
                              gross_dollar_pnl,
                              risk_amount
                        )
                  )

                  session["total_realized_r"] += realized_r
                  session["risk_trades"] += 1

            if net_dollar_pnl > 0:
                  session["gross_net_profit"] += net_dollar_pnl
            elif net_dollar_pnl < 0:
                  session["gross_net_loss"] += abs(net_dollar_pnl)

      for session in session_analytics.values():
            session["net_win_rate"] = (
                  session["wins"]
                  / session["total_trades"]
                  * 100
            )

            if session["risk_trades"] > 0:
                  session["average_realized_r"] = (
                        session["total_realized_r"]
                        / session["risk_trades"]
                  )
            else:
                  session["average_realized_r"] = None

            if session["gross_net_loss"] > 0:
                  session["net_profit_factor"] = (
                        session["gross_net_profit"]
                        / session["gross_net_loss"]
                  )
            else:
                  session["net_profit_factor"] = None

      return session_analytics

def format_currency(value):
      if value < 0: 
            return f"-${abs(value):,.2f}"
      return f"${value:,.2f}"

def display_session_analytics(trades): 
      if len(trades) == 0:
            print("No trades to calculate session analytics.")
            return

      session_analytics = calculate_session_analysis(trades)

      print("\n" + "=" * 50)
      print("SESSION ANALYTICS")
      print("=" * 50)

      remaining_session_names = sorted(
            name for name in session_analytics if name not in SESSION_DISPLAY_ORDER
      )
      ordered_session_names = [
            name for name in list(SESSION_DISPLAY_ORDER) + remaining_session_names
            if name in session_analytics
      ]

      for session_name in ordered_session_names:
            session = session_analytics[session_name]

            heading = session_name.upper()
            if not heading.endswith("OVERLAP") and "SESSION" not in heading:
                  heading = f"{heading} SESSION"

            print()
            print("-" * 31)
            print(heading)
            print("-" * 31)
            print()

            print( 
                  f"{'Total Trades: ':<27}"
                  f"{session['total_trades']}"
            )

            print(
                  f"{'Net P/L: ':<27}"
                  f"{format_currency(session['net_pnl'])}"
            )

            print(
                  f"{'Net Win Rate: ':<27}"
                  f"{session['net_win_rate']:.2f}%"
            )

            if session["average_realized_r"] is None:
                  print(f"{'Average Realized R: ':<27}N/A")
            else:
                  print(
                        f"{'Average Realized R: ':<27}"
                        f"{session['average_realized_r']:.2f}R"
                  )
            if session["net_profit_factor"] is None:
                  print(
                        f"{'Net Profit Factor: ':<27}"
                        f"N/A (no losing trades)"
                  )
            else:
                  print(
                        f"{'Net Profit Factor: ':<27}"
                        f"{session['net_profit_factor']:.2f}"
                  )

      comparable_sessions = {
            name: data
            for name, data in session_analytics.items()
            if name != MAINTENANCE_SESSION_NAME
      }

      print("\n" + "=" * 50)
      print("SESSION COMPARISON")
      print("=" * 50)
      print()

      if comparable_sessions:
            best_session = max(
                  comparable_sessions,
                  key = lambda name: comparable_sessions[name]["net_pnl"]
            )

            worst_session = min(
                  comparable_sessions,
                  key = lambda name: comparable_sessions[name]["net_pnl"]
            )

            print(
                  f"{'Best Session':<27}"
                  f"{best_session} "
                  f"({format_currency(comparable_sessions[best_session]['net_pnl'])})"
            )

            print(
                  f"{'Worst Session':<27}"
                  f"{worst_session} "
                  f"({format_currency(comparable_sessions[worst_session]['net_pnl'])})"
            )
      else:
            print(f"{'Best Session':<27}N/A (no comparable sessions)")
            print(f"{'Worst Session':<27}N/A (no comparable sessions)")

def normalize_setup_name(setup):
      if setup is None:
            return "Unspecified"

      setup_text = " ".join(str(setup).strip().split())

      if setup_text == "":
            return "Unspecified"

      setup_aliases = {
            "ls": "Liquidity Sweep",
            "liquidity sweep": "Liquidity Sweep",
            "liquidity grab": "Liquidity Grab",

            "ob": "Order Block",
            "order block": "Order Block",

            "breaker": "Breaker Block",
            "breaker block": "Breaker Block",

            "fvg": "Fair Value Gap (FVG)",
            "fair value gap": "Fair Value Gap (FVG)",

            "ifvg": "Inverse Fair Value Gap (IFVG)",
            "inverse fair value gap": "Inverse Fair Value Gap (IFVG)",

            "bos": "Break of Structure (BOS)",
            "break of structure": "Break of Structure (BOS)",

            "choch": "Change of Character (CHOCH)",
            "change of character": "Change of Character (CHOCH)",

            "mss": "Market Structure Shift",
            "market structure shift": "Market Structure Shift",

            "cisd": "Change in State of Delivery (CISD)",
            "change in state of delivery": "Change in State of Delivery (CISD)",
            "change in the state of delivery": "Change in State of Delivery (CISD)",

            "smt": "SMT Divergence",
            "smt divergence": "SMT Divergence",

            "absorption": "Absorption",

            "delta divergence": "Delta Divergence",
            "delta div": "Delta Divergence",

            "cvd divergence": "Cumulative Volume Delta (CVD) Divergence",
            "cumulative volume delta divergence": "Cumulative Volume Delta (CVD) Divergence",

            "stacked imbalance": "Stacked Imbalances",
            "stacked imbalances": "Stacked Imbalances",

            "volume imbalance": "Volume Imbalance",
            "volume imbalances": "Volume Imbalance",

            "unfinished auction": "Unfinished Auction",
            "unfinished auctions": "Unfinished Auction",

            "exhaustion": "Exhaustion",

            "trapped buyers": "Trapped Buyers",
            "trapped sellers": "Trapped Sellers",
            "trapped traders": "Trapped Traders",

            "iceberg order": "Iceberg Order",
            "iceberg orders": "Iceberg Order",

            "large lot activity": "Large-Lot Activity",
            "large-lot activity": "Large-Lot Activity",

            "fib": "Fibonacci Retracement",
            "fibonacci": "Fibonacci Retracement",
            "fibonacci retracement": "Fibonacci Retracement",

            "supply and demand": "Supply and Demand",
            "supply/demand": "Supply and Demand",
            "supply & demand": "Supply and Demand",
            "s&d": "Supply and Demand",

            "equilibrium": "Equilibrium",
            "eq": "Equilibrium",

            "head and shoulders": "Head and Shoulders",
            "h&s": "Head and Shoulders",
            "double top": "Double Top",
            "double bottom": "Double Bottom",

            "power of 3": "Power of 3",
            "po3": "Power of 3",
            "power of three": "Power of 3",
            "amd": "Power of 3",

            "judas swing": "Judas Swing",
            "judas": "Judas Swing",

            "supply zone tapped": "Supply Zone Tapped Into",
            "supply zone tapped into": "Supply Zone Tapped Into",
            "supply zone was tapped": "Supply Zone Tapped Into",
            "supply zone was tapped into": "Supply Zone Tapped Into",
            "supply zone touch": "Supply Zone Tapped Into",
            "supply zone touched": "Supply Zone Tapped Into",

            "demand zone tapped": "Demand Zone Tapped Into",
            "demand zone tapped into": "Demand Zone Tapped Into",
            "demand zone was tapped": "Demand Zone Tapped Into",
            "demand zone was tapped into": "Demand Zone Tapped Into",
            "demand zone touch": "Demand Zone Tapped Into",
            "demand zone touched": "Demand Zone Tapped Into",

            "unspecified": "Unspecified",
      }

      canonical_setup_names = set(setup_aliases.values())
      canonical_setup_names.add("Unspecified")

      if setup_text in canonical_setup_names:
            return setup_text

      setup_key = setup_text.lower()

      return setup_aliases.get(
            setup_key,
            setup_text.title()
      )

def dedupe_case_insensitive(items):
      deduped = []
      seen = set()

      for item in items:
            key = item.lower()
            if key not in seen:
                  seen.add(key)
                  deduped.append(item)

      return deduped

def build_combination_key(names):
      unique_names = dedupe_case_insensitive(names)

      return " + ".join(sorted(unique_names, key=str.lower))

def split_setup_components(raw_text):
      if not raw_text:
            return []

      pieces = str(raw_text).replace("+", ",").split(",")

      return [piece.strip() for piece in pieces if piece.strip() != ""]

def _replace_case_insensitive(text, old, new):
      result = []
      lowered_text = text.lower()
      lowered_old = old.lower()
      start = 0

      while True:
            idx = lowered_text.find(lowered_old, start)
            if idx == -1:
                  result.append(text[start:])
                  break
            result.append(text[start:idx])
            result.append(new)
            start = idx + len(old)

      return "".join(result)

def split_strategy_methods(raw_text):
      if not raw_text:
            return []

      text = str(raw_text)

      # "Supply and Demand" / "Supply & Demand" are single strategy names that
      # happen to contain the word "and" / the character "&". Protect them
      # before splitting so they are never mistaken for a combinator joining
      # two different strategies.
      protected_token = "\x00SUPPLY_AND_DEMAND\x00"
      text = _replace_case_insensitive(text, "supply & demand", protected_token)
      text = _replace_case_insensitive(text, "supply and demand", protected_token)

      text = text.replace("+", ",")
      text = _replace_case_insensitive(text, " and ", ",")

      pieces = text.split(",")

      restored_pieces = []
      for piece in pieces:
            piece = piece.replace(protected_token, "Supply and Demand").strip()
            if piece != "":
                  restored_pieces.append(piece)

      return restored_pieces

SETUP_CONNECTOR_WORDS = {"and"}

def strip_setup_connector_words(text):
      words = str(text).split()

      while words and words[0].lower() in SETUP_CONNECTOR_WORDS:
            words = words[1:]

      while words and words[-1].lower() in SETUP_CONNECTOR_WORDS:
            words = words[:-1]

      return " ".join(words)

def get_setup_components(trade):
      stored_components = trade.get("setup_components")

      if isinstance(stored_components, list) and stored_components:
            raw_components = [
                  str(component) for component in stored_components
                  if str(component).strip() != ""
            ]
      else:
            raw_components = split_setup_components(trade.get("setup", ""))

      # A standalone leading/trailing "and" (e.g. from "FVG + and BOS") is a
      # stray connector word, not part of the component name. Strip it here,
      # by whole word only, before alias normalization - this leaves phrases
      # like "Supply and Demand" untouched since "and" sits in the middle.
      cleaned_components = [
            cleaned for cleaned in (
                  strip_setup_connector_words(component) for component in raw_components
            )
            if cleaned != ""
      ]

      normalized_components = dedupe_case_insensitive(
            [normalize_setup_name(component) for component in cleaned_components]
      )

      if not normalized_components:
            return ["Unspecified"]

      return normalized_components

def normalize_strategy_method(value):
      if value is None:
            return "Unspecified"

      value_text = " ".join(str(value).strip().split())

      if value_text == "":
            return "Unspecified"

      strategy_aliases = {
            "ict": "ICT",
            "inner circle trader": "ICT",

            "order flow": "Order Flow",
            "orderflow": "Order Flow",
            "footprint": "Order Flow",
            "footprint trading": "Order Flow",

            "supply and demand": "Supply & Demand",
            "supply & demand": "Supply & Demand",

            "price action": "Price Action",
            "pa": "Price Action",

            "opening range breakout": "Opening Range Breakout",
            "orb": "Opening Range Breakout",

            "trend following": "Trend Following",

            "unspecified": "Unspecified",
      }

      canonical_strategy_names = set(strategy_aliases.values())
      canonical_strategy_names.add("Unspecified")

      if value_text in canonical_strategy_names:
            return value_text

      value_key = value_text.lower()

      return strategy_aliases.get(
            value_key,
            value_text.title()
      )

def get_strategy_methods(trade):
      stored_methods = trade.get("strategy_methods")

      if isinstance(stored_methods, list) and stored_methods:
            raw_methods = [
                  str(method) for method in stored_methods
                  if str(method).strip() != ""
            ]
      else:
            raw_methods = split_strategy_methods(trade.get("strategy_method", ""))

      normalized_methods = dedupe_case_insensitive(
            [normalize_strategy_method(method) for method in raw_methods]
      )

      if not normalized_methods:
            return ["Unspecified"]

      return normalized_methods

def get_strategy_method(trade):
      return ", ".join(get_strategy_methods(trade))

def _new_setup_bucket():
      return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "breakevens": 0,
            "net_pnl": 0,
            "total_realized_r": 0,
            "risk_trades": 0,
            "gross_net_profit": 0,
            "gross_net_loss": 0,
      }

def _record_trade_in_setup_bucket(buckets, name, net_dollar_pnl, net_result, realized_r):
      if name not in buckets:
            buckets[name] = _new_setup_bucket()

      bucket = buckets[name]

      bucket["total_trades"] += 1
      bucket["net_pnl"] += net_dollar_pnl

      if net_result == "Win":
            bucket["wins"] += 1
      elif net_result == "Loss":
            bucket["losses"] += 1
      else:
            bucket["breakevens"] += 1

      if realized_r is not None:
            bucket["total_realized_r"] += realized_r
            bucket["risk_trades"] += 1

      if net_dollar_pnl > 0:
            bucket["gross_net_profit"] += net_dollar_pnl
      elif net_dollar_pnl < 0:
            bucket["gross_net_loss"] += abs(net_dollar_pnl)

def _finalize_setup_buckets(buckets):
      for bucket in buckets.values():
            bucket["net_win_rate"] = (
                  bucket["wins"]
                  / bucket["total_trades"]
                  * 100
            )

            if bucket["risk_trades"] > 0:
                  bucket["average_realized_r"] = (
                        bucket["total_realized_r"]
                        / bucket["risk_trades"]
                  )
            else:
                  bucket["average_realized_r"] = None

            if bucket["gross_net_loss"] > 0:
                  bucket["net_profit_factor"] = (
                        bucket["gross_net_profit"]
                        / bucket["gross_net_loss"]
                  )
            else:
                  bucket["net_profit_factor"] = None

def _get_trade_bucket_financials(trade):
      net_dollar_pnl = trade.get(
            "net_dollar_pnl",
            trade.get("dollar_pnl", 0)
      )

      net_result = trade.get(
            "net_result",
            calculate_net_result(net_dollar_pnl)
      )

      risk_amount = trade.get("risk_amount", 0)
      gross_dollar_pnl = trade.get("dollar_pnl", 0)

      realized_r = None

      if isinstance(risk_amount, (int, float)) and risk_amount > 0:
            if isinstance(gross_dollar_pnl, (int, float)):
                  realized_r = calculate_realized_r(
                        gross_dollar_pnl,
                        risk_amount
                  )
            else:
                  stored_realized_r = trade.get("realized_r")

                  if isinstance(stored_realized_r, (int, float)):
                        realized_r = stored_realized_r

      return net_dollar_pnl, net_result, realized_r

def calculate_setup_analysis(trades):
      component_analytics = {}
      combination_analytics = {}

      for trade in trades:
            components = get_setup_components(trade)
            combination_name = build_combination_key(components)

            net_dollar_pnl, net_result, realized_r = _get_trade_bucket_financials(trade)

            if len(components) >= 2:
                  _record_trade_in_setup_bucket(
                        combination_analytics,
                        combination_name,
                        net_dollar_pnl,
                        net_result,
                        realized_r
                  )

            for component in components:
                  _record_trade_in_setup_bucket(
                        component_analytics,
                        component,
                        net_dollar_pnl,
                        net_result,
                        realized_r
                  )

      _finalize_setup_buckets(component_analytics)
      _finalize_setup_buckets(combination_analytics)

      return component_analytics, combination_analytics

def calculate_strategy_method_analysis(trades):
      strategy_analytics = {}
      strategy_combination_analytics = {}

      for trade in trades:
            strategies = get_strategy_methods(trade)
            combination_name = build_combination_key(strategies)

            net_dollar_pnl, net_result, realized_r = _get_trade_bucket_financials(trade)

            if len(strategies) >= 2:
                  _record_trade_in_setup_bucket(
                        strategy_combination_analytics,
                        combination_name,
                        net_dollar_pnl,
                        net_result,
                        realized_r
                  )

            for strategy in strategies:
                  _record_trade_in_setup_bucket(
                        strategy_analytics,
                        strategy,
                        net_dollar_pnl,
                        net_result,
                        realized_r
                  )

      _finalize_setup_buckets(strategy_analytics)
      _finalize_setup_buckets(strategy_combination_analytics)

      return strategy_analytics, strategy_combination_analytics

def _display_setup_buckets(buckets):
      ordered_names = sorted(buckets, key=str.lower)

      for name in ordered_names:
            bucket = buckets[name]

            print()
            print("-" * 31)
            print(name.upper())
            print("-" * 31)
            print()

            print(
                  f"{'Total Trades: ':<27}"
                  f"{bucket['total_trades']}"
            )

            print(
                  f"{'Net P/L: ':<27}"
                  f"{format_currency(bucket['net_pnl'])}"
            )

            print(
                  f"{'Net Win Rate: ':<27}"
                  f"{bucket['net_win_rate']:.2f}%"
            )

            if bucket["average_realized_r"] is None:
                  print(f"{'Average Realized R: ':<27}N/A")
            else:
                  print(
                        f"{'Average Realized R: ':<27}"
                        f"{bucket['average_realized_r']:.2f}R"
                  )

            if bucket["net_profit_factor"] is None:
                  print(
                        f"{'Net Profit Factor: ':<27}"
                        f"N/A (no losing trades)"
                  )
            else:
                  print(
                        f"{'Net Profit Factor: ':<27}"
                        f"{bucket['net_profit_factor']:.2f}"
                  )

def display_setup_analytics(trades):
      if len(trades) == 0:
            print("No trades to calculate setup analytics.")
            return

      component_analytics, combination_analytics = calculate_setup_analysis(trades)

      print("\n" + "=" * 50)
      print("SETUP COMPONENT ANALYTICS")
      print("=" * 50)

      _display_setup_buckets(component_analytics)

      print("\n" + "=" * 50)
      print("EXACT MULTI-COMPONENT COMBINATION ANALYTICS")
      print("=" * 50)

      if combination_analytics:
            _display_setup_buckets(combination_analytics)
      else:
            print("\nNo trades contain two or more setup components yet.")

      comparable_components = {
            name: data
            for name, data in component_analytics.items()
            if name != "Unspecified"
      }

      print("\n" + "=" * 50)
      print("SETUP COMPONENT COMPARISON")
      print("=" * 50)
      print()

      if comparable_components:
            best_component = max(
                  comparable_components,
                  key=lambda name: comparable_components[name]["net_pnl"]
            )

            worst_component = min(
                  comparable_components,
                  key=lambda name: comparable_components[name]["net_pnl"]
            )

            print(
                  f"{'Best Component':<27}"
                  f"{best_component} "
                  f"({format_currency(comparable_components[best_component]['net_pnl'])})"
            )

            print(
                  f"{'Worst Component':<27}"
                  f"{worst_component} "
                  f"({format_currency(comparable_components[worst_component]['net_pnl'])})"
            )
      else:
            print(f"{'Best Component':<27}N/A (no specified components)")
            print(f"{'Worst Component':<27}N/A (no specified components)")

def display_strategy_method_analytics(trades):
      if len(trades) == 0:
            return

      strategy_analytics, strategy_combination_analytics = calculate_strategy_method_analysis(trades)

      print("\n" + "=" * 50)
      print("STRATEGY / METHOD ANALYTICS")
      print("=" * 50)

      _display_setup_buckets(strategy_analytics)

      print("\n" + "=" * 50)
      print("STRATEGY / METHOD COMBINATION ANALYTICS")
      print("=" * 50)

      if strategy_combination_analytics:
            _display_setup_buckets(strategy_combination_analytics)
      else:
            print("\nNo trades contain two or more strategies/methods yet.")

      comparable_strategies = {
            name: data
            for name, data in strategy_analytics.items()
            if name != "Unspecified"
      }

      print("\n" + "=" * 50)
      print("STRATEGY / METHOD COMPARISON")
      print("=" * 50)
      print()

      if comparable_strategies:
            best_strategy = max(
                  comparable_strategies,
                  key=lambda name: comparable_strategies[name]["net_pnl"]
            )

            worst_strategy = min(
                  comparable_strategies,
                  key=lambda name: comparable_strategies[name]["net_pnl"]
            )

            print(
                  f"{'Best Strategy/Method':<27}"
                  f"{best_strategy} "
                  f"({format_currency(comparable_strategies[best_strategy]['net_pnl'])})"
            )

            print(
                  f"{'Worst Strategy/Method':<27}"
                  f"{worst_strategy} "
                  f"({format_currency(comparable_strategies[worst_strategy]['net_pnl'])})"
            )
      else:
            print(f"{'Best Strategy/Method':<27}N/A (no specified strategies)")
            print(f"{'Worst Strategy/Method':<27}N/A (no specified strategies)")

def get_trade_datetime(trade): 
      trade_date_text = str(
            trade.get("trade_date", "")
      ).strip().replace(" ", "-")

      entry_time_text = str(
            trade.get("entry_time", "")
      ).strip()

      try: 
            return datetime.strptime(
                  f"{trade_date_text} {entry_time_text}",
                  "%Y-%m-%d %H:%M"
            )
      except (ValueError, TypeError):
            return None
      

def calculate_equity_drawdown_history(
      trades,
      starting_balance
):

      numbered_trades = [
            (
                  trade_number, 
                  trade,
                  get_trade_datetime(trade)
            )
            for trade_number, trade in enumerate(trades, start=1)
      ]

      numbered_trades.sort(
            key=lambda item: (
                  item[2] is None, 
                  item [2] or datetime.max,
                  item[0]
            )
      )
      
      running_balance = float(starting_balance)
      high_water_mark = float(starting_balance)
      high_water_mark_source = "Starting Balance"

      maximum_drawdown = 0.0
      maximum_drawdown_percentage = 0.0
      maximum_drawdown_peak = "Starting Balance"
      maximum_drawdown_trough = "N/A"

      history = []
      unspecified_datetime_trades = 0

      for (
            trade_number, 
            trade, 
            trade_datetime
      ) in numbered_trades:

            if trade_datetime is None:
                  unspecified_datetime_trades += 1
                  
            net_dollar_pnl = trade.get(
                  "net_dollar_pnl",
                  trade.get("dollar_pnl", 0)
            )

            try: 
                  net_dollar_pnl = float(
                        net_dollar_pnl
                  )
            except (ValueError, TypeError):
                  net_dollar_pnl = 0.0

            running_balance += net_dollar_pnl

            if running_balance > high_water_mark:
                  high_water_mark = running_balance
                  high_water_mark_source = (
                        f"Trade #{trade_number}"
                  )

            drawdown= (
                  high_water_mark
                  - running_balance
            )

            if high_water_mark > 0:
                  drawdown_percentage = (
                        drawdown
                        / high_water_mark
                        * 100
                  )
            else:
                  drawdown_percentage = 0.0

            history_row = {
                  "trade_number": trade_number,

                  "trade_date": (
                        trade_datetime.strftime(
                              "%Y-%m-%d"
                        )
                        if trade_datetime is not None
                        else "Unspecified"
                  ),

                  "entry_time": (
                        trade_datetime.strftime(
                              "%H:%M"
                        )
                        if trade_datetime is not None
                        else "N/A"
                  ),

                  "symbol": str(
                        trade.get(
                              "symbol",
                              "N/A"
                        )
                  ).upper(),

                  "net_dollar_pnl": (
                        net_dollar_pnl
                  ),

                  "equity": (
                        running_balance
                  ),

                  "high_water_mark": (
                        high_water_mark
                  ),

                  "drawdown": drawdown,

                  "drawdown_percentage": (
                        drawdown_percentage
                  ),
            }

            history.append(history_row)

            if drawdown > maximum_drawdown:
                  maximum_drawdown = drawdown

                  maximum_drawdown_peak = (
                        high_water_mark_source
                  )

                  maximum_drawdown_trough = (
                        f"Trade {trade_number}"
                  )

            if (
                  drawdown_percentage
                  > maximum_drawdown_percentage
            ):
                  maximum_drawdown_percentage = (
                        drawdown_percentage
                  )

      ending_balance = running_balance

      net_change = (
            ending_balance
            - float(starting_balance)
      )

      if history:
            current_drawdown = (
                  history[-1]["drawdown"]
            )

            current_drawdown_percentage = (
                  history[-1][
                        "drawdown_percentage"
                  ]
            )
      else:
            current_drawdown = 0.0
            current_drawdown_percentage = 0.0

      return {
            "history": history,

            "starting_balance": (
                  float(starting_balance)
            ),

            "ending_balance": ending_balance,

            "net_change": net_change,

            "high_water_mark": (
                  high_water_mark
            ),

            "current_drawdown": (
                  current_drawdown
            ),

            "current_drawdown_percentage": (
                  current_drawdown_percentage
            ),

            "maximum_drawdown": (
                  maximum_drawdown
            ),

            "maximum_drawdown_percentage": (
                  maximum_drawdown_percentage
            ),

            "maximum_drawdown_peak": (
                  maximum_drawdown_peak
            ),

            "maximum_drawdown_trough": (
                  maximum_drawdown_trough
            ),

            "unspecified_datetime_trades": (
                  unspecified_datetime_trades
            ),

      }

def format_drawdown(value):
      if value > 0:
            return f"-${(value):,.2f}"

      return "$0.00"

def format_drawdown_percentage(value):
      if value > 0:
            return f"-{value:.2f}%"

      return "0.00%"


def display_equity_drawdown_history(
      trades,
      account
): 
      if account is None: 
            print(
                  "\nNo account has been created yet. "
                  "Please create an account through "
                  "Account Status first. "
            )
            return

      equity_data = (
            calculate_equity_drawdown_history(
                  trades,
                  account["starting_balance"]
            )
      )

      table_width = 95

      print("\n" + "=" * table_width)
      print("EQUITY & DRAWDOWN HISTORY".center(table_width))
      print("=" * table_width)
      print()

      print(
            f"{'#':<4}"
            f"{'Date':<12}"
            f"{'Time':<7}"
            f"{'Symbol':<9}"
            f"{'Net P/L':>12}"
            f"{'Equity':>14}"
            f"{'HWM':>14}"
            f"{'Drawdown':>14}"
            f"{'DD %':>9}"
      )

      print("-" * table_width)

      if not equity_data["history"]:
            print("No trades to display. ")

      else:  
            for row in equity_data["history"]:
                  print(
                        f"{row['trade_number']:<4}"
                        f"{row['trade_date']:<12}"
                        f"{row['entry_time']:<7}"
                        f"{row['symbol']:<9}"
                        f"{format_currency(row['net_dollar_pnl']):>12}"
                        f"{format_currency(row['equity']):>14}"
                        f"{format_currency(row['high_water_mark']):>14}"
                        f"{format_drawdown(row['drawdown']):>14}"
                        f"{format_drawdown_percentage(row['drawdown_percentage']):>9}"
                  )

      print("\n" + "=" * 50)
      print("EQUITY & DRAWDOWN SUMMARY".center(50))
      print("=" * 50)
      print()

      print(
            f"{'Starting Balance: ':<30}"
            f"{format_currency(equity_data['starting_balance'])}"
      )

      print(
            f"{'Ending Balance: ':<30}"
            f"{format_currency(equity_data['ending_balance'])}"
      )

      print(
            f"{'Net Change: ':<30}"
            f"{format_currency(equity_data['net_change'])}"
      )

      print(
            f"{'High Water Mark: ':<30}"
            f"{format_currency(equity_data['high_water_mark'])}"
      )

      print(
            f"{'Current Drawdown: ':<30}"
            f"{format_drawdown(equity_data['current_drawdown'])}"
      )

      print(
            f"{'Current Drawdown Percentage: ':<30}"
            f"{format_drawdown_percentage(equity_data['current_drawdown_percentage'])}"
      )

      print(
            f"{'Maximum Drawdown: ':<30}"
            f"{format_drawdown(equity_data['maximum_drawdown'])}"
      )

      print(
            f"{'Maximum Drawdown Percentage: ':<30}"
            f"{format_drawdown_percentage(equity_data['maximum_drawdown_percentage'])}"
      )

      print(
            f"{'Maximum Drawdown Peak: ':<30}"
            f"{equity_data['maximum_drawdown_peak']}"
      )

      print(
            f"{'Maximum Drawdown Trough: ':<30}"
            f"{equity_data['maximum_drawdown_trough']}"
      )

      if (
            equity_data[
               "unspecified_datetime_trades"
            ]
            > 0
      ):

            print()

            print(
                  "Warning: "
                  f"{equity_data['unspecified_datetime_trades']} "
                  "trade(s) have unspecified or invalid "
                  "date/time and were placed at the end "
                  "in original order. "
            )

      print()

      print(
            "Note: drawdown is calculated from "
            "closed-trade equity after commission,"
            "not intratrade floating P/L."
      )

def calculate_duration(entry_time, exit_time):
      entry_datetime = datetime.strptime(entry_time, "%H:%M")
      exit_datetime = datetime.strptime(exit_time, "%H:%M")

      if exit_datetime < entry_datetime:
            exit_datetime = exit_datetime + timedelta(days=1)

      duration = exit_datetime - entry_datetime
      duration_minutes = int(duration.total_seconds() / 60)

      return duration_minutes

def get_finite_number(
      value,
      field_name,
      minimum=None,
      minimum_is_strict=False,
):
      if isinstance(value, bool):
            raise ValueError(
                  f"{field_name} must be a number. "
            )

      try:
            number = float(value)
      
      except (TypeError, ValueError):
            raise ValueError(
                  f"{field_name} must be a number. "
            )

      if not math.isfinite(number):
            raise ValueError(
                  f"{field_name} must be a finite "
                  "number. "
            )

      if minimum is not None:
            if (
                  minimum_is_strict
                  and number <= minimum
            ):
                  raise ValueError(
                        f"{field_name} must be "
                        f"greater than {minimum}. "
                  )

            if (
                  not minimum_is_strict
                  and number < minimum 
            ):

                  raise ValueError(
                        f"{field_name} must be "
                        f"greater than or equal to "
                        f"{minimum}. "
                  )

      return number

def get_positive_integer(
      value,
      field_name
):

      if isinstance(value, bool):
            raise ValueError(
                  f"{field_name} must be a whole "
                  "number greater than 0."
            )

      try:
            number = float(value)

      except (TypeError, ValueError):
            raise ValueError(
                  f"{field_name} must be a whole "
                  "number greater than 0."
            )

      if (
            not math.isfinite(number)
            or not number.is_integer()
            or number <= 0
      ):
            raise ValueError(
                  f"{field_name} must be a whole "
                  "number greater than 0."
            )

      return int(number)

def normalize_date_value(value):
      date_text = (
            str(value)
            .strip()
            .replace (" ", "-")
      )

      parsed_date = datetime.strptime(
            date_text, 
            "%Y-%m-%d"
      )

      return parsed_date.strftime(
            "%Y-%m-%d"
      )

def normalize_time_value(value):
      time_text = str(value).strip()

      parsed_time = datetime.strptime(
            time_text,
            "%H:%M"
      )

      return parsed_time.strftime(
            "%H:%M"
      )

def validate_and_normalize_trade(trade):
      if not isinstance(trade, dict):
            return None, [
                  "Trade record must be a "
                  "JSON object."
            ]
      
      errors = []

      symbol = str(
            trade.get("symbol", "")
      ).strip().lower()
      
      if symbol == "":
            errors.append(
                  "Symbol cannot be blank."
            )

      direction = str(
            trade.get("direction", "")
      ).strip().lower()

      if direction not in valid_directions: 
            errors.append(
                  "Direction must be long or short."
            )

      numeric_values = {}

      numeric_rules = (
            (
                  "entry",
                  "Entry price",
                  0,
                  True
            ),
            (
                  "exit",
                  "Exit price",
                  0,
                  True
            ),
            (
                  "point_value",
                  "Point value",
                  0,
                  True
            ),
            (
                  "risk_amount",
                  "Risk amount",
                  0,
                  True
            ),
            (
                  "commission",
                  "Commission",
                  0,
                  False
            ),
      )

      for (
            field_name,
            display_name,
            minimum,
            minimum_is_strict
      ) in numeric_rules:
            try:
                  numeric_values[field_name] = get_finite_number(
                              trade.get(
                                    field_name
                              ),
                              display_name,
                              minimum,
                              minimum_is_strict
                        )
            except ValueError as error:
                  errors.append(str(error))
            
      try:
            contracts = get_positive_integer(
                  trade.get("contracts"),
                  "Contracts"
            )

      except ValueError as error:
            errors.append(str(error))
            contracts = None

      try: 
            trade_date = normalize_date_value(
                  trade.get(
                        "trade_date",
                        ""
                  )
            )

      except (TypeError, ValueError):
            errors.append(
                  "Trade date must be in YYYY-MM-DD "
                  "format."
            )
            trade_date = None
      
      try: 
            entry_time = normalize_time_value(
                  trade.get(
                        "entry_time",
                        ""
                  )
            )
      
      except (TypeError, ValueError):
            errors.append(
                  "Entry time must use 24-hour format "
                  "HH:MM 24-hour format."
            )
            entry_time = None

      try:
            exit_time = normalize_time_value(
                  trade.get(
                        "exit_time",
                        ""
                  )
            )
      
      except (TypeError, ValueError):
            errors.append(
                  "Exit time must use 24-hour format "
                  "HH:MM."
            )
            exit_time = None
      
      if errors: 
            return None, errors
      
      points_pnl = calculate_points_pnl(
            direction,
            numeric_values["entry"],
            numeric_values["exit"],
      )

      dollar_pnl = calculate_dollar_pnl(
            points_pnl,
            numeric_values["point_value"],
            contracts
      )

      net_dollar_pnl = calculate_net_dollar_pnl(
            dollar_pnl,
            numeric_values["commission"]
      )

      realized_r = calculate_realized_r(
            dollar_pnl,
            numeric_values["risk_amount"]
      )

      calculated_values = (
            points_pnl,
            dollar_pnl,
            net_dollar_pnl,
            realized_r
      )

      if not all(
            math.isfinite(value)
            for value in calculated_values
      ):
            return None, [
                  "Calculated trade values are too "
                  "large to store safely."
            ]

      strategy_methods = (
            get_strategy_methods(trade)
      )

      if strategy_methods == ["Unspecified"]:
            strategy_methods = []
      
      setup_components = (
            get_setup_components(trade)
      )

      if setup_components == ["Unspecified"]:
            setup_components = []

      normalized_trade = dict(trade)

      normalized_trade.update({
            "symbol": symbol,
            "direction": direction,

            "entry": (
                  numeric_values["entry"]
            ), 

            "exit": (
                  numeric_values["exit"]
            ), 

            "contracts": contracts,

            "point_value": (
                  numeric_values["point_value"]
            ),

            "points_pnl": points_pnl,
            "dollar_pnl": dollar_pnl,

            "commission": (
                  numeric_values["commission"]
            ),

            "net_dollar_pnl": (
                  net_dollar_pnl
            ),

            "result": calculate_result(points_pnl),
            "net_result": calculate_net_result(net_dollar_pnl),

            "risk_amount": (
                  numeric_values["risk_amount"]
            ),

            "realized_r": realized_r,
            "trade_date": trade_date,
            "entry_time": entry_time,
            "exit_time": exit_time,

            "duration": calculate_duration(
                  entry_time,
                  exit_time
            ),

            "strategy_methods": (
                  strategy_methods
            ), 

            "setup_components": (
                  setup_components
            ), 

            "session": (
                  determine_session(entry_time)
                  or "Unspecified"
            ), 

            "notes": str(
                  trade.get("notes", "")
                  if trade.get("notes") is not None
                  else ""
            ).strip(),

            "mistake": str(
                  trade.get("mistake", "")
                  if trade.get("mistake") 
                  is not None
                  else ""
            ).strip(), 
      })

      return normalized_trade, []

def validate_and_normalize_account(
      account
): 
      if not isinstance(account, dict):
            return None, [
                  "Account data must be a "
                  "JSON object."
            ]

      errors = []

      account_name = str(
            account.get("name", "")
      ).strip()

      if account_name == "": 
            errors.append(
                  "Account name cannot be blank."
            )

      account_type_text = str(
            account.get("type", "")
      ).strip().lower()

      account_type_lookup = {
            value.lower(): value
            for value in VALID_ACCOUNT_TYPES
      }

      account_type = (
            account_type_lookup.get(
                  account_type_text
            )
      )

      if account_type is None:
            errors.append(
                  "Account type must be Personal, "
                  "Evaluation, or Funded."
            )

      try:
            starting_balance = (
                  get_finite_number(
                        account.get(
                              "starting_balance"
                        ),
                        "Starting balance",
                        0
                  )
            )

      except ValueError as error:
            errors.append(str(error))
            starting_balance = None

      if errors:
            return None, errors

      try:
            high_water_mark = (
                  get_finite_number(
                        account.get(
                              "high_water_mark",
                              starting_balance
                        ),
                        "High water mark",
                        starting_balance
                  )
            )

      except ValueError:
            high_water_mark = (
                  starting_balance
            )

      normalized_account = dict(account)

      normalized_account.update({
            "name": account_name,
            "type": account_type,

            "starting_balance": (
                  starting_balance
            ),

            "high_water_mark": (
                  high_water_mark
            )
      })

      return normalized_account, []

def prompt_required_text(
            prompt,
            field_name
): 
      while True:
            value = input(prompt).strip()

            if value != "":
                  return value

            print(
                  f"{field_name} cannot be blank. "
            )

def prompt_choice(
      prompt, 
      valid_choices, 
      error_message, 
      default=None
):
      while True: 
            value = (
                  input(prompt)
                  .strip()
                  .lower()
            )

            if (
                  value == ""
                  and default is not None
            ): 
                  return default
            
            if value in valid_choices:
                  return value

            print (error_message)

def prompt_finite_number(
      prompt,
      field_name,
      minimum = None, 
      minimum_is_strict = False, 
      default = None
):

      while True: 
            value = input(prompt).strip()

            if (
                  value == ""
                  and default is not None
            ): 
                  return default
            try: 
                  return get_finite_number(
                        value,
                        field_name,
                        minimum,
                        minimum_is_strict
                  )
            except ValueError as error:
                  print(error)

def prompt_positive_integer(
            prompt, 
            field_name,
            default = None
): 
      
      while True: 
            value = input(prompt).strip()

            if (
                  value == ""
                  and default is not None
            ): 
                  return default
            try: 
                  return get_positive_integer(
                        value,
                        field_name
                  )
            except ValueError as error:
                  print(error)
            
def prompt_date(
      prompt, 
      default = None
): 
      while True: 
            value = input(prompt).strip()

            if (
                  value == ""
                  and default is not None
            ): 
                  return default

            try: 
                  return normalize_date_value(
                        value
                  )

            except (TypeError, ValueError):
                  print(
                        "Invalid date. Please use "
                        "YYYY-MM-DD format."
                  )

def prompt_time(
      prompt,
      default = None
):

      while True: 
            value = input(prompt).strip()

            if (
                  value == ""
                  and default is not None
            ): 
                  return default

            try:
                  return normalize_time_value(
                        value
                  )

            except (TypeError, ValueError):
                  print(
                        "Invalid time. Please use "
                        "24-hour HH:MM format."
                  )

def get_trade_weekday(trade):
      trade_date_text = str(
            trade.get("trade_date", "")
      ).strip().replace(" ", "-")
      
      try: 
            trade_date = datetime.strptime(
                  trade_date_text,
                  "%Y-%m-%d"
            )
      except (ValueError, TypeError):
            return "Unspecified"
      
      return trade_date.strftime("%A")

def get_entry_hour_range(trade):
      entry_time_text = str(
            trade.get("entry_time", "")
      ).strip()

      try:
            entry_time = datetime.strptime(
                  entry_time_text,
                  "%H:%M"
            )
      except (ValueError, TypeError):
            return "Unspecified" 
      
      hour = entry_time.hour

      return f"{hour:02d}:00 - {hour:02d}:59"

def get_duration_range(trade): 
      duration = trade.get("duration")

      if isinstance(duration, bool):
            return "Unspecified"
      
      try:
            duration = float(duration)
      except (ValueError, TypeError):
            return "Unspecified"
      
      if duration < 0:
            return "Unspecified"
      elif duration <= 15:
            return "0 - 15 minutes"
      elif duration <= 30:
            return "16 - 30 minutes"
      elif duration <= 60:
            return "31 - 60 minutes"
      elif duration <= 120:
            return "61 - 120 minutes"
      elif duration <= 240:
            return "121 - 240 minutes"
      else:
            return "241+ minutes"
      
def calculate_time_based_analytics(trades):
      weekday_analytics = {}
      entry_hour_analytics = {}
      duration_analytics = {}

      for trade in trades:
            net_dollar_pnl, net_result, realized_r = (
                  _get_trade_bucket_financials(trade)
            )
            time_categories = (
                  (
                        weekday_analytics,
                        get_trade_weekday(trade)
                  ), 
                  (
                        entry_hour_analytics,
                        get_entry_hour_range(trade)
                  ), 
                  (
                        duration_analytics,
                        get_duration_range(trade)
                  )
            )

            for analytics, category_name in time_categories:
                  _record_trade_in_setup_bucket(
                        analytics,
                        category_name,
                        net_dollar_pnl,
                        net_result,
                        realized_r
                  )

      _finalize_setup_buckets(weekday_analytics)
      _finalize_setup_buckets(entry_hour_analytics)
      _finalize_setup_buckets(duration_analytics)

      
      return (
            weekday_analytics,
            entry_hour_analytics,
            duration_analytics                                                            
      )

def _display_time_buckets(buckets, display_order=None): 
      if display_order is None:
            ordered_names = sorted(
                  buckets,
                  key=str.lower
            )
      else:
            remaining_names = sorted(
                  name
                  for name in buckets
                  if name not in display_order
            )

            ordered_names = [
                  name
                  for name in list(display_order) + remaining_names
                  if name in buckets
            ]

      for name in ordered_names:
            _display_setup_buckets(
                  {name: buckets[name]}
            )

def _display_time_comparison(label, buckets): 
      comparable_buckets = {
            name: data
            for name, data in buckets.items()
            if name != "Unspecified"
      }

      if not comparable_buckets:
            print(
                  f"{'Best ' + label:<27}"
                  f"N/A"
            )
            return
      best_name = max(
            comparable_buckets,
            key=lambda name: comparable_buckets[name]["net_pnl"]
      )

      worst_name = min(
            comparable_buckets,
            key=lambda name: comparable_buckets[name]["net_pnl"]
      )

      best = comparable_buckets[best_name]
      worst = comparable_buckets[worst_name]

      best_trade_word = (
            "trade"
            if best["total_trades"] == 1
            else "trades"
      )

      worst_trade_word = (
            "trade"
            if worst["total_trades"] == 1
            else "trades"
      )

      print(
            f"{'Best ' + label:<27}"
            f"{best_name} "
            f"({format_currency(best['net_pnl'])}, "
            f"{best['total_trades']} {best_trade_word})"
      )

      print( 
            f"{'Worst ' + label:<27}"
            f"{worst_name} "
            f"({format_currency(worst['net_pnl'])}, "
            f"{worst['total_trades']} {worst_trade_word})"
      )

def display_time_based_analytics(trades):
      if len(trades) == 0:
            print(
                  "No trades to calculate " 
                  "time-based analytics."
            )
            return
      (
            weekday_analytics,
            entry_hour_analytics,
            duration_analytics,
      ) = calculate_time_based_analytics(trades)

      print("\n" + "=" * 50)
      print("DAY-OF-WEEK ANALYTICS")
      print("=" * 50)

      _display_time_buckets(
            weekday_analytics,
            WEEKLY_DISPLAY_ORDER
      )

      print("\n" + "=" * 50)
      print("ENTRY-HOUR ANALYTICS")
      print("=" * 50)

      _display_time_buckets(
            entry_hour_analytics,
      )

      print("\n" + "=" * 50)
      print("TRADE-DURATION ANALYTICS")
      print("=" * 50)

      _display_time_buckets(
            duration_analytics,
            DURATION_DISPLAY_ORDER
      )

      print("\n" + "=" * 50)
      print("TIME-BASED COMPARISONS")
      print("=" * 50)
      print()

      _display_time_comparison(
            "Weekday",
            weekday_analytics
      )

      _display_time_comparison(
            "Entry Hour",
            entry_hour_analytics
      )

      _display_time_comparison(
            "Trade Duration",
            duration_analytics
      )

      print()
      print(
            "Note: comparisons are ranked by net P/L. Always consider the trade count."
      )

def get_optional_date(prompt): 
      while True:
            date_input = input(prompt).strip().replace(" ", "-")
      
            if date_input == "":
                  return None

            try:
                  parsed_date = datetime.strptime(
                        date_input, 
                        "%Y-%m-%d"
                  ).date()

                  return parsed_date
            
            except ValueError:
                  print("Invalid date. Please use YYYY-MM-DD format.")

def trade_is_in_date_range(trade, start_date, end_date):
      if start_date is None and end_date is None:
            return True
      
      trade_date_text = (
            trade.get("trade_date", "")
            .strip()
            .replace(" ", "-")
      )

      try:
            trade_date = datetime.strptime(
                  trade_date_text, 
                  "%Y-%m-%d"
            ).date()

      except ValueError:
            return False
      
      if start_date is not None and trade_date < start_date:
            return False
      
      if end_date is not None and trade_date > end_date:
            return False
      
      return True 

trades = load_trades()
account = load_account()

while True:
      show_menu()
      choice = input("Choose an option: ").strip()

      if choice == "1":
            if account is None: 
                  print("\nNo account has been created yet. Please create an account first.")
            
                  account_name = (
                        prompt_required_text(
                              "Enter account name: ",
                              "Account name"
                        )
                  )
            

                  print("\nAccount Types")
                  print("1. Personal")
                  print("2. Evaluation")
                  print("3. Funded")

                  account_type_choice = (
                        prompt_choice(
                              "Choose account type (1-3): ",
                              ["1", "2", "3"],
                              "Invalid account type."
                        )
                  )

                  account_type = {
                        "1": "Personal",
                        "2": "Evaluation",
                        "3": "Funded",
                  }[account_type_choice]

                  starting_balance = (
                        prompt_finite_number(
                              (
                                    "Enter starting "
                                    "balance: $"
                              ), 
                                    "Starting balance", 
                                    minimum=0,
                        )
                  )

                  new_account = {
                        "name": account_name,
                        "type": account_type,
                        "starting_balance": starting_balance,
                        "high_water_mark": starting_balance,
                  }

                  if save_account(new_account):
                        account = new_account

                        print(
                              f"Account '{account_name}' "
                              "created successfully."
                        )

                  else:
                        print(
                              "Account was not created "
                              "because it could not be "
                              "saved."
                        )
                        continue

            starting_balance = account.get("starting_balance", 0)

            equity_data = calculate_equity_drawdown_history(
                  trades,
                  starting_balance
            )

            current_balance = equity_data["ending_balance"]
            net_profit = equity_data["net_change"]

            growth_percentage = (
                  net_profit
                  / starting_balance
                  * 100
                  if starting_balance != 0
                  else 0
            )

            high_water_mark = equity_data["high_water_mark"]

            if (
                  account.get("high_water_mark") 
                  != high_water_mark
            ): 
                  previous_high_water_mark = (
                        account.get(
                              "high_water_mark"
                        )
                  )
                  
                  account["high_water_mark"] = (
                        high_water_mark
                  )

                  if not save_account(account):
                        account[
                              "high_water_mark"
                        ] = previous_high_water_mark


            drawdown = equity_data["current_drawdown"]
            drawdown_percentage = equity_data["current_drawdown_percentage"]

            print("\n=========================")
            print("ACCOUNT STATUS")
            print("=========================")
            print(f"Account Name: {account['name']}")
            print(f"Account Type: {account['type']}")
            print(f"Starting Balance: ${starting_balance:,.2f}")
            print(f"Current Balance: ${current_balance:,.2f}")
            print(f"High Water Mark: ${high_water_mark:,.2f}")

            if net_profit > 0:
                  print(f"Net Profit: ${net_profit:,.2f}")
                  print(f"Growth: {growth_percentage:.2f}%")
            elif net_profit < 0:
                  print(f"Net Loss: -${abs(net_profit):,.2f}")
                  print(f"Growth: {growth_percentage:.2f}%")
            else:
                  print("Net P/L: $0.00")
                  print("Growth: 0.00%")

            print(f"Drawdown: {format_drawdown(drawdown)}")
            print(f"Drawdown Percentage: {format_drawdown_percentage(drawdown_percentage)}")

            print(
                  "Maximum Drawdown: "
                  f"{format_drawdown(equity_data['maximum_drawdown'])}"
            )

            print(
                  "Maximum Drawdown Percentage: "
                  f"{format_drawdown_percentage(equity_data['maximum_drawdown_percentage'])}"
            )

      elif choice == "2":
            if account is None:
                  print("\nNo account has been created yet. Please create an account first.")
                  continue
                  
            print("\nEDIT ACCOUNT")
            print("Press Enter to keep current value.")

            new_account_name = input(
                  f"Account Name (current: {account['name']}): " 
            ).strip()

            if new_account_name == "":
                  new_account_name = account["name"]

            print(f"\nCurrent account type: {account['type']}")  
            print("1. Personal")
            print("2. Evaluation")
            print("3. Funded")
            print("Press Enter to keep current account type.")

            account_type_choice = (
                  prompt_choice(
                        "Chose new account type: ", 
                        ("1", "2", "3"),
                        "Invalid account type.",
                        default=""
                  )
            )

            if account_type_choice == "":
                  new_account_type = (
                        account ["type"]
                  )
            else: 
                  new_account_type = {
                        "1": "Personal",
                        "2": "Evaluation",
                        "3": "Funded"
                  }[account_type_choice]

            new_starting_balance = (
                  prompt_finite_number(
                        (
                              "Starting Balance "
                              f"(current: "
                              f"${account['starting_balance']:,.2f}"
                              "): $"
                        ), 
                        "Starting balance",
                        minimum=0,
                        default=(
                              account[
                                    "starting_balance"
                              ]
                        )
                  )
            )
      
            equity_data = (
                  calculate_equity_drawdown_history(
                        trades,
                        new_starting_balance
                  )
            )

            updated_account = {
                  **account,

                  "name": new_account_name,
                  "type": new_account_type,
                  "starting_balance": new_starting_balance,

                  "high_water_mark": (
                        equity_data[
                              "high_water_mark"
                        ]
                  ),
            }

            if save_account(updated_account):
                  account = updated_account

                  print(
                        "Account updated successfully."
                  )

            else: 
                  print(
                        "Account changes were not "
                        "applied because they could "
                        "not be saved."
                  )

      elif choice == "3":
            symbol = prompt_required_text(
                  "Enter symbol: ",
                  "Symbol"
            ).lower()

            direction = prompt_choice(
                  "Enter direction (long/short): ",
                  valid_directions,
                  "Direction must be long or short."
            )

            entry = prompt_finite_number(
                  "Enter entry price: $",
                  "Entry price",
                  minimum=0,
                  minimum_is_strict=True
            )

            exit_price = prompt_finite_number(
                  "Enter exit price: $",
                  "Exit price",
                  minimum=0,
                  minimum_is_strict=True
            )

            contracts = prompt_positive_integer(
                  "Enter number of contracts: ",
                  "Contracts"
            )

            point_value = prompt_finite_number(
                  "Enter point value: $",
                  "Point value",
                  minimum=0,
                  minimum_is_strict=True
            )

            risk_amount = prompt_finite_number(
                  "Enter risk amount: $",
                  "Risk amount",
                  minimum=0,
                  minimum_is_strict=True
            )

            commission = prompt_finite_number(
                  "Enter total commission: $",
                  "Commission",
                  minimum=0,
            )

            trade_date = prompt_date(
                  "Enter trade date (YYYY-MM-DD): "
            )

            entry_time = prompt_time(
                  "Enter entry time (HH:MM) "
            )

            exit_time = prompt_time(
                  "Enter exit time (HH:MM) "
            )

            duration = calculate_duration(
                  entry_time,
                  exit_time
            )

            strategy_method_input = input("Enter Strategy / Method (separate multiple with commas or +): ").strip()
            strategy_methods = dedupe_case_insensitive(split_strategy_methods(strategy_method_input))
            print(f"Strategy / Method recorded: {', '.join(get_strategy_methods({'strategy_methods': strategy_methods}))}")

            setup_input = input("Enter Setup Components (separate with commas or +): ").strip()
            setup_components = dedupe_case_insensitive(split_setup_components(setup_input))
            print(f"Setup Components recorded: {', '.join(get_setup_components({'setup_components': setup_components}))}")

            session = determine_session(entry_time)
            if session is None:
                  session = "Unspecified"
            print(f"Session automatically assigned: {session}")

            notes = input("Enter notes: ").strip()
            mistake = input("Enter mistake: ").strip()

            points_pnl = calculate_points_pnl(
                  direction, 
                  entry, 
                  exit_price
            )

            dollar_pnl = calculate_dollar_pnl(
                  points_pnl,
                  point_value,
                  contracts
            )

            net_dollar_pnl = calculate_net_dollar_pnl(
                  dollar_pnl, 
                  commission
            )
            
            realized_r = calculate_realized_r(
                  dollar_pnl,
                  risk_amount
            )

            if not all(
                  math.isfinite(value)
                  for value in (
                        points_pnl,
                        dollar_pnl,
                        net_dollar_pnl,
                        realized_r
                  )
            ):
                  print(
                        "Calculated trade values are too "
                        "large to store safely."
                  )

                  continue

            result = calculate_result(points_pnl)
            net_result = calculate_net_result(net_dollar_pnl)

            trade = {
                  "symbol": symbol,
                  "direction": direction,

                  "entry": entry,
                  "exit": exit_price,

                  "contracts": contracts,
                  "point_value": point_value,

                  "points_pnl": points_pnl,
                  "dollar_pnl": dollar_pnl,
                  "commission": commission,
                  "net_dollar_pnl": net_dollar_pnl,
                  "result": result,
                  "net_result": net_result,

                  "risk_amount": risk_amount,
                  "realized_r": realized_r,

                  "trade_date": trade_date,
                  "entry_time": entry_time,
                  "exit_time": exit_time,
                  "duration": duration,

                  "strategy_methods": strategy_methods,
                  "setup_components": setup_components,
                  "session": session,
                  "notes": notes,
                  "mistake": mistake
            }
            trades.append(trade)
           
            if save_trades(trades): 
                  print("Trade added successfully.")

            else: 
                  trades.pop()

                  print(
                        "Trade was not added because it "
                        "could not be saved."
                  )

      elif choice == "4":
            if len(trades) == 0:
                  print("No trades yet.")
            else:
                  print(f"\nTrades ({len(trades)} total):")
                  for i in range(len(trades)):
                        trade = trades[i]

                        net_pnl = trade.get(
                              "net_dollar_pnl",
                              trade.get("dollar_pnl", 0)
                        )

                        print(
                              f"  {i + 1}. {trade['symbol'].upper()} | "
                              f"{trade.get('trade_date', 'N/A').replace('-', ' ')} | "
                              f"{trade['direction']} | "
                              f"{trade.get('net_result', trade.get('result', 'N/A'))} | "
                              f"{trade['points_pnl']:,.2f} pts | "
                              f"Net: ${net_pnl:,.2f}"
                        )

                  view_input = input("\nEnter a trade number for full details, or press Enter to go back: ").strip()

                  if view_input == "":
                        continue

                  try:
                        view_number = int(view_input)
                  except ValueError:
                        print("Invalid trade number.")
                        continue

                  view_index = view_number - 1

                  if 0 <= view_index < len(trades):
                        trade = trades[view_index]
                        print(f"\nTrade #{view_number}")
                        print(f"Symbol: {trade['symbol']}")
                        print(f"Direction: {trade['direction']}")
                        print(f"Date: {trade.get('trade_date', 'N/A').replace('-', ' ')}")

                        print(f"Entry: {trade['entry']}")
                        print(f"Exit: {trade['exit']}")
                        print(f"Contracts: {trade.get('contracts', 'N/A')}")

                        point_value = trade.get("point_value")
                        if point_value is None:
                              print("Point Value: N/A")
                        else:
                              print(f"Point Value: ${point_value:,.2f}")

                        print(f"Points P/L: {trade['points_pnl']:,.2f} pts")
                        print(
                              f"Gross Dollar P/L: "
                              f"${trade.get('dollar_pnl', 0):,.2f}"
                         )
                        print(
                              f"Commission: "
                              f"${trade.get('commission', 0):,.2f}"
                        )
                        print(
                              f"Net Dollar P/L: "
                              f"${trade.get('net_dollar_pnl', trade.get('dollar_pnl', 0)):,.2f}"
                        )
                        
                        print(f"Result: {trade['result']}")
                        print(
                              f"Net Result: "
                              f"{trade.get('net_result', trade.get('result', 'N/A'))}"
                        )

                        print(f"Risk Amount: ${trade.get('risk_amount', 0):,.2f}")
                        print(f"Realized R: {trade.get('realized_r', 0):.2f}R")

                        print(f"Entry Time: {trade.get('entry_time', 'N/A')}")
                        print(f"Exit Time: {trade.get('exit_time', 'N/A')}")
                        print(f"Duration: {trade.get('duration', 'N/A')} minutes")

                        print(f"Strategy / Method: {get_strategy_method(trade)}")
                        print(f"Setup Components: {', '.join(get_setup_components(trade))}")
                        print(f"Session: {trade.get('session', 'N/A')}")
                        print(f"Notes: {trade.get('notes', 'N/A')}")
                        print(f"Mistake: {trade.get('mistake', 'N/A')}")
                  else:
                        print("Invalid trade number.")

      elif choice == "5":
            if len(trades) == 0:
                  print("No trades to edit.")
                  continue

            for i in range(len(trades)):
                  trade = trades[i]
                  print(f"{i + 1}. {trade['symbol']} {trade['direction']} Points P/L: {trade['points_pnl']}")

            try:
                  trade_number = int(input("Which trade number would you like to edit? "))
            except ValueError:
                  print("Invalid trade number.")
                  continue

            edit_index = trade_number - 1

            if 0 <= edit_index < len(trades):
                  current = trades[edit_index]

                  symbol_input = input(
                        f"Symbol (current: {current['symbol']}): "
                        ).lower().strip()
                  new_symbol = (
                        symbol_input 
                        if symbol_input != "" 
                        else current["symbol"]
                  )

                  new_direction = prompt_choice(
                        (
                              "Direction "
                              f"(current: "
                              f"{current['direction']}): "
                        ), 
                        valid_directions,
                        (
                              "Direction must be "
                              "long or short."
                        ), 
                        default=(
                              current["direction"]
                        )
                  )

                  try:
                        new_entry = (
                              prompt_finite_number(
                                    (
                                          "Entry price "
                                          f"(current: "
                                          f"${current['entry']}): "
                                    ),
                                    "Entry price",
                                    minimum=0,
                                    minimum_is_strict=True,
                                    default=current["entry"]
                              )
                        )

                        new_exit = (
                              prompt_finite_number(
                                    (
                                          "Exit price "
                                          f"(current: "
                                          f"${current['exit']}): "
                                    ),
                                    "Exit price",
                                    minimum=0,
                                    minimum_is_strict=True,
                                    default=current["exit"]
                              )
                        )

                        new_contracts = (
                              prompt_positive_integer(
                                    (
                                          "Contracts "
                                          f"(current: "
                                          f"{current.get('contracts')}): "
                                    ),
                                    "Contracts",
                                    default=(
                                          current[
                                                "contracts"
                                          ]
                                    )
                              )
                        )
                  
                        new_point_value = (
                              prompt_finite_number(
                                    (
                                          "Point value "
                                          f"(current: "
                                          f"${current['point_value']}): "
                                    ),
                                    "Point value",
                                    minimum=0,
                                    minimum_is_strict=True,
                                    default=(
                                          current[
                                                "point_value"
                                          ]
                                    )
                              )
                        )

                        new_risk_amount = (
                              prompt_finite_number(
                                    (
                                          "Risk amount "
                                          f"(current: "
                                          f"${current.get('risk_amount', 0):,.2f}"
                                          "): $"
                                    ),
                                    "Risk amount",
                                    minimum=0,
                                    minimum_is_strict=True,
                                    default=(
                                          current[
                                          "risk_amount"
                                          ]
                                    )
                              )
                        )
                  
                        new_commission = (
                              prompt_finite_number(
                                    (
                                          "Total commission "
                                          f"(current: "
                                          f"${current.get('commission', 0):,.2f}"
                                          "): $"
                                    ),
                                    "Commission",
                                    minimum=0,
                                    default=(
                                          current[
                                                "commission"
                                          ]
                                    )
                              )
                        )
                        
                        new_trade_date = prompt_date(
                              (
                                    "Trade date "
                                    f"(current: "
                                    f"{current.get('trade_date')}): "
                              ), 
                              default=(
                                    current["trade_date"]
                              )
                        )

                        new_entry_time = prompt_time(
                              (
                                    "Entry time "
                                    f"(current: "
                                    f"{current.get('entry_time')}): "
                              ),
                              default=(
                                    current["entry_time"]
                              )
                        )

                        new_exit_time = prompt_time(
                              (
                                    "Exit time "
                                    f"(current: "
                                    f"{current.get('exit_time')}): "
                              ),
                              default=(
                                    current["exit_time"]
                              )
                        )

                        new_duration = calculate_duration(
                              new_entry_time,
                              new_exit_time
                        )
      
                  except ValueError:
                        print("Invalid time format. Please use HH:MM.")
                        continue

                  current_strategies_display = ", ".join(get_strategy_methods(current))
                  strategy_method_input = input(f"Strategy / Method (current: {current_strategies_display}): ").strip()

                  if strategy_method_input == "":
                        if isinstance(current.get("strategy_methods"), list):
                              new_strategy_methods = current["strategy_methods"]
                        else:
                              new_strategy_methods = dedupe_case_insensitive(
                                    split_strategy_methods(current.get("strategy_method", ""))
                              )
                  else:
                        new_strategy_methods = dedupe_case_insensitive(
                              split_strategy_methods(strategy_method_input)
                        )

                  print(f"Strategy / Method recorded: {', '.join(get_strategy_methods({'strategy_methods': new_strategy_methods}))}")

                  current_components_display = ", ".join(get_setup_components(current))
                  setup_input = input(f"Setup Components (current: {current_components_display}): ").strip()

                  if setup_input == "":
                        if isinstance(current.get("setup_components"), list):
                              new_setup_components = current["setup_components"]
                        else:
                              new_setup_components = dedupe_case_insensitive(
                                    split_setup_components(current.get("setup", ""))
                              )
                  else:
                        new_setup_components = dedupe_case_insensitive(
                              split_setup_components(setup_input)
                        )

                  print(f"Setup Components recorded: {', '.join(get_setup_components({'setup_components': new_setup_components}))}")

                  derived_session = determine_session(new_entry_time)
                  if derived_session is not None:
                        new_session = derived_session
                  else:
                        new_session = normalize_session_name(current.get("session", ""))
                  print(f"Session automatically assigned: {new_session}")

                  notes_input = input(f"Notes (current: {current.get('notes', 'N/A')}): ").strip()
                  new_notes = notes_input if notes_input != "" else current.get("notes", "")

                  mistake_input = input(f"Mistake (current: {current.get('mistake', 'N/A')}): ").strip()
                  new_mistake = mistake_input if mistake_input != "" else current.get("mistake", "")


                  new_points_pnl = calculate_points_pnl( 
                        new_direction, 
                        new_entry,
                        new_exit
                  )
                  
                  new_dollar_pnl = calculate_dollar_pnl(
                        new_points_pnl, 
                        new_point_value, 
                        new_contracts
                  )

                  new_net_dollar_pnl = calculate_net_dollar_pnl(
                        new_dollar_pnl,
                        new_commission
                  )

                  new_realized_r = calculate_realized_r(
                        new_dollar_pnl,
                        new_risk_amount
                  )

                  if not all(
                        math.isfinite(value)
                        for value in [
                              new_points_pnl,
                              new_dollar_pnl,
                              new_net_dollar_pnl,
                              new_realized_r
                        ]
                  ):
                        print(
                              "Calculated trade values "
                              "are too large to store "
                              "safely."
                        )

                        continue

                  new_result = calculate_result(new_points_pnl)
                  new_net_result = calculate_net_result(
                        new_net_dollar_pnl
                  )

                  updated_trade = {
                        "symbol": new_symbol,
                        "direction": new_direction,

                        "entry": new_entry,
                        "exit": new_exit,

                        "contracts": new_contracts,
                        "point_value": new_point_value,

                        "points_pnl": new_points_pnl,
                        "dollar_pnl": new_dollar_pnl,
                        "commission": new_commission,
                        "net_dollar_pnl": new_net_dollar_pnl,
                        "result": new_result,
                        "net_result": new_net_result,

                        "risk_amount": new_risk_amount,
                        "realized_r": new_realized_r,

                        "trade_date": new_trade_date,
                        "entry_time": new_entry_time,
                        "exit_time": new_exit_time,
                        "duration": new_duration,

                        "strategy_methods": new_strategy_methods,
                        "setup_components": new_setup_components,
                        "session": new_session,
                        "notes": new_notes,
                        "mistake": new_mistake
                  }

                  previous_trade = current

                  trades[edit_index] = updated_trade

                  if save_trades(trades):
                        print(
                              "Trade updated "
                              "successfully."
                        )

                  else:
                        trades[edit_index] = (
                              previous_trade
                        )

                        print(
                              "Trade changes were not "
                              "applied because they "
                              "could not be saved."
                        )


      elif choice == "6":
            if len(trades) == 0:
                  print("No trades to delete.")
            else:
                  for i in range(len(trades)):
                        trade = trades[i]
                        print(f"{i + 1}. {trade['symbol']} {trade['direction']} Points P/L: {trade['points_pnl']}")

                  try:
                        trade_number = int(input("Which trade number would you like to delete? "))
                  except ValueError:
                        print("Invalid trade number.")
                        continue

                  delete_index = trade_number - 1

                  if 0 <= delete_index < len(trades):
                        trade_to_delete = trades[delete_index]

                        delete_net_result = trade_to_delete.get(
                              "net_result",
                              calculate_net_result(
                                    trade_to_delete.get(
                                          "net_dollar_pnl",
                                          trade_to_delete.get("dollar_pnl", 0)
                                    )
                              )
                        )

                        confirm = input(
                              f"Are you sure you want to delete "
                              f"{trade_to_delete['symbol']} "
                              f"({delete_net_result}, "
                              f"{trade_to_delete['points_pnl']:,.2f} pts)? "
                              f"(yes/no): "
                        ).lower().strip()
                        if confirm == "yes":
                              removed_trade = (
                                    trades.pop(
                                          delete_index
                                    )
                              )

                              if save_trades(trades):
                                    print(
                                          "Deleted trade " 
                                          f"{removed_trade['symbol']}"
                                    )
                              
                              else: 
                                    trades.insert(
                                          delete_index, 
                                          removed_trade
                                    )

                                    print(
                                          "Trade was not "
                                          "deleted because "
                                          "the change could"
                                          " not be saved."
                                    )
                  
                        else:
                              print("Delete cancelled.")
                  else:
                        print("Invalid trade number.")

      elif choice == "7":
            if len(trades) == 0:
                  print("No trades to calculate statistics.")
            else:
                  total_trades = len(trades)
                  wins = 0
                  losses = 0
                  breakevens = 0

                  net_wins = 0
                  net_losses = 0
                  net_breakevens = 0

                  total_points_pnl = 0
                  total_dollar_pnl = 0
                  total_commission = 0
                  total_net_dollar_pnl = 0

                  total_risk = 0
                  total_realized_r = 0
                  risk_trades = 0

                  total_duration = 0
                  timed_trades = 0 
                  longest_duration = None
                  shortest_duration = None
                  earliest_entry_time = None 
                  latest_entry_time = None
                  best_r_trade = None
                  worst_r_trade = None
                  best_r_idx = None
                  worst_r_idx = None

                  best_points_trade = trades[0]
                  worst_points_trade = trades[0]
                  best_dollar_trade = trades[0]
                  worst_dollar_trade = trades[0]
                  best_net_trade = trades[0]
                  worst_net_trade = trades[0]
                  best_points_idx = 0
                  worst_points_idx = 0
                  best_dollar_idx = 0
                  worst_dollar_idx = 0
                  best_net_idx = 0
                  worst_net_idx = 0

                  for i, trade in enumerate(trades):
                        points_pnl = trade['points_pnl']
                        dollar_pnl = trade.get('dollar_pnl', 0)
                        commission = trade.get('commission', 0)
                        net_dollar_pnl = trade.get(
                              "net_dollar_pnl", 
                              trade.get("dollar_pnl", 0)
                        )
                        result = trade['result']

                        total_points_pnl += points_pnl
                        total_dollar_pnl += dollar_pnl
                        total_commission += commission
                        total_net_dollar_pnl += net_dollar_pnl

                        risk_amount = trade.get("risk_amount", 0)
                        realized_r = trade.get("realized_r", 0)

                        if risk_amount > 0:
                              total_risk += risk_amount
                              total_realized_r += realized_r
                              risk_trades += 1
                        
                              if best_r_trade is None or realized_r > best_r_trade.get("realized_r", 0):
                                    best_r_trade = trade
                                    best_r_idx = i
                              
                              if worst_r_trade is None or realized_r < worst_r_trade.get("realized_r", 0):
                                    worst_r_trade = trade
                                    worst_r_idx = i

                        if (
                              net_dollar_pnl
                              > best_net_trade.get(
                                    "net_dollar_pnl", 
                                    best_net_trade.get("dollar_pnl", 0)
                              )
                        ):
                              best_net_trade = trade
                              best_net_idx = i  

                        if (
                              net_dollar_pnl
                              < worst_net_trade.get(
                                    "net_dollar_pnl", 
                                    worst_net_trade.get("dollar_pnl", 0)
                              )
                        ):
                              worst_net_trade = trade
                              worst_net_idx = i

                        if result == "Win":
                              wins += 1
                        elif result == "Loss":
                              losses += 1
                        else:
                              breakevens += 1

                        net_result = trade.get(
                              "net_result",
                              calculate_net_result(net_dollar_pnl)
                        )

                        if net_result == "Win":
                              net_wins += 1
                        elif net_result == "Loss":
                              net_losses += 1
                        else:
                              net_breakevens += 1

                        if trade['points_pnl'] > best_points_trade['points_pnl']:
                              best_points_trade = trade
                              best_points_idx = i

                        if trade['points_pnl'] < worst_points_trade['points_pnl']:
                              worst_points_trade = trade
                              worst_points_idx = i

                        if trade.get('dollar_pnl', 0) > best_dollar_trade.get('dollar_pnl', 0):
                              best_dollar_trade = trade
                              best_dollar_idx = i
                        
                        if trade.get('dollar_pnl', 0) < worst_dollar_trade.get('dollar_pnl', 0):
                              worst_dollar_trade = trade
                              worst_dollar_idx = i
                        
                        duration = trade.get("duration")

                        if duration is not None:
                              total_duration += duration
                              timed_trades += 1

                              if longest_duration is None or duration > longest_duration:
                                    longest_duration = duration

                              if shortest_duration is None or duration < shortest_duration:
                                    shortest_duration = duration

                        entry_time = trade.get("entry_time")

                        if entry_time is not None:
                              entry_datetime = datetime.strptime(entry_time, "%H:%M")

                              if earliest_entry_time is None or entry_datetime < earliest_entry_time:
                                    earliest_entry_time = entry_datetime

                              if latest_entry_time is None or entry_datetime > latest_entry_time:
                                    latest_entry_time = entry_datetime
                                    
                  win_rate = (wins / total_trades) * 100
                  net_win_rate = (net_wins / total_trades) * 100

                  average_points_pnl = total_points_pnl / total_trades
                  average_dollar_pnl = total_dollar_pnl / total_trades
                  average_commission = total_commission / total_trades
                  average_net_dollar_pnl = (
                        total_net_dollar_pnl / total_trades
                  )

                  gross_net_profit = sum(
                        trade.get(
                              "net_dollar_pnl",
                              trade.get("dollar_pnl", 0)
                        )
                        for trade in trades
                        if trade.get(
                              "net_dollar_pnl",
                              trade.get("dollar_pnl", 0)
                        ) > 0
                  )

                  gross_net_loss = sum(
                        abs(
                              trade.get(
                                    "net_dollar_pnl",
                                    trade.get("dollar_pnl", 0)
                              )
                        )
                        for trade in trades
                        if trade.get(
                              "net_dollar_pnl",
                              trade.get("dollar_pnl", 0)
                        ) < 0
                  )

                  gross_points_profit = sum(
                        abs(trade["points_pnl"]) \
                        for trade in trades
                        if trade["points_pnl"] > 0
                  )
                  
                  gross_points_loss = sum(
                        abs(trade["points_pnl"])
                        for trade in trades
                        if trade["points_pnl"] < 0
                  )

                  gross_dollar_profit = sum(
                        abs(trade.get("dollar_pnl", 0))
                        for trade in trades
                        if trade.get("dollar_pnl", 0) > 0
                  )
                  gross_dollar_loss = sum(
                        abs(trade.get("dollar_pnl", 0))
                        for trade in trades
                        if trade.get("dollar_pnl", 0) < 0
                  )
                  
                  average_points_win = gross_points_profit / wins if wins > 0 else 0
                  average_points_loss = gross_points_loss / losses if losses > 0 else 0

                  average_dollar_win = gross_dollar_profit / wins if wins > 0 else 0
                  average_dollar_loss = gross_dollar_loss / losses if losses > 0 else 0

                  average_net_win = (
                        gross_net_profit / net_wins
                        if net_wins > 0
                        else 0
                  )

                  average_net_loss = (
                        gross_net_loss / net_losses
                        if net_losses > 0
                        else 0
                  )

                  if gross_points_loss > 0:
                        points_profit_factor = gross_points_profit / gross_points_loss
                  else:
                        points_profit_factor = None

                  if gross_dollar_loss > 0:
                        dollar_profit_factor = gross_dollar_profit / gross_dollar_loss
                  else:
                        dollar_profit_factor = None


                  if gross_net_loss > 0:
                        net_profit_factor = (
                              gross_net_profit / gross_net_loss
                        )
                  else:
                        net_profit_factor = None

                  points_expectancy = average_points_pnl
                  dollar_expectancy = average_dollar_pnl
                  net_expectancy = average_net_dollar_pnl

                  if timed_trades > 0: 
                        average_duration = total_duration / timed_trades 
                  else: 
                        average_duration = 0
                  
                  if risk_trades > 0:
                        average_risk = total_risk / risk_trades
                        average_realized_r = total_realized_r / risk_trades
                  else: 
                        average_risk = 0 
                        average_realized_r = 0

                  print("\n" + "=" * 50)
                  print("PERFORMANCE STATISTICS")
                  print("=" * 50)

                  print()
                  print("-" * 31)
                  print("GENERAL PERFORMANCE")
                  print("-" * 31)
                  print()
                  print(f"{'Total Trades:':<27}{total_trades}")
                  print(f"{'Wins:':<27}{wins}")
                  print(f"{'Losses:':<27}{losses}")
                  print(f"{'Break-even Trades:':<27}{breakevens}")
                  print(f"{'Win Rate:':<27}{win_rate:.2f}%")

                  print()
                  print("-" * 31)
                  print("POINTS PERFORMANCE")
                  print("-" * 31)
                  print()
                  print(f"{'Total Points:':<27}{total_points_pnl:,.2f} pts")
                  print(f"{'Average Points per Trade:':<27}{average_points_pnl:.2f} pts")
                  print(
                        f"{'Best Trade:':<27}#{best_points_idx + 1} {best_points_trade['symbol']} "
                        f"({best_points_trade['points_pnl']:.2f} pts)"
                  )
                  print(
                        f"{'Worst Trade:':<27}#{worst_points_idx + 1} {worst_points_trade['symbol']} "
                        f"({worst_points_trade['points_pnl']:.2f} pts)"
                  )
                  print(f"{'Gross Points Profit:':<27}{gross_points_profit:,.2f} pts")
                  print(f"{'Gross Points Loss:':<27}-{gross_points_loss:,.2f} pts")
                  print(f"{'Average Points Win:':<27}{average_points_win:,.2f} pts")
                  print(f"{'Average Points Loss:':<27}-{average_points_loss:,.2f} pts")

                  if points_profit_factor is None:
                        print(f"{'Points Profit Factor:':<27}N/A (no losing trades)")
                  else:
                        print(f"{'Points Profit Factor:':<27}{points_profit_factor:.2f}")

                  print(f"{'Points Expectancy:':<27}{points_expectancy:.2f} pts")

                  print()
                  print("-" * 31)
                  print("GROSS DOLLAR PERFORMANCE")
                  print("-" * 31)
                  print()
                  print(f"{'Total Gross Dollar P/L:':<27}${total_dollar_pnl:,.2f}")
                  print(f"{'Average Gross Dollar P/L:':<27}${average_dollar_pnl:,.2f}")
                  print(
                        f"{'Best Dollar Trade:':<27}#{best_dollar_idx + 1} {best_dollar_trade['symbol']} "
                        f"(${best_dollar_trade.get('dollar_pnl', 0):,.2f})"
                  )
                  print(
                        f"{'Worst Dollar Trade:':<27}#{worst_dollar_idx + 1} {worst_dollar_trade['symbol']} "
                        f"(${worst_dollar_trade.get('dollar_pnl', 0):,.2f})"
                  )
                  print(f"{'Gross Profit:':<27}${gross_dollar_profit:,.2f}")
                  print(f"{'Gross Loss:':<27}-${gross_dollar_loss:,.2f}")
                  print(f"{'Average Gross Winner:':<27}${average_dollar_win:,.2f}")
                  print(f"{'Average Gross Loser:':<27}-${average_dollar_loss:,.2f}")

                  if dollar_profit_factor is None:
                        print(f"{'Profit Factor:':<27}N/A (no losing trades)")
                  else:
                        print(f"{'Profit Factor:':<27}{dollar_profit_factor:.2f}")

                  print(f"{'Expectancy:':<27}${dollar_expectancy:,.2f}")

                  print("\n" + "=" * 50)
                  print("COMMISSION & NET PERFORMANCE")
                  print("=" * 50)
                  print()
                  print(f"{'Total Commission:':<27}${total_commission:,.2f}")
                  print(f"{'Average Commission:':<27}${average_commission:,.2f}")
                  print(
                        f"{'Total Net Dollar P/L:':<27}"
                        f"${total_net_dollar_pnl:,.2f}"
                  )

                  print(
                        f"{'Average Net Dollar P/L:':<27}"
                        f"${average_net_dollar_pnl:,.2f}"
                  )

                  print(
                        f"{'Best Net Trade:':<27}#{best_net_idx + 1} "
                        f"{best_net_trade['symbol']} "
                        f"(${best_net_trade.get('net_dollar_pnl', best_net_trade.get('dollar_pnl', 0)):,.2f})"
                  )

                  print(
                        f"{'Worst Net Trade:':<27}#{worst_net_idx + 1} "
                        f"{worst_net_trade['symbol']} "
                        f"(${worst_net_trade.get('net_dollar_pnl', worst_net_trade.get('dollar_pnl', 0)):,.2f})"
                  )

                  print(f"{'Gross Net Profit:':<27}${gross_net_profit:,.2f}")
                  print(f"{'Gross Net Loss:':<27}-${gross_net_loss:,.2f}")
                  print(f"{'Average Net Winner:':<27}${average_net_win:,.2f}")
                  print(f"{'Average Net Loser:':<27}-${average_net_loss:,.2f}")

                  if net_profit_factor is None:
                        print(f"{'Net Profit Factor:':<27}N/A (no losing trades)")
                  else:
                        print(f"{'Net Profit Factor:':<27}{net_profit_factor:.2f}")

                  print(f"{'Net Expectancy:':<27}${net_expectancy:,.2f}")
                  print(f"{'Net Wins:':<27}{net_wins}")
                  print(f"{'Net Losses:':<27}{net_losses}")
                  print(f"{'Net Break-even Trades:':<27}{net_breakevens}")
                  print(f"{'Net Win Rate:':<27}{net_win_rate:.2f}%")

                  print("\n" + "=" * 50)
                  print("RISK ANALYTICS")
                  print("=" * 50)
                  print()
                  print(f"{'Average Risk:':<27}${average_risk:,.2f}")
                  print(f"{'Average Realized R:':<27}{average_realized_r:.2f}R")

                  if best_r_trade is not None:
                        print(
                              f"{'Best R Trade:':<27}#{best_r_idx + 1} "
                              f"{best_r_trade['symbol']} "
                              f"({best_r_trade.get('realized_r', 0):.2f}R)"
                        )
                  else:
                        print(f"{'Best R Trade:':<27}N/A")
                  if worst_r_trade is not None:
                        print(
                              f"{'Worst R Trade:':<27}#{worst_r_idx + 1} "
                              f"{worst_r_trade['symbol']} "
                              f"({worst_r_trade.get('realized_r', 0):.2f}R)"
                        )
                  else:
                        print(f"{'Worst R Trade:':<27}N/A")

                  print("\n" + "=" * 50)
                  print("TRADE DURATION")
                  print("=" * 50)
                  print()
                  print(f"{'Average Trade Duration:':<27}{average_duration:.2f} minutes")
                  if timed_trades > 0:
                        print(f"{'Longest trade duration:':<27}{longest_duration} minutes")
                        print(f"{'Shortest trade duration:':<27}{shortest_duration} minutes")
                  else:
                        print(f"{'Longest trade duration:':<27}N/A")
                        print(f"{'Shortest trade duration:':<27}N/A")

                  if earliest_entry_time is not None:
                        print(f"{'Earliest entry time:':<27}{earliest_entry_time.strftime('%H:%M')}")
                        print(f"{'Latest entry time:':<27}{latest_entry_time.strftime('%H:%M')}")
                  else:
                        print(f"{'Earliest entry time:':<27}N/A")
                        print(f"{'Latest entry time:':<27}N/A")

                  streaks = calculate_streaks(trades)

                  if streaks["current_type"] == "Win":
                        current_streak_display = (
                              f"{streaks['current_length']} Win"
                              + ("s" if streaks["current_length"] != 1 else "")
                        )
                  elif streaks["current_type"] == "Loss":
                        current_streak_display = (
                              f"{streaks['current_length']} Loss"
                              + ("es" if streaks["current_length"] != 1 else "")
                        )
                  else:
                        current_streak_display = "No Active Streak"

                  longest_winning_display = (
                        f"{streaks['longest_winning']} Win"
                        + ("s" if streaks["longest_winning"] != 1 else "")
                  )
                  longest_losing_display = (
                        f"{streaks['longest_losing']} Loss"
                        + ("es" if streaks["longest_losing"] != 1 else "")
                  )

                  print("\n" + "=" * 50)
                  print("STREAK ANALYTICS")
                  print("=" * 50)
                  print()
                  print(f"{'Current Streak:':<27}{current_streak_display}")
                  print(f"{'Longest Winning Streak:':<27}{longest_winning_display}")
                  print(f"{'Longest Losing Streak:':<27}{longest_losing_display}")

      elif choice == "8":
            if len(trades) == 0:
                  print("No trades to search")
            else:
                  print("\nMulti-Filter Search.")
                  print("Press Enter to skip any filter.")

                  symbol_filter = input("Symbol: ").lower().strip()
                  direction_filter = input ("Direction: ").lower().strip()
                  result_filter = input ("Result: ").lower().strip()
                  net_result_filter = input("Net Result: ").lower().strip()
                  setup_filter = input ("Setup Component: ").strip()
                  strategy_method_filter = input("Strategy / Method: ").strip()
                  session_filter = input ("session: ").lower().strip()

                  start_date_filter = get_optional_date(
                        "Start date (YYYY-MM-DD): "
                  )

                  end_date_filter = get_optional_date(
                        "End date (YYYY-MM-DD): "
                  )

                  if (
                        start_date_filter is not None
                        and end_date_filter is not None
                        and end_date_filter < start_date_filter
                  ):
                        print("End date cannot be earlier than start date.")
                        continue

                  found = False
                  match_count = 0

                  for i in range(len(trades)):
                        trade = trades[i]
                        matches = True

                        if symbol_filter != "" and trade.get("symbol", "").lower().strip() != symbol_filter:
                              matches = False
                        if direction_filter != "" and trade.get("direction", "").lower().strip() != direction_filter:
                              matches = False
                        if result_filter != "" and trade.get("result", "").lower().strip() != result_filter:
                              matches = False

                        net_result = trade.get(
                              "net_result",
                              calculate_net_result(
                                    trade.get(
                                          "net_dollar_pnl",
                                          trade.get("dollar_pnl", 0)
                                    )
                              )
                        )

                        if (
                              net_result_filter != ""
                              and net_result.lower().strip() != net_result_filter
                        ):
                              matches = False

                        if setup_filter != "":
                              normalized_setup_filter = normalize_setup_name(setup_filter).lower()
                              trade_components_lower = [
                                    component.lower() for component in get_setup_components(trade)
                              ]
                              if normalized_setup_filter not in trade_components_lower:
                                    matches = False
                        if strategy_method_filter != "":
                              normalized_strategy_filter = normalize_strategy_method(strategy_method_filter).lower()
                              trade_strategies_lower = [
                                    strategy.lower() for strategy in get_strategy_methods(trade)
                              ]
                              if normalized_strategy_filter not in trade_strategies_lower:
                                    matches = False
                        if session_filter != "" and trade.get("session", "").lower().strip() != session_filter:
                              matches = False

                        if not trade_is_in_date_range(
                              trade,
                              start_date_filter,
                              end_date_filter
                        ):
                              matches = False

                        if matches:
                              print(f"\nTrade #{i + 1}")
                              print(f"Symbol: {trade['symbol']}")
                              print(f"Direction: {trade['direction']}")
                              print(f"Date: {trade.get('trade_date', 'N/A').replace('-', ' ')}")

                              print(f"Entry: {trade['entry']}")
                              print(f"Exit: {trade['exit']}")
                              print(f"Contracts: {trade.get('contracts', 'N/A')}")
                              point_value = trade.get("point_value")
                              if point_value is None:
                                    print("Point Value: N/A")
                              else:
                                    print(f"Point Value: ${point_value:,.2f}")

                              print(f"Points P/L: {trade['points_pnl']:,.2f} pts")
                              print(
                                    f"Gross Dollar P/L: "
                                    f"${trade.get('dollar_pnl', 0):,.2f}"
                              )
                              print(
                                    f"Commission: "
                                    f"${trade.get('commission', 0):,.2f}"
                              )
                              print(
                                    f"Net Dollar P/L: "
                                    f"${trade.get('net_dollar_pnl', trade.get('dollar_pnl', 0)):,.2f}"
                              )
                              print(f"Result: {trade['result']}")
                              print(f"Net Result: {net_result}")
                              print(f"Risk Amount: ${trade.get('risk_amount', 0):,.2f}")
                              print(f"Realized R: {trade.get('realized_r', 0):.2f}R")

                              print(f"Entry Time: {trade.get('entry_time', 'N/A')}")
                              print(f"Exit Time: {trade.get('exit_time', 'N/A')}")
                              print(f"Duration: {trade.get('duration', 'N/A')} minutes")

                              print(f"Strategy / Method: {get_strategy_method(trade)}")
                              print(f"Setup Components: {', '.join(get_setup_components(trade))}")
                              print(f"Session: {trade.get('session', 'N/A')}")
                              print(f"Notes: {trade.get('notes', 'N/A')}")
                              print(f"Mistake: {trade.get('mistake', 'N/A')}")
                              found = True
                              match_count += 1

                  if not found:
                        print("No matching trades found")
                  else:
                        print(f"\n{match_count} trade(s) found.")

      elif choice == "9": 
            if len(trades) == 0: 
                  print("No trades to calculate filtered statistics.")
            else: 
                  print("\nFiltered Statistics")
                  print("Press Enter to skip any filter. ")

                  symbol_filter = input("Symbol: ").lower().strip()
                  direction_filter = input ("Direction: ").lower().strip()
                  result_filter = input ("Result: ").lower().strip()
                  net_result_filter = input("Net Result: ").lower().strip()
                  setup_filter = input ("Setup Component: ").strip()
                  session_filter = input ("Session: ").lower().strip()

                  start_date_filter = get_optional_date(
                        "Start date (YYYY-MM-DD): "
                  )

                  end_date_filter = get_optional_date(
                        "End date (YYYY-MM-DD): "
                  )

                  if (
                        start_date_filter is not None
                        and end_date_filter is not None
                        and end_date_filter < start_date_filter
                  ):
                        print("End date cannot be earlier than start date.")
                        continue
                  
                  filtered_trades = []
                  filtered_indices = []

                  for idx, trade in enumerate(trades): 
                        matches = True 
                        
                        if symbol_filter != "" and trade.get("symbol", "").lower().strip() != symbol_filter:
                              matches = False 
                        if direction_filter != "" and trade.get("direction", "").lower().strip() != direction_filter: 
                              matches = False 
                        if result_filter != "" and trade.get("result", "").lower().strip() != result_filter:
                              matches = False

                        net_result = trade.get(
                              "net_result",
                              calculate_net_result(
                                    trade.get(
                                          "net_dollar_pnl",
                                          trade.get("dollar_pnl", 0)
                                    )
                              )
                        )

                        if (
                              net_result_filter != ""
                              and net_result.lower().strip() != net_result_filter
                        ):
                              matches = False

                        if setup_filter != "":
                              normalized_setup_filter = normalize_setup_name(setup_filter).lower()
                              trade_components_lower = [
                                    component.lower() for component in get_setup_components(trade)
                              ]
                              if normalized_setup_filter not in trade_components_lower:
                                    matches = False
                        if session_filter != "" and trade.get("session", "").lower().strip() != session_filter:
                              matches = False

                        if not trade_is_in_date_range(
                              trade,
                              start_date_filter,
                              end_date_filter
                        ):
                              matches = False

                        if matches: 
                              filtered_trades.append(trade)
                              filtered_indices.append(idx)

                  if len(filtered_trades) == 0: 
                        print("No trades matched those filters")
                  else: 
                        total_trades = len(filtered_trades)
                        wins = 0
                        losses = 0
                        breakevens = 0

                        net_wins = 0
                        net_losses = 0
                        net_breakevens = 0

                        total_points_pnl = 0
                        total_dollar_pnl = 0
                        total_commission = 0
                        total_net_dollar_pnl = 0

                        total_risk = 0
                        total_realized_r = 0
                        risk_trades = 0

                        best_points_trade = filtered_trades[0]
                        worst_points_trade = filtered_trades[0]
                        best_dollar_trade = filtered_trades[0]
                        worst_dollar_trade = filtered_trades[0]
                        best_points_idx = filtered_indices[0]
                        worst_points_idx = filtered_indices[0]
                        best_dollar_idx = filtered_indices[0]
                        worst_dollar_idx = filtered_indices[0]
                        best_net_trade = filtered_trades[0]
                        worst_net_trade = filtered_trades[0]
                        best_net_idx = filtered_indices[0]
                        worst_net_idx = filtered_indices[0]

                        total_duration = 0
                        timed_trades = 0
                        longest_duration = None
                        shortest_duration = None
                        earliest_entry_time = None
                        latest_entry_time = None
                        best_r_trade = None
                        worst_r_trade = None
                        best_r_idx = None
                        worst_r_idx = None
                        
                        for i, trade in enumerate(filtered_trades): 
                              points_pnl = trade["points_pnl"]
                              dollar_pnl = trade.get("dollar_pnl", 0)
                              commission = trade.get("commission", 0)
                              net_dollar_pnl = trade.get(
                                    "net_dollar_pnl",
                                    trade.get("dollar_pnl", 0)
                              )
                              result = trade["result"]    

                              total_points_pnl += points_pnl
                              total_dollar_pnl += dollar_pnl
                              total_commission += commission
                              total_net_dollar_pnl += net_dollar_pnl

                              if result == "Win":
                                    wins += 1
                              elif result == "Loss":
                                    losses += 1
                              else:
                                    breakevens += 1

                              net_result = trade.get(
                                    "net_result",
                                    calculate_net_result(net_dollar_pnl)
                              )

                              if net_result == "Win":
                                    net_wins += 1
                              elif net_result == "Loss":
                                    net_losses += 1
                              else:
                                    net_breakevens += 1

                              if points_pnl > best_points_trade["points_pnl"]:
                                    best_points_trade = trade
                                    best_points_idx = filtered_indices[i]

                              if points_pnl < worst_points_trade["points_pnl"]:
                                    worst_points_trade = trade
                                    worst_points_idx = filtered_indices[i]

                              if dollar_pnl > best_dollar_trade.get("dollar_pnl", 0):
                                    best_dollar_trade = trade
                                    best_dollar_idx = filtered_indices[i]

                              if dollar_pnl < worst_dollar_trade.get("dollar_pnl", 0):
                                    worst_dollar_trade = trade
                                    worst_dollar_idx = filtered_indices[i]

                              if (
                                    net_dollar_pnl
                                    > best_net_trade.get(
                                          "net_dollar_pnl",
                                          best_net_trade.get("dollar_pnl", 0)
                                    )
                              ):
                                    best_net_trade = trade
                                    best_net_idx = filtered_indices[i]
                              if (
                                    net_dollar_pnl
                                    < worst_net_trade.get(
                                          "net_dollar_pnl",
                                          worst_net_trade.get("dollar_pnl", 0)
                                    )
                              ):
                                    worst_net_trade = trade
                                    worst_net_idx = filtered_indices[i]

                              risk_amount = trade.get("risk_amount", 0)
                              realized_r = trade.get("realized_r", 0)

                              if risk_amount > 0:
                                    total_risk += risk_amount
                                    total_realized_r += realized_r
                                    risk_trades += 1

                                    if best_r_trade is None or realized_r > best_r_trade.get("realized_r", 0):
                                          best_r_trade = trade
                                          best_r_idx = filtered_indices[i]

                                    if worst_r_trade is None or realized_r < worst_r_trade.get("realized_r", 0):
                                          worst_r_trade = trade
                                          worst_r_idx = filtered_indices[i]

                              duration = trade.get("duration")
                              if duration is not None:
                                    total_duration += duration
                                    timed_trades += 1
                                    if longest_duration is None or duration > longest_duration:
                                          longest_duration = duration
                                    if shortest_duration is None or duration < shortest_duration:
                                          shortest_duration = duration

                              entry_time = trade.get("entry_time")
                              if entry_time is not None:
                                    entry_datetime = datetime.strptime(entry_time, "%H:%M")
                                    if earliest_entry_time is None or entry_datetime < earliest_entry_time:
                                          earliest_entry_time = entry_datetime
                                    if latest_entry_time is None or entry_datetime > latest_entry_time:
                                          latest_entry_time = entry_datetime

                        win_rate = (wins / total_trades) * 100
                        net_win_rate = (net_wins / total_trades) * 100

                        average_points_pnl = total_points_pnl / total_trades
                        average_dollar_pnl = total_dollar_pnl / total_trades
                        
                        average_commission = (
                              total_commission / total_trades
                        )

                        average_net_dollar_pnl = (
                              total_net_dollar_pnl / total_trades
                        )

                        gross_net_profit = sum(
                              trade.get(
                                    "net_dollar_pnl",
                                    trade.get("dollar_pnl", 0)
                              )
                              for trade in filtered_trades
                              if trade.get(
                                    "net_dollar_pnl",
                                    trade.get("dollar_pnl", 0)
                              ) > 0
                        )
                        gross_net_loss = sum(
                              abs(
                                    trade.get(
                                          "net_dollar_pnl",
                                          trade.get("dollar_pnl", 0)
                                    )
                              )
                              for trade in filtered_trades
                              if trade.get(
                                    "net_dollar_pnl",
                                    trade.get("dollar_pnl", 0)
                              ) < 0
                        )

                        average_net_win = (
                              gross_net_profit / net_wins
                              if net_wins > 0
                              else 0
                        )

                        average_net_loss = (
                              gross_net_loss / net_losses
                              if net_losses > 0
                              else 0
                        )

                        if gross_net_loss > 0:
                              net_profit_factor = (
                                    gross_net_profit / gross_net_loss
                              )
                        else:
                              net_profit_factor = None
                        
                        net_expectancy = average_net_dollar_pnl

                        gross_points_profit = sum(
                              trade["points_pnl"]
                              for trade in filtered_trades
                              if trade["points_pnl"] > 0
                        )

                        gross_points_loss = sum(
                              abs(trade["points_pnl"])
                              for trade in filtered_trades
                              if trade["points_pnl"] < 0
                        )

                        gross_dollar_profit = sum(
                              trade.get("dollar_pnl", 0) 
                              for trade in filtered_trades 
                              if trade.get("dollar_pnl", 0) > 0
                        )

                        gross_dollar_loss = sum(
                              abs(trade.get("dollar_pnl", 0)) 
                              for trade in filtered_trades 
                              if trade.get("dollar_pnl", 0) < 0
                        )

                        if risk_trades > 0:
                              average_risk = total_risk / risk_trades
                              average_realized_r = total_realized_r / risk_trades
                        else:
                              average_risk = 0
                              average_realized_r = 0

                        average_points_win = gross_points_profit / wins if wins > 0 else 0
                        average_points_loss = gross_points_loss / losses if losses > 0 else 0

                        average_dollar_win = gross_dollar_profit / wins if wins > 0 else 0
                        average_dollar_loss = gross_dollar_loss / losses if losses > 0 else 0

                        if gross_points_loss > 0:
                              points_profit_factor = gross_points_profit / gross_points_loss
                        else:
                              points_profit_factor = None
                        
                        if gross_dollar_loss > 0:
                              dollar_profit_factor = gross_dollar_profit / gross_dollar_loss
                        else:
                              dollar_profit_factor = None

                        points_expectancy = average_points_pnl
                        dollar_expectancy = average_dollar_pnl

                        print("\n" + "=" * 50)
                        print("PERFORMANCE STATISTICS")
                        print("=" * 50)

                        print()
                        print("-" * 31)
                        print("GENERAL PERFORMANCE")
                        print("-" * 31)
                        print()
                        print(f"{'Total Trades:':<27}{total_trades}")
                        print(f"{'Wins:':<27}{wins}")
                        print(f"{'Losses:':<27}{losses}")
                        print(f"{'Break-even Trades:':<27}{breakevens}")
                        print(f"{'Win Rate:':<27}{win_rate:.2f}%")

                        print()
                        print("-" * 31)
                        print("POINTS PERFORMANCE")
                        print("-" * 31)
                        print()
                        print(f"{'Total Points:':<27}{total_points_pnl:,.2f} pts")
                        print(f"{'Average Points per Trade:':<27}{average_points_pnl:.2f} pts")
                        print(
                              f"{'Best Trade:':<27}#{best_points_idx + 1} {best_points_trade['symbol']} "
                              f"({best_points_trade['points_pnl']:.2f} pts)"
                        )
                        print(
                              f"{'Worst Trade:':<27}#{worst_points_idx + 1} {worst_points_trade['symbol']} "
                              f"({worst_points_trade['points_pnl']:.2f} pts)"
                        )
                        print(f"{'Gross Points Profit:':<27}{gross_points_profit:,.2f} pts")
                        print(f"{'Gross Points Loss:':<27}-{gross_points_loss:,.2f} pts")
                        print(f"{'Average Points Win:':<27}{average_points_win:,.2f} pts")
                        print(f"{'Average Points Loss:':<27}-{average_points_loss:,.2f} pts")

                        if points_profit_factor is None:
                              print(f"{'Points Profit Factor:':<27}N/A (no losing trades)")
                        else:
                              print(f"{'Points Profit Factor:':<27}{points_profit_factor:.2f}")

                        print(f"{'Points Expectancy:':<27}{points_expectancy:.2f} pts")

                        print()
                        print("-" * 31)
                        print("GROSS DOLLAR PERFORMANCE")
                        print("-" * 31)
                        print()
                        print(f"{'Total Gross Dollar P/L:':<27}${total_dollar_pnl:,.2f}")
                        print(f"{'Average Gross Dollar P/L:':<27}${average_dollar_pnl:,.2f}")
                        print(
                              f"{'Best Dollar Trade:':<27}#{best_dollar_idx + 1} {best_dollar_trade['symbol']} "
                              f"(${best_dollar_trade.get('dollar_pnl', 0):,.2f})"
                        )
                        print(
                              f"{'Worst Dollar Trade:':<27}#{worst_dollar_idx + 1} {worst_dollar_trade['symbol']} "
                              f"(${worst_dollar_trade.get('dollar_pnl', 0):,.2f})"
                        )
                        print(f"{'Gross Profit:':<27}${gross_dollar_profit:,.2f}")
                        print(f"{'Gross Loss:':<27}-${gross_dollar_loss:,.2f}")
                        print(f"{'Average Gross Winner:':<27}${average_dollar_win:,.2f}")
                        print(f"{'Average Gross Loser:':<27}-${average_dollar_loss:,.2f}")

                        if dollar_profit_factor is None:
                              print(f"{'Profit Factor:':<27}N/A (no losing trades)")
                        else:
                              print(f"{'Profit Factor:':<27}{dollar_profit_factor:.2f}")

                        print(f"{'Expectancy:':<27}${dollar_expectancy:,.2f}")

                        print("\n" + "=" * 50)
                        print("COMMISSION & NET PERFORMANCE")
                        print("=" * 50)
                        print()
                        print(f"{'Total Commission:':<27}${total_commission:,.2f}")
                        print(f"{'Average Commission:':<27}${average_commission:,.2f}")
                        print(
                              f"{'Total Net Dollar P/L:':<27}"
                              f"${total_net_dollar_pnl:,.2f}"
                        )

                        print(
                              f"{'Average Net Dollar P/L:':<27}"
                              f"${average_net_dollar_pnl:,.2f}"
                        )

                        print(
                              f"{'Best Net Trade:':<27}#{best_net_idx + 1} "
                              f"{best_net_trade['symbol']} "
                              f"(${best_net_trade.get('net_dollar_pnl', best_net_trade.get('dollar_pnl', 0)):,.2f})"
                        )

                        print(
                              f"{'Worst Net Trade:':<27}#{worst_net_idx + 1} "
                              f"{worst_net_trade['symbol']} "
                              f"(${worst_net_trade.get('net_dollar_pnl', worst_net_trade.get('dollar_pnl', 0)):,.2f})"
                        )

                        print(f"{'Gross Net Profit:':<27}${gross_net_profit:,.2f}")
                        print(f"{'Gross Net Loss:':<27}-${gross_net_loss:,.2f}")
                        print(f"{'Average Net Winner:':<27}${average_net_win:,.2f}")
                        print(f"{'Average Net Loser:':<27}-${average_net_loss:,.2f}")

                        if net_profit_factor is None:
                              print(f"{'Net Profit Factor:':<27}N/A (no losing trades)")
                        else:
                              print(f"{'Net Profit Factor:':<27}{net_profit_factor:.2f}")

                        print(f"{'Net Expectancy:':<27}${net_expectancy:,.2f}")
                        print(f"{'Net Wins:':<27}{net_wins}")
                        print(f"{'Net Losses:':<27}{net_losses}")
                        print(f"{'Net Break-even Trades:':<27}{net_breakevens}")
                        print(f"{'Net Win Rate:':<27}{net_win_rate:.2f}%")

                        if timed_trades > 0:
                              average_duration = total_duration / timed_trades
                        else:
                              average_duration = 0

                        print("\n" + "=" * 50)
                        print("RISK ANALYTICS")
                        print("=" * 50)
                        print()
                        print(f"{'Average Risk:':<27}${average_risk:,.2f}")
                        print(f"{'Average Realized R:':<27}{average_realized_r:.2f}R")

                        if best_r_trade is not None:
                              print(
                                    f"{'Best R Trade:':<27}#{best_r_idx + 1} "
                                    f"{best_r_trade['symbol']} "
                                    f"({best_r_trade.get('realized_r', 0):.2f}R)"
                              )
                        else:
                              print(f"{'Best R Trade:':<27}N/A")

                        if worst_r_trade is not None:
                              print(
                                    f"{'Worst R Trade:':<27}#{worst_r_idx + 1} "
                                    f"{worst_r_trade['symbol']} "
                                    f"({worst_r_trade.get('realized_r', 0):.2f}R)"
                              )
                        else:
                              print(f"{'Worst R Trade:':<27}N/A")

                        print("\n" + "=" * 50)
                        print("TRADE DURATION")
                        print("=" * 50)
                        print()
                        print(f"{'Average Trade Duration:':<27}{average_duration:.2f} minutes")
                        if timed_trades > 0:
                              print(f"{'Longest trade duration:':<27}{longest_duration} minutes")
                              print(f"{'Shortest trade duration:':<27}{shortest_duration} minutes")
                        else:
                              print(f"{'Longest trade duration:':<27}N/A")
                              print(f"{'Shortest trade duration:':<27}N/A")

                        if earliest_entry_time is not None:
                              print(f"{'Earliest entry time:':<27}{earliest_entry_time.strftime('%H:%M')}")
                              print(f"{'Latest entry time:':<27}{latest_entry_time.strftime('%H:%M')}")
                        else:
                              print(f"{'Earliest entry time:':<27}N/A")
                              print(f"{'Latest entry time:':<27}N/A")

                        streaks = calculate_streaks(filtered_trades)

                        if streaks["current_type"] == "Win":
                              current_streak_display = (
                                    f"{streaks['current_length']} Win"
                                    + ("s" if streaks["current_length"] != 1 else "")
                              )
                        elif streaks["current_type"] == "Loss":
                              current_streak_display = (
                                    f"{streaks['current_length']} Loss"
                                    + ("es" if streaks["current_length"] != 1 else "")
                              )
                        else:
                              current_streak_display = "No Active Streak"

                        longest_winning_display = (
                              f"{streaks['longest_winning']} Win"
                              + ("s" if streaks["longest_winning"] != 1 else "")
                        )
                        longest_losing_display = (
                              f"{streaks['longest_losing']} Loss"
                              + ("es" if streaks["longest_losing"] != 1 else "")
                        )

                        print("\n" + "=" * 50)
                        print("STREAK ANALYTICS")
                        print("=" * 50)
                        print()
                        print(f"{'Current Streak:':<27}{current_streak_display}")
                        print(f"{'Longest Winning Streak:':<27}{longest_winning_display}")
                        print(f"{'Longest Losing Streak:':<27}{longest_losing_display}")

      elif choice == "10":
            display_session_analytics(trades)

      elif choice == "11":
            display_setup_analytics(trades)
            display_strategy_method_analytics(trades)

      elif choice == "12":
            display_time_based_analytics(trades)

      elif choice == "13":
            display_equity_drawdown_history(
                  trades,
                  account
            )

      elif choice == "14":
            if save_trades(trades): 
                  print(
                        "Trades saved. "
                        "(Trades are also saved "
                        "automatically after every "
                        "add, edit, and delete.)"
                  )

            else: 
                  print(
                        "Trades could not be saved. "
                  )

      elif choice == "15":
            export_trades_to_csv(trades)

      elif choice == "16":
            print("Goodbye.")
            break
      else:
            print("Invalid choice.")
      