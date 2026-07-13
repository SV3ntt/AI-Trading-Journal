import csv
import json
from datetime import datetime, timedelta

valid_directions = ("long", "short")

def load_trades():
      try:
            with open("data/trades.json", "r") as file:
                  trades = json.load(file)
                  for trade in trades:
                        if "pnl" in trade and "points_pnl" not in trade:
                              trade["points_pnl"] = trade["pnl"]
                  return trades
      except FileNotFoundError:
            return []
      except json.JSONDecodeError:
            print("Warning: trades.json is corrupted. Starting with an empty trade list.")
            return []

def save_trades(trades):
      with open("data/trades.json", "w") as file:
            json.dump(trades, file, indent=4)

def load_account(): 
      try: 
            with open("data/account.json", "r") as file: 
                  account = json.load(file) 
                  return account
      except FileNotFoundError:
            return None
      except json.JSONDecodeError:
            print("Warning: account.json is corrupted.")
            return None
      
def save_account(account):
      with open("data/account.json", "w") as file: 
            json.dump(account, file, indent=4)

def show_menu():
      print("\nAI Trading Journal")
      print("1. Account Status")
      print("2. Edit Account")
      print("3. Add Trade")
      print("4. View Trades")
      print("5. Delete Trade")
      print("6. Edit Trade")
      print("7. Trading Statistics")
      print("8. Search / Filter Trades")
      print("9. Filtered Statistics")
      print("10. Save Trades")
      print("11. Export Trades to CSV")
      print("12. Quit")

