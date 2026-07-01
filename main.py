


trades = []

valid_directions = ("long", "short") 

while True:
      print("\nAI Trading Journal")
      print("1. Add Trade")
      print("2. View Trades")
      print("3. Delete Trade")
      print("4. Edit Trade")
      print("5. Trading Statistics")
      print("6. Quit")

      choice = input("Choose an option: ")

      if choice == "1":
            symbol = input("Enter symbol: ") 
            direction = input("Long or short: ").lower().strip()

            if direction not in valid_directions:
                  print("Invalid direction")
                  continue
            
            entry = float(input("Entry price: "))
            exit_price = float(input("Exit price: "))

            if direction == "long":
                  pnl = exit_price - entry
            else:
                  pnl = entry - exit_price

            if pnl > 0:
                result = "Win"
            elif pnl <0:
                result = "Loss"
            else:
                result = "Break-even"
            trade = [symbol, direction, entry, exit_price, pnl, result]
            trades.append(trade)

            print("Trade added.")
      elif choice == "2":
            if len(trades) == 0:
                  print("No trades yet.")
            else:
                  for i in range(len(trades)):
                        trade = trades[i]
                        print(f"\nTrade #{i + 1}")
                        print(f"Symbol: {trade[0]}")
                        print(f"Direction: {trade[1]}")
                        print(f"Entry: {trade[2]}")
                        print(f"Exit: {trade[3]}")
                        print(f"P/L: {trade[4]}")
                        print(f"Result: {trade[5]}")
      elif choice == "3":
            if len(trades) == 0:
                  print("No trades to delete.")
            else:
                  for i in range(len(trades)):
                        trade = trades[i]
                        print(f"{i + 1}. {trade[0]} {trade[1]} P/L: {trade[4]}")

                  try:
                        trade_number = int(input("Which trade number would you like to delete? "))
                  except ValueError:
                        print("Invalid trade number.")
                        continue

                  delete_index = trade_number - 1
                  if 0 <= delete_index < len(trades):
                        removed_trade = trades.pop(delete_index)
                        print(f"Deleted trade: {removed_trade[0]}")
                  else:
                        print("Invalid trade number.")

      elif choice == "4":
            if len(trades) == 0:
                  print("No trades to edit.")
                  continue

            for i in range(len(trades)):
                  trade = trades[i]
                  print(f"{i + 1}. {trade[0]} {trade[1]} P/L: {trade[4]}")

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

                  if new_direction == "long":
                        new_pnl = new_exit - new_entry
                  else:
                        new_pnl = new_entry - new_exit

                  if new_pnl > 0:
                        new_result = "Win"
                  elif new_pnl < 0:
                        new_result = "Loss"
                  else:
                        new_result = "Break-even"

                  trades[edit_index] = [new_symbol, new_direction, new_entry, new_exit, new_pnl, new_result]
                  print("Trade updated successfully.")
            else:
                  print("Invalid trade number.")
                  
      elif choice == "5":
            print("Trading Statistics:")
            if len(trades) == 0:
                print("No trades to calculate statistics.")  
            else:
                  total_trades = len(trades)
                  wins = 0
                  losses = 0
                  breakevens = 0
                  total_pnl = 0
                  best_trade = trades[0]
                  worst_trade = trades[0]
                  for trade in trades:
                        pnl = trade[4]
                        result = trade[5]
                        total_pnl += pnl
                        if trade [4] > best_trade[4]:
                              best_trade = trade
                        if trade [4] < worst_trade[4]:
                              worst_trade = trade
                        if result == "Win":
                              wins += 1
                        elif result == "Loss":
                              losses += 1
                        else:
                              breakevens += 1

                  win_rate = (wins / total_trades) * 100
                  average_pnl = total_pnl / total_trades 

                  print("\nTrading Statistics")
                  print(f"Total trades: {total_trades}")
                  print(f"Wins: {wins}")
                  print(f"Losses: {losses}")
                  print(f"Break-even trades: {breakevens}")
                  print(f"Win rate: {win_rate}%")
                  print(f"Total P/L: {total_pnl}")
                  print(f"Average P/L: {average_pnl}")
                  print(f"Best trade: {best_trade[0]} ({best_trade[4]})")
                  print(f"Worst trade: {worst_trade[0]} ({worst_trade[4]})")
      elif choice == "6":
            print("Goodbye.")
            break
      else:
            print("Invalid choice.") 
