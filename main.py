import json

valid_directions = ("long", "short")

def load_trades():
      try:
            with open("data/trades.json", "r") as file:
                  return json.load(file)
      except FileNotFoundError:
            return []

def save_trades(trades):
      with open("data/trades.json", "w") as file:
            json.dump(trades, file, indent=4)

def show_menu():
      print("\nAI Trading Journal")
      print("1. Add Trade")
      print("2. View Trades")
      print("3. Delete Trade")
      print("4. Edit Trade")
      print("5. Trading Statistics")
      print("6. Search Trades")
      print("7. Save Trades")
      print("8. Quit")

def calculate_pnl(direction, entry, exit_price):
      if direction == "long":
            return exit_price - entry
      else:
            return entry - exit_price

def calculate_result(pnl):
      if pnl > 0:
            return "Win"
      elif pnl < 0:
            return "Loss"
      else:
            return "Break-even"

trades = load_trades()

while True:
      show_menu()
      choice = input("Choose an option: ").strip()

      if choice == "1":
            symbol = input("Enter symbol ").lower().strip()
            direction = input("Long or short: ").lower().strip()

            if direction not in valid_directions:
                  print("Invalid direction")
                  continue
            try:
                 entry = float(input("Entry price: "))
                 exit_price = float(input("Exit price: "))
            except ValueError:
                  print ("Invalid price.")
                  continue
      
            setup = input("Enter setup: ").strip()
            session = input("Enter session: ").strip()
            notes = input("Enter notes: ").strip()
            mistake = input("Enter mistake: ").strip()

            pnl = calculate_pnl(direction, entry, exit_price)
            result = calculate_result(pnl)
      
            trade = {
                  "symbol": symbol,
                  "direction": direction,
                  "entry": entry,
                  "exit": exit_price,
                  "pnl": pnl,
                  "result": result,
                  "setup": setup,
                  "session": session,
                  "notes": notes,
                  "mistake": mistake
            }
            trades.append(trade)
            save_trades(trades)

            print("Trade added.")

      elif choice == "2":
            if len(trades) == 0:
                  print("No trades yet.")
            else:
                  for i in range(len(trades)):
                        trade = trades[i]
                        print(f"\nTrade #{i + 1}")
                        print(f"Symbol: {trade['symbol']}")
                        print(f"Direction: {trade['direction']}")
                        print(f"Entry: {trade['entry']}")
                        print(f"Exit: {trade['exit']}")
                        print(f"P/L: {trade['pnl']}")
                        print(f"Result: {trade['result']}")
                        print(f"Setup: {trade.get('setup', 'N/A')}")
                        print(f"Session: {trade.get('session', 'N/A')}")
                        print(f"Notes: {trade.get('notes', 'N/A')}")
                        print(f"Mistake: {trade.get('mistake', 'N/A')}")

      elif choice == "3":
            if len(trades) == 0:
                  print("No trades to delete.")
            else:
                  for i in range(len(trades)):
                        trade = trades[i]
                        print(f"{i + 1}. {trade['symbol']} {trade['direction']} P/L: {trade['pnl']}")

                  try:
                        trade_number = int(input("Which trade number would you like to delete? "))
                  except ValueError:
                        print("Invalid trade number.")
                        continue

                  delete_index = trade_number - 1

                  if 0 <= delete_index < len(trades):
                        removed_trade = trades.pop(delete_index)
                        save_trades(trades)

                        print(f"Deleted trade: {removed_trade['symbol']}")
                  else:
                        print("Invalid trade number.")

      elif choice == "4":
            if len(trades) == 0:
                  print("No trades to edit.")
                  continue

            for i in range(len(trades)):
                  trade = trades[i]
                  print(f"{i + 1}. {trade['symbol']} {trade['direction']} P/L: {trade['pnl']}")

            try:
                  trade_number = int(input("Which trade number would you like to edit? "))
            except ValueError:
                  print("Invalid trade number.")
                  continue

            edit_index = trade_number - 1

            if 0 <= edit_index < len(trades):
                  new_symbol = input("New Instrument: ")
                  new_direction = input("New direction, long or short: ").lower().strip()

                  if new_direction not in valid_directions:
                        print("Invalid direction")
                        continue

                  try:
                        new_entry = float(input("New entry price: "))
                        new_exit = float(input("New exit price: "))
                  except ValueError:
                        print("Invalid price.")
                        continue

                  new_setup = input("New setup: ").strip()
                  new_session = input("New session: ").strip()
                  new_notes = input("New notes: ").strip()
                  new_mistake = input("New mistake: ").strip()


                  new_pnl = calculate_pnl(new_direction, new_entry, new_exit)
                  new_result = calculate_result(new_pnl)

                  trades[edit_index] = {
                        "symbol": new_symbol,
                        "direction": new_direction,
                        "entry": new_entry,
                        "exit": new_exit,
                        "pnl": new_pnl,
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
                  
                  
      elif choice == "5":
            print("\nTrading Statistics:")

            if len(trades) == 0:
                  print("No trades to calculate statistics.")
            else:
                  total_trades = len(trades)
                  wins = 0
                  losses = 0
                  breakevens = 0
                  total_pnl = 0
                  gross_profit = 0
                  gross_loss = 0
                  average_winning_trade = 0
                  average_losing_trade = 0
                  profit_factor = 0
                  expectancy = 0

                  best_trade = trades[0]
                  worst_trade = trades[0]

                  for trade in trades:
                        pnl = trade['pnl']
                        result = trade['result']

                        total_pnl += pnl

                        if result == "Win":
                              wins += 1
                        elif result == "Loss":
                              losses += 1
                        else:
                              breakevens += 1

                        if trade['pnl'] > best_trade['pnl']:
                              best_trade = trade

                        if trade['pnl'] < worst_trade['pnl']:
                              worst_trade = trade

                  win_rate = (wins / total_trades) * 100
                  average_pnl = total_pnl / total_trades
                  gross_profit = sum(trade['pnl'] for trade in trades if trade['result'] == "Win")
                  gross_loss = sum(abs(trade['pnl']) for trade in trades if trade['result'] == "Loss")
                  average_winning_trade = gross_profit / wins if wins > 0 else 0
                  average_losing_trade = gross_loss / losses if losses > 0 else 0

                  if gross_loss > 0:
                        profit_factor = gross_profit / gross_loss
                  else:
                        profit_factor = None

                  expectancy = average_pnl

                  print("\nTrading Statistics")
                  print(f"Total trades: {total_trades}")
                  print(f"Wins: {wins}")
                  print(f"Losses: {losses}")
                  print(f"Break-even trades: {breakevens}")
                  print(f"Win rate: {win_rate:.2f}%")
                  print(f"Total P/L: {total_pnl:,.2f} pts")
                  print(f"Average P/L: {average_pnl:.2f} pts")
                  print(f"Best trade: {best_trade['symbol']} ({best_trade['pnl']:.2f} pts)")
                  print(f"Worst trade: {worst_trade['symbol']} ({worst_trade['pnl']:.2f} pts)")
                  print(f"Gross profit: {gross_profit:,.2f} pts")
                  print(f"Gross loss: {gross_loss:,.2f} pts")
                  print(f"Average winning trade: {average_winning_trade:,.2f} pts")
                  print(f"Average losing trade: {average_losing_trade:,.2f} pts")

                  if profit_factor is None:
                        print("Profit factor: N/A (no losing trades)")
                  else:
                        print(f"Profit factor: {profit_factor:.2f}")

                  print(f"Expectancy: {expectancy:.2f} pts")

      elif choice == "6":
            if len(trades) == 0: 
                  print("No trades to search")
            else:
                  search_symbol = input("Enter symbol to search: ").lower().strip()
                  found = False

                  for i in range (len(trades)): 
                        trade =trades [i]

                        if trade['symbol'].lower().strip() == search_symbol:
                              print(f"\nTrade #{i + 1}")
                              print(f"symbol: {trade['symbol']}")
                              print(f"Direction: {trade['direction']}")
                              print(f"Entry: {trade['entry']}")
                              print(f"Exit: {trade['exit']}")
                              print(f"P/L: {trade['pnl']}")
                              print(f"Result: {trade['result']}")
                              print(f"Setup: {trade.get('setup', 'N/A')}")
                              print(f"Session: {trade.get('session', 'N/A')}")
                              print(f"Notes: {trade.get('notes', 'N/A')}")
                              print(f"Mistake: {trade.get('mistake', 'N/A')}")

                              found = True

                  if found == False:
                        print("No matching trades found.")

      elif choice == "7":
            save_trades(trades)
            print("Trades saved.")

      elif choice == "8":
            print("Goodbye.")
            break
      else:
            print("Invalid choice.") 