def export_trades_to_csv(trades): 
      if len(trades) == 0:
            print("No trades to export.")
            return
      
      filename = f"data/trades_export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
      
      headers = [
            "Trade Number", 
            "Date",
            "Symbol",
            "Direction",
            "Entry",
            "Exit",
            "Contracts",
            "Point Value",
            "Points P/L",
            "Dollar P/L",
            "Result",
            "Entry Time",
            "Exit Time",
            "Duration (Minutes)",
            "Setup",
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
                              trade.get("trade_date", "").replace("-", " "),
                              trade.get("symbol", "").upper(),
                              trade.get("direction", ""),
                              round(trade.get("entry", 0), 4),
                              round(trade.get("exit", 0), 4),
                              trade.get("contracts", ""),
                              round(trade.get("point_value", 0), 2),
                              round(trade.get("points_pnl", 0), 2),
                              round(trade.get("dollar_pnl", 0), 2),
                              trade.get("result", ""),
                              trade.get("entry_time", ""),
                              trade.get("exit_time", ""),
                              trade.get("duration", ""),
                              trade.get("setup", ""),
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

def calculate_result(points_pnl):
      if points_pnl > 0:
            return "Win"
      elif points_pnl < 0:
            return "Loss"
      else:
            return "Break-even"
      
def calculate_duration(entry_time, exit_time):
      entry_datetime = datetime.strptime(entry_time, "%H:%M")
      exit_datetime = datetime.strptime(exit_time, "%H:%M")

      if exit_datetime < entry_datetime:
            exit_datetime = exit_datetime + timedelta(days=1)

      duration = exit_datetime - entry_datetime
      duration_minutes = int(duration.total_seconds() / 60)

      return duration_minutes

trades = load_trades()
account = load_account()

while True:
      show_menu()
      choice = input("Choose an option: ").strip()

      if choice == "1":
            if account is None: 
                  print("\nNo account has been created yet. Please create an account first.")
            
                  account_name = input("Enter account name: ").strip()

                  if account_name == "":
                        print("Account name cannot be blank.")
                        continue

                  print("\nAccount Types")
                  print("1. Personal")
                  print("2. Evaluation")
                  print("3. Funded")

                  account_type_choice = input ("Choose account type: ").strip()

                  if account_type_choice == "1":
                        account_type = "Personal"
                  elif account_type_choice == "2":
                        account_type = "Evaluation"
                  elif account_type_choice == "3":
                        account_type = "Funded"
                  else:
                        print("Invalid account type")
                        continue

                  try:
                        starting_balance = float(input("Enter starting balance: $").strip())     
                  except ValueError:
                        print("Invalid starting balance.")
                        continue

                  if starting_balance < 0:
                        print(f"Starting balance must be greater than or equal to $0.")
                        continue

                  account = {
                        "name": account_name,
                        "type": account_type,
                        "starting_balance": starting_balance,
                        "high_water_mark": starting_balance
                  }
                  save_account(account)
                  print(f"Account '{account_name}' created successfully.")

            total_dollar_pnl = sum(
                  trade.get("dollar_pnl", 0)
                  for trade in trades
            )

            starting_balance = account["starting_balance"]
            current_balance = starting_balance + total_dollar_pnl
            net_profit = total_dollar_pnl
            growth_percentage = (net_profit / starting_balance) * 100 if starting_balance != 0 else 0

            high_water_mark = account.get("high_water_mark", starting_balance)

            if current_balance > high_water_mark:
                  high_water_mark = current_balance
                  account["high_water_mark"] = high_water_mark
                  save_account(account)
                  
            drawdown = current_balance - high_water_mark

            if high_water_mark > 0: 
                  drawdown_percentage = (drawdown / high_water_mark) * 100
            else:
                  drawdown_percentage = 0

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
            
            if drawdown < 0:
                  print(f"Drawdown: ${drawdown:,.2f}")
                  print(f"Drawdown Percentage: {drawdown_percentage:.2f}%")
            else: 
                  print("Drawdown: $0.00")
                  print("Drawdown Percentage: 0.00%")
                  

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

            account_type_choice = input(
                  "Choose new account type: "
                  ).strip()
            if account_type_choice == "":
                  new_account_type = account["type"]
            elif account_type_choice == "1":
                  new_account_type = "Personal"
            elif account_type_choice == "2":
                  new_account_type = "Evaluation"
            elif account_type_choice == "3":
                  new_account_type = "Funded"
            else:
                  print("Invalid account type.")
                  continue

            new_starting_balance_input = input(
                  f"Starting Balance (current: ${account['starting_balance']:,.2f}): $"
            ).strip()
            if new_starting_balance_input == "":
                  new_starting_balance = account["starting_balance"]
            else: 
                  try:
                        new_starting_balance = float(
                              new_starting_balance_input    
                        )
                  except ValueError:
                        print("Invalid starting balance.")
                        continue
                  if new_starting_balance < 0:
                        print("Starting balance must be greater than or equal to $0.")
                        continue

            old_starting_balance = account["starting_balance"]

            account["name"] = new_account_name
            account["type"] = new_account_type
            account["starting_balance"] = new_starting_balance

            if new_starting_balance != old_starting_balance:
                  total_dollar_pnl = sum(
                        trade.get("dollar_pnl", 0)
                        for trade in trades
                  )

                  recalculated_balance = (
                        new_starting_balance + total_dollar_pnl
                  )

                  account["high_water_mark"] = max(
                        new_starting_balance, 
                        recalculated_balance
                  )

            save_account(account)
            print("Account updated successfully.")

      elif choice == "3":
            symbol = input("Enter symbol: ").lower().strip()

            if symbol == "":
                  print("Symbol cannot be blank.")
                  continue

            direction = input("Long or short: ").lower().strip()

            if direction not in valid_directions:
                  print("Invalid direction")
                  continue
            try:
                 entry = float(input("Entry price: "))
                 exit_price = float(input("Exit price: "))
                 contracts = int(input("Number of contracts: "))
                 point_value = float(input("Point value: ")) 
                 
            except ValueError:
                  print ("Invalid price, contracts, or point value.")
                  continue

            if entry <= 0 or exit_price <= 0:
                  print("Entry and exit prices must be greater than 0.")
                  continue
            if contracts <= 0:
                  print("Contracts must be greater than 0.")
                  continue
            if point_value <= 0:
                  print("Point value must be greater than 0.")
                  continue

            try:
                  trade_date = input("Trade date (YYYY-MM-DD): ").strip().replace(" ", "-")
                  
                  parsed_date = datetime.strptime(trade_date, "%Y-%m-%d")
                  trade_date = parsed_date.strftime("%Y-%m-%d")

            except ValueError:
                  print("Invalid date. Please use YYYY-MM-DD format.")
                  continue

            try:
                  entry_time = input("Entry time (HH:MM): ").strip()
                  exit_time = input("Exit time (HH:MM): ").strip()
                  duration = calculate_duration(entry_time, exit_time)
            except ValueError:
                  print("Invalid time format. Please use HH:MM.")
                  continue

            setup = input("Enter setup: ").strip()
            session = input("Enter session: ").strip()
            notes = input("Enter notes: ").strip()
            mistake = input("Enter mistake: ").strip()

            points_pnl = calculate_points_pnl(direction, entry, exit_price)
            dollar_pnl = calculate_dollar_pnl(points_pnl, point_value, contracts)
            result = calculate_result(points_pnl)
            
      
            trade = {
                  "symbol": symbol,
                  "direction": direction,
                  "entry": entry,
                  "exit": exit_price,
                  "contracts": contracts,
                  "point_value": point_value,

                  "trade_date": trade_date,
                  "entry_time": entry_time,
                  "exit_time": exit_time,
                  "duration": duration,

                  "points_pnl": points_pnl,
                  "dollar_pnl": dollar_pnl,
                  "result": result,
                  

                  "setup": setup,
                  "session": session,
                  "notes": notes,
                  "mistake": mistake
            }
            trades.append(trade)
            save_trades(trades)

            print("Trade added.")

      elif choice == "4":
            if len(trades) == 0:
                  print("No trades yet.")
            else:
                  print(f"\nTrades ({len(trades)} total):")
                  for i in range(len(trades)):
                        trade = trades[i]
                        print(f"  {i + 1}. {trade['symbol'].upper()} | {trade.get('trade_date', 'N/A')} | {trade['direction']} | {trade['result']} | {trade['points_pnl']:,.2f} pts | ${trade.get('dollar_pnl', 0):,.2f}")

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
                        print(f"Date: {trade.get('trade_date', 'N/A')}")
                        print(f"Entry: {trade['entry']}")
                        print(f"Exit: {trade['exit']}")
                        print(f"Contracts: {trade.get('contracts', 'N/A')}")

                        point_value = trade.get("point_value")
                        if point_value is None:
                              print("Point Value: N/A")
                        else:
                              print(f"Point Value: ${point_value:,.2f}")

                        print(f"Entry Time: {trade.get('entry_time', 'N/A')}")
                        print(f"Exit Time: {trade.get('exit_time', 'N/A')}")
                        print(f"Duration: {trade.get('duration', 'N/A')} minutes")
                        print(f"Points P/L: {trade['points_pnl']:,.2f} pts")
                        print(f"Dollar P/L: ${trade.get('dollar_pnl', 0):,.2f}")
                        print(f"Result: {trade['result']}")
                        print(f"Setup: {trade.get('setup', 'N/A')}")
                        print(f"Session: {trade.get('session', 'N/A')}")
                        print(f"Notes: {trade.get('notes', 'N/A')}")
                        print(f"Mistake: {trade.get('mistake', 'N/A')}")
                  else:
                        print("Invalid trade number.")

      elif choice == "5":
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
                        confirm = input(f"Are you sure you want to delete {trade_to_delete['symbol']} ({trade_to_delete['result']}, {trade_to_delete['points_pnl']:,.2f} pts)? (yes/no): ").lower().strip()
                        if confirm == "yes":
                              removed_trade = trades.pop(delete_index)
                              save_trades(trades)
                              print(f"Deleted trade: {removed_trade['symbol']}")
                        else:
                              print("Delete cancelled.")
                  else:
                        print("Invalid trade number.")

      elif choice == "6":
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

                  symbol_input = input(f"Symbol (current: {current['symbol']}): ").lower().strip()
                  new_symbol = symbol_input if symbol_input != "" else current["symbol"]

                  direction_input = input(f"Direction (current: {current['direction']}): ").lower().strip()
                  if direction_input == "":
                        new_direction = current["direction"]
                  elif direction_input not in valid_directions:
                        print("Invalid direction.")
                        continue
                  else:
                        new_direction = direction_input

                  try:
                        entry_input = input(f"Entry price (current: {current['entry']}): ").strip()
                        new_entry = float(entry_input) if entry_input != "" else current["entry"]

                        exit_input = input(f"Exit price (current: {current['exit']}): ").strip()
                        new_exit = float(exit_input) if exit_input != "" else current["exit"]

                        contracts_input = input(f"Contracts (current: {current.get('contracts', 'N/A')}): ").strip()
                        new_contracts = int(contracts_input) if contracts_input != "" else current.get("contracts", 1)

                        point_value_input = input(f"Point value (current: {current.get('point_value', 'N/A')}): ").strip()
                        new_point_value = float(point_value_input) if point_value_input != "" else current.get("point_value", 1.0)

                  except ValueError:
                        print("Invalid price, contracts, or point value.")
                        continue

                  if new_entry <= 0 or new_exit <= 0:
                        print("Entry and exit prices must be greater than 0.")
                        continue
                  if new_contracts <= 0:
                        print("Contracts must be greater than 0.")
                        continue
                  if new_point_value <= 0:
                        print("Point value must be greater than 0.")
                        continue

                  try:
                        date_input = input(f"Trade date (current: {current.get('trade_date', 'N/A')}): ").strip().replace(" ", "-")
                        if date_input == "" or date_input == "-":
                              new_trade_date = current.get("trade_date", "")
                        else:
                              parsed_date = datetime.strptime(date_input, "%Y-%m-%d")
                              new_trade_date = parsed_date.strftime("%Y-%m-%d")
                  except ValueError:
                        print("Invalid date. Please use YYYY-MM-DD format.")
                        continue

                  try:
                        entry_time_input = input(f"Entry time (current: {current.get('entry_time', 'N/A')}): ").strip()
                        new_entry_time = entry_time_input if entry_time_input != "" else current.get("entry_time", "")

                        exit_time_input = input(f"Exit time (current: {current.get('exit_time', 'N/A')}): ").strip()
                        new_exit_time = exit_time_input if exit_time_input != "" else current.get("exit_time", "")

                        if new_entry_time and new_exit_time:
                              new_duration = calculate_duration(new_entry_time, new_exit_time)
                        else:
                              new_duration = current.get("duration", None)

                  except ValueError:
                        print("Invalid time format. Please use HH:MM.")
                        continue

                  setup_input = input(f"Setup (current: {current.get('setup', 'N/A')}): ").strip()
                  new_setup = setup_input if setup_input != "" else current.get("setup", "")

                  session_input = input(f"Session (current: {current.get('session', 'N/A')}): ").strip()
                  new_session = session_input if session_input != "" else current.get("session", "")

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
                  new_result = calculate_result(new_points_pnl)

                  trades[edit_index] = {
                        "symbol": new_symbol,
                        "direction": new_direction,
                        "entry": new_entry,
                        "exit": new_exit,
                        "contracts": new_contracts,
                        "point_value": new_point_value,

                        "trade_date": new_trade_date,
                        "entry_time": new_entry_time,
                        "exit_time": new_exit_time,
                        "duration": new_duration,

                        "points_pnl": new_points_pnl,
                        "dollar_pnl": new_dollar_pnl,
                        "result": new_result,

                        "setup": new_setup,
                        "session": new_session,
                        "notes": new_notes,
                        "mistake": new_mistake
                  }

                  save_trades(trades)

                  print ("Trade updated successfully.")
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

                  total_points_pnl = 0
                  total_dollar_pnl = 0

                  total_duration = 0
                  timed_trades = 0 
                  longest_duration = None
                  shortest_duration = None
                  earliest_entry_time = None 
                  latest_entry_time = None

                  best_points_trade = trades[0]
                  worst_points_trade = trades[0]
                  best_dollar_trade = trades[0]
                  worst_dollar_trade = trades[0]
                  best_points_idx = 0
                  worst_points_idx = 0
                  best_dollar_idx = 0
                  worst_dollar_idx = 0

                  for i, trade in enumerate(trades):
                        points_pnl = trade['points_pnl']
                        dollar_pnl = trade.get('dollar_pnl', 0)
                        result = trade['result']

                        total_points_pnl += points_pnl
                        total_dollar_pnl += dollar_pnl
                  
                        if result == "Win":
                              wins += 1
                        elif result == "Loss":
                              losses += 1
                        else:
                              breakevens += 1

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

                  average_points_pnl = total_points_pnl / total_trades
                  average_dollar_pnl = total_dollar_pnl / total_trades

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

                  if timed_trades > 0: 
                        average_duration = total_duration / timed_trades 
                  else: 
                        average_duration = 0

                  print("\nTrading Statistics")
                  print(f"Total trades: {total_trades}")
                  print(f"Wins: {wins}")
                  print(f"Losses: {losses}")
                  print(f"Break-even trades: {breakevens}")
                  print(f"Win rate: {win_rate:.2f}%")

                  print("\nPoints P/L Statistics")
                  print(f"Total points P/L: {total_points_pnl:,.2f} pts")
                  print(f"Average points P/L: {average_points_pnl:.2f} pts")
                  print(
                        f"Best Points Trade: #{best_points_idx + 1} {best_points_trade['symbol']} "
                        f"({best_points_trade['points_pnl']:.2f} pts)"
                  )
                  print(
                        f"Worst Points Trade: #{worst_points_idx + 1} {worst_points_trade['symbol']} "
                        f"({worst_points_trade['points_pnl']:.2f} pts)"
                  )
                  print(f"Gross Points Profit: {gross_points_profit:,.2f} pts")
                  print(f"Gross Points Loss: -{gross_points_loss:,.2f} pts")
                  print(f"Average Points Win: {average_points_win:,.2f} pts")
                  print(f"Average Points Loss: -{average_points_loss:,.2f} pts")

                  if points_profit_factor is None:
                        print("Points Profit Factor: N/A (no losing trades)")
                  else:
                        print(f"Points Profit Factor: {points_profit_factor:.2f}")

                  print(f"Points Expectancy: {points_expectancy:.2f} pts")

                  print("\nDollar P/L Statistics")
                  print(f"Total dollar P/L: ${total_dollar_pnl:,.2f}")
                  print(f"Average dollar P/L: ${average_dollar_pnl:,.2f}")
                  print(
                        f"Best Dollar Trade: #{best_dollar_idx + 1} {best_dollar_trade['symbol']} "
                        f"(${best_dollar_trade.get('dollar_pnl', 0):,.2f})"
                  )
                  print(
                        f"Worst Dollar Trade: #{worst_dollar_idx + 1} {worst_dollar_trade['symbol']} "
                        f"(${worst_dollar_trade.get('dollar_pnl', 0):,.2f})"
                  )
                  print(f"Gross Dollar Profit: ${gross_dollar_profit:,.2f}")
                  print(f"Gross Dollar Loss: -${gross_dollar_loss:,.2f}")
                  print(f"Average Dollar Win: ${average_dollar_win:,.2f}")
                  print(f"Average Dollar Loss: -${average_dollar_loss:,.2f}")

                  if dollar_profit_factor is None:
                        print("Dollar Profit Factor: N/A (no losing trades)")
                  else:
                        print(f"Dollar Profit Factor: {dollar_profit_factor:.2f}")

                  print(f"Dollar Expectancy: ${dollar_expectancy:,.2f}")

                  print("\nTrade Duration Statistics")
                  print(f"Average trade duration: {average_duration:.2f} minutes")
                  if timed_trades > 0:
                        print(f"Longest trade duration: {longest_duration} minutes")
                        print(f"Shortest trade duration: {shortest_duration} minutes")
                  else:
                        print("Longest trade duration: N/A")
                        print("Shortest trade duration: N/A")

                  if earliest_entry_time is not None:
                        print(f"Earliest entry time: {earliest_entry_time.strftime('%H:%M')}")
                        print(f"Latest entry time: {latest_entry_time.strftime('%H:%M')}")
                  else:
                        print("Earliest entry time: N/A")
                        print("Latest entry time: N/A")

      elif choice == "8":
            if len(trades) == 0:
                  print("No trades to search")
            else:
                  print("\nMulti-Filter Search.")
                  print("Press Enter to skip any filter.")

                  symbol_filter = input("Symbol: ").lower().strip()
                  direction_filter = input ("Direction: ").lower().strip()
                  result_filter = input ("Result: ").lower().strip()
                  setup_filter = input ("setup: ").lower().strip()
                  session_filter = input ("session: ").lower().strip()

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
                        if setup_filter != "" and trade.get("setup", "").lower().strip() != setup_filter:
                              matches = False
                        if session_filter != "" and trade.get("session", "").lower().strip() != session_filter:
                              matches = False 

                        if matches:
                              print(f"\nTrade #{i + 1}")
                              print(f"Symbol: {trade['symbol']}")
                              print(f"Direction: {trade['direction']}")
                              print(f"Date: {trade.get('trade_date', 'N/A')}")
                              print(f"Entry: {trade['entry']}")
                              print(f"Exit: {trade['exit']}")
                              print(f"Entry Time: {trade.get('entry_time', 'N/A')}")
                              print(f"Exit Time: {trade.get('exit_time', 'N/A')}")
                              print(f"Duration: {trade.get('duration', 'N/A')} minutes")
                              print(f"Points P/L: {trade['points_pnl']:,.2f} pts")
                              print(f"Dollar P/L: ${trade.get('dollar_pnl', 0):,.2f}")
                              print(f"Contracts: {trade.get('contracts', 'N/A')}")
                              point_value = trade.get("point_value")
                              if point_value is None:
                                    print("Point Value: N/A")
                              else:
                                    print(f"Point Value: ${point_value:,.2f}")
                              print(f"Result: {trade['result']}")
                              print(f"Setup: {trade.get('setup', 'N/A')}")
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
                  setup_filter = input ("Setup: ").lower().strip()
                  session_filter = input ("Session: ").lower().strip()

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
                        if setup_filter != "" and trade.get("setup", "").lower().strip() != setup_filter:
                              matches = False 
                        if session_filter != "" and trade.get("session", "").lower().strip() != session_filter:
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

                        total_points_pnl = 0
                        total_dollar_pnl = 0

                        best_points_trade = filtered_trades[0]
                        worst_points_trade = filtered_trades[0]
                        best_dollar_trade = filtered_trades[0]
                        worst_dollar_trade = filtered_trades[0]
                        best_points_idx = filtered_indices[0]
                        worst_points_idx = filtered_indices[0]
                        best_dollar_idx = filtered_indices[0]
                        worst_dollar_idx = filtered_indices[0]

                        total_duration = 0
                        timed_trades = 0
                        longest_duration = None
                        shortest_duration = None
                        earliest_entry_time = None
                        latest_entry_time = None
                        
                        for i, trade in enumerate(filtered_trades): 
                              points_pnl = trade["points_pnl"]
                              dollar_pnl = trade.get("dollar_pnl", 0)
                              result = trade["result"]    

                              total_points_pnl += points_pnl
                              total_dollar_pnl += dollar_pnl

                              if result == "Win": 
                                    wins += 1
                              elif result == "Loss":
                                    losses += 1
                              else: 
                                    breakevens += 1

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

                        average_points_pnl = total_points_pnl / total_trades
                        average_dollar_pnl = total_dollar_pnl / total_trades
                        
                        gross_profit = sum(
                              trade["points_pnl"] 
                              for trade in filtered_trades 
                              if trade["points_pnl"] > 0
                        )

                        gross_loss = sum(
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

                        average_winning_trade = gross_profit / wins if wins > 0 else 0
                        average_points_loss = gross_loss / losses if losses > 0 else 0

                        average_dollar_win = gross_dollar_profit / wins if wins > 0 else 0
                        average_dollar_loss = gross_dollar_loss / losses if losses > 0 else 0

                        if gross_loss > 0:
                              profit_factor = gross_profit / gross_loss
                        else:
                              profit_factor = None
                        
                        if gross_dollar_loss > 0:
                              dollar_profit_factor = gross_dollar_profit / gross_dollar_loss
                        else:
                              dollar_profit_factor = None

                        points_expectancy = average_points_pnl
                        dollar_expectancy = average_dollar_pnl

                        print("\nFiltered Trading Statistics")
                        print(f"Total trades: {total_trades}")
                        print(f"Wins: {wins}")
                        print(f"Losses: {losses}")
                        print(f"Break-even trades: {breakevens}")
                        print(f"Win rate: {win_rate:.2f}%")

                        print("\nPoints P/L Statistics")
                        print(f"Total points P/L: {total_points_pnl:,.2f} pts")
                        print(f"Average points P/L: {average_points_pnl:.2f} pts")
                        print(
                              f"Best Points Trade: #{best_points_idx + 1} {best_points_trade['symbol']} "
                              f"({best_points_trade['points_pnl']:.2f} pts)"
                        )
                        print(
                              f"Worst Points Trade: #{worst_points_idx + 1} {worst_points_trade['symbol']} "
                              f"({worst_points_trade['points_pnl']:.2f} pts)"
                        )
                        print(f"Gross Points Profit: {gross_profit:,.2f} pts")
                        print(f"Gross Points Loss: -{gross_loss:,.2f} pts")
                        print(f"Average Points Win: {average_winning_trade:,.2f} pts")
                        print(f"Average Points Loss: -{average_points_loss:,.2f} pts")

                        if profit_factor is None:
                              print("Points Profit Factor: N/A (no losing trades)")
                        else:
                              print(f"Points Profit Factor: {profit_factor:.2f}")
                        
                        print(f"Points Expectancy: {points_expectancy:.2f} pts")

                        print("\nDollar P/L Statistics")
                        print(f"Total dollar P/L: ${total_dollar_pnl:,.2f}")
                        print(f"Average dollar P/L: ${average_dollar_pnl:,.2f}")
                        print(
                              f"Best Dollar Trade: #{best_dollar_idx + 1} {best_dollar_trade['symbol']} "
                              f"(${best_dollar_trade.get('dollar_pnl', 0):,.2f})"
                        )
                        print(
                              f"Worst Dollar Trade: #{worst_dollar_idx + 1} {worst_dollar_trade['symbol']} "
                              f"(${worst_dollar_trade.get('dollar_pnl', 0):,.2f})"
                        )
                        print(f"Gross Dollar Profit: ${gross_dollar_profit:,.2f}")
                        print(f"Gross Dollar Loss: -${gross_dollar_loss:,.2f}")
                        print(f"Average Dollar Win: ${average_dollar_win:,.2f}")
                        print(f"Average Dollar Loss: -${average_dollar_loss:,.2f}")

                        if dollar_profit_factor is None:
                              print("Dollar Profit Factor: N/A (no losing trades)")
                        else:
                              print(f"Dollar Profit Factor: {dollar_profit_factor:.2f}")

                        print(f"Dollar Expectancy: ${dollar_expectancy:,.2f}")

                        if timed_trades > 0:
                              average_duration = total_duration / timed_trades
                        else:
                              average_duration = 0

                        print("\nTrade Duration Statistics")
                        print(f"Average trade duration: {average_duration:.2f} minutes")
                        if timed_trades > 0:
                              print(f"Longest trade duration: {longest_duration} minutes")
                              print(f"Shortest trade duration: {shortest_duration} minutes")
                        else:
                              print("Longest trade duration: N/A")
                              print("Shortest trade duration: N/A")

                        if earliest_entry_time is not None:
                              print(f"Earliest entry time: {earliest_entry_time.strftime('%H:%M')}")
                              print(f"Latest entry time: {latest_entry_time.strftime('%H:%M')}")
                        else:
                              print("Earliest entry time: N/A")
                              print("Latest entry time: N/A")

      elif choice == "10":
            save_trades(trades)
            print("Trades saved. (Trades are also saved automatically after every add, edit, and delete.)")

      elif choice == "11":
            export_trades_to_csv(trades)

      elif choice == "12":
            print("Goodbye.")
            break
      else:
            print("Invalid choice.")
