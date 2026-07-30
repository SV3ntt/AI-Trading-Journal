from datetime import datetime

from journal.constants import (
    FLOATING_POINT_TOLERANCE,
    STANDARD_FOREX_CURRENCIES,
    STANDARD_LOT_UNITS,
    VALID_MARKET_TYPES,
    valid_directions,
)
from journal.calculations import (
    calculate_duration,
    calculate_net_result,
    get_finite_number,
    get_positive_integer,
)
from journal.markets import (
    get_known_futures_profile,
    get_standard_forex_pip_profile,
    normalize_forex_symbol,
)
from journal.analytics import (
    calculate_equity_drawdown_history,
    calculate_streaks,
    compute_unit_performance_stats,
    dedupe_case_insensitive,
    determine_session,
    get_setup_components,
    get_strategy_method,
    get_strategy_methods,
    normalize_session_name,
    normalize_setup_name,
    normalize_strategy_method,
    split_setup_components,
    split_strategy_methods,
    trade_is_in_date_range,
)
from journal.validation import validate_and_normalize_trade
from journal.storage import export_trades_to_csv, save_account, save_trades
from journal.display import (
    display_equity_drawdown_history,
    display_session_analytics,
    display_setup_analytics,
    display_strategy_method_analytics,
    display_time_based_analytics,
    format_drawdown,
    format_drawdown_percentage,
    format_trade_price,
    format_trade_unit_summary,
    print_futures_instrument_profile,
    print_trade_unit_detail,
    print_unit_performance_stats,
    show_menu,
)
from journal.prompts import (
    ensure_account_currency,
    get_optional_date,
    prompt_choice,
    prompt_date,
    prompt_finite_number,
    prompt_forex_price,
    prompt_futures_price,
    prompt_positive_integer,
    prompt_required_text,
    prompt_time,
    resolve_forex_pair_profile,
    resolve_forex_pip_value,
    resolve_forex_pip_value_for_edit,
    resolve_futures_tick_metadata,
)


def handle_account_status(trades, account):
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
                  return account

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
      print(
            "Account Currency: "
            f"{account.get('account_currency') or 'Not set'}"
      )
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

      return account

def handle_edit_account(account, trades):
      if account is None:
            print("\nNo account has been created yet. Please create an account first.")
            return account

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

      current_account_currency = account.get(
            "account_currency"
      )

      while True:
            account_currency_input = input(
                  (
                        "Account Currency "
                        f"(current: "
                        f"{current_account_currency or 'Not set'}"
                        "): "
                  )
            ).strip().upper()

            if account_currency_input == "":
                  new_account_currency = (
                        current_account_currency
                  )
                  break

            if (
                  len(account_currency_input) == 3
                  and account_currency_input.isalpha()
                  and account_currency_input
                  in STANDARD_FOREX_CURRENCIES
            ):
                  new_account_currency = (
                        account_currency_input
                  )
                  break

            print(
                  "Account currency must be a "
                  "recognized three-letter currency "
                  "code."
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
            "account_currency": new_account_currency,

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

      return account

def handle_add_trade(trades, account):
      market_type = prompt_choice(
            "Market type (Futures/Forex): ",
            VALID_MARKET_TYPES,
            "Market type must be futures or forex."
      )

      symbol = prompt_required_text(
            "Enter symbol: ",
            "Symbol"
      ).lower()

      direction = prompt_choice(
            "Enter direction (long/short): ",
            valid_directions,
            "Direction must be long or short."
      )

      if market_type == "futures":
            contracts = prompt_positive_integer(
                  "Enter number of contracts: ",
                  "Contracts"
            )

            tick_size, tick_value = (
                  resolve_futures_tick_metadata(symbol)
            )

            entry = prompt_futures_price(
                  "Enter entry price: $",
                  "Entry price",
                  tick_size
            )

            exit_price = prompt_futures_price(
                  "Enter exit price: $",
                  "Exit price",
                  tick_size
            )

            lot_size = None
            pip_size = None
            pip_value = None
            price_precision = None

            account_currency = None
            conversion_rate = None
            conversion_pair = None
            conversion_timestamp = None
            conversion_rate_source = None
      else:
            ensure_account_currency(account)

            lot_size = prompt_finite_number(
                  "Enter lot size: ",
                  "Lot size",
                  minimum=0,
                  minimum_is_strict=True
            )

            pip_size, price_precision, is_standard_pair = (
                  resolve_forex_pair_profile(symbol)
            )

            entry = prompt_forex_price(
                  "Enter entry price: ",
                  "Entry price",
                  price_precision
            )

            exit_price = prompt_forex_price(
                  "Enter exit price: ",
                  "Exit price",
                  price_precision
            )

            contracts = None
            tick_size = None
            tick_value = None

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

      if market_type == "forex":
            pip_value_info = resolve_forex_pip_value(
                  symbol=symbol,
                  pip_size=pip_size,
                  price_precision=price_precision,
                  is_standard_pair=is_standard_pair,
                  account=account,
                  exit_price=exit_price,
                  exit_date=trade_date,
                  exit_time=exit_time,
            )

            pip_value = pip_value_info["pip_value"]
            account_currency = account.get("account_currency")
            conversion_rate = pip_value_info["conversion_rate"]
            conversion_pair = pip_value_info["conversion_pair"]
            conversion_timestamp = pip_value_info[
                  "conversion_timestamp"
            ]
            conversion_rate_source = pip_value_info[
                  "conversion_rate_source"
            ]

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

      trade = {
            "symbol": symbol,
            "direction": direction,
            "market_type": market_type,

            "entry": entry,
            "exit": exit_price,

            "contracts": contracts,
            "tick_size": tick_size,
            "tick_value": tick_value,

            "lot_size": lot_size,
            "pip_size": pip_size,
            "pip_value": pip_value,
            "price_precision": price_precision,

            "standard_lot_units": STANDARD_LOT_UNITS,
            "account_currency": account_currency,
            "conversion_rate": conversion_rate,
            "conversion_pair": conversion_pair,
            "conversion_timestamp": conversion_timestamp,
            "conversion_rate_source": conversion_rate_source,

            "commission": commission,
            "risk_amount": risk_amount,

            "trade_date": trade_date,
            "entry_time": entry_time,
            "exit_time": exit_time,

            "strategy_methods": strategy_methods,
            "setup_components": setup_components,
            "notes": notes,
            "mistake": mistake
      }

      normalized_trade, errors = validate_and_normalize_trade(trade)

      if errors:
            print(
                  "Trade was not added due to the "
                  "following errors:"
            )

            for error in errors:
                  print(f"  - {error}")

            return

      trades.append(normalized_trade)

      if save_trades(trades):
            print("Trade added successfully.")

      else:
            trades.pop()

            print(
                  "Trade was not added because it "
                  "could not be saved."
            )

def handle_view_trades(trades):
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
                        f"{format_trade_unit_summary(trade)} | "
                        f"Net: ${net_pnl:,.2f}"
                  )

            view_input = input("\nEnter a trade number for full details, or press Enter to go back: ").strip()

            if view_input == "":
                  return

            try:
                  view_number = int(view_input)
            except ValueError:
                  print("Invalid trade number.")
                  return

            view_index = view_number - 1

            if 0 <= view_index < len(trades):
                  trade = trades[view_index]
                  print(f"\nTrade #{view_number}")
                  print(f"Symbol: {trade['symbol']}")
                  print(f"Direction: {trade['direction']}")
                  print(f"Date: {trade.get('trade_date', 'N/A').replace('-', ' ')}")

                  print(f"Market Type: {trade.get('market_type', 'futures')}")
                  print(f"Entry: {format_trade_price(trade, 'entry')}")
                  print(f"Exit: {format_trade_price(trade, 'exit')}")

                  print_trade_unit_detail(trade)

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

def handle_edit_trade(trades, account):
      if len(trades) == 0:
            print("No trades to edit.")
            return

      for i in range(len(trades)):
            trade = trades[i]
            print(f"{i + 1}. {trade['symbol']} {trade['direction']} {format_trade_unit_summary(trade)}")

      try:
            trade_number = int(input("Which trade number would you like to edit? "))
      except ValueError:
            print("Invalid trade number.")
            return

      edit_index = trade_number - 1

      if 0 <= edit_index < len(trades):
            current = trades[edit_index]
            current_market_type = current.get(
                  "market_type",
                  "futures"
            )

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

            new_market_type = prompt_choice(
                  (
                        "Market type "
                        f"(current: "
                        f"{current_market_type}): "
                  ),
                  VALID_MARKET_TYPES,
                  (
                        "Market type must be "
                        "futures or forex."
                  ),
                  default=current_market_type
            )

            new_contracts = None
            new_tick_size = None
            new_tick_value = None
            new_point_value = current.get("point_value")

            new_lot_size = None
            new_pip_size = None
            new_pip_value = None
            new_price_precision = None

            try:
                  if new_market_type == "futures":
                        if current_market_type == "futures":
                              new_contracts = (
                                    prompt_positive_integer(
                                          (
                                                "Contracts "
                                                f"(current: "
                                                f"{current.get('contracts')}): "
                                          ),
                                          "Contracts",
                                          default=(
                                                current.get(
                                                      "contracts"
                                                )
                                          )
                                    )
                              )

                              has_current_tick_metadata = (
                                    current.get("tick_size")
                                    is not None
                                    and current.get("tick_value")
                                    is not None
                              )

                              if has_current_tick_metadata:
                                    recognized_profile = (
                                          get_known_futures_profile(
                                                new_symbol
                                          )
                                    )

                                    if recognized_profile is not None:
                                          implied_point_value = (
                                                recognized_profile[
                                                      "point_value"
                                                ]
                                          )

                                          existing_point_value = (
                                                current.get(
                                                      "point_value"
                                                )
                                          )

                                          if (
                                                existing_point_value
                                                is not None
                                                and abs(
                                                      implied_point_value
                                                      - existing_point_value
                                                )
                                                >= FLOATING_POINT_TOLERANCE
                                          ):
                                                print(
                                                      "The built-in "
                                                      "specification "
                                                      "for "
                                                      f"{recognized_profile['root']} "
                                                      "implies a point "
                                                      "value of "
                                                      f"${implied_point_value:,.2f}, "
                                                      "which is "
                                                      "inconsistent "
                                                      "with this "
                                                      "trade's existing "
                                                      "point value of "
                                                      f"${existing_point_value:,.2f}. "
                                                      "This would "
                                                      "change its "
                                                      "historical gross "
                                                      "P/L, so the edit "
                                                      "was not applied."
                                                )

                                                return

                                          print_futures_instrument_profile(
                                                recognized_profile
                                          )

                                          new_tick_size = (
                                                recognized_profile[
                                                      "tick_size"
                                                ]
                                          )
                                          new_tick_value = (
                                                recognized_profile[
                                                      "tick_value"
                                                ]
                                          )
                                    else:
                                          new_tick_size = (
                                                prompt_finite_number(
                                                      (
                                                            "Tick size "
                                                            f"(current: "
                                                            f"{current.get('tick_size')}): "
                                                      ),
                                                      "Tick size",
                                                      minimum=0,
                                                      minimum_is_strict=True,
                                                      default=current.get(
                                                            "tick_size"
                                                      )
                                                )
                                          )

                                          new_tick_value = (
                                                prompt_finite_number(
                                                      (
                                                            "Tick value "
                                                            f"(current: "
                                                            f"{current.get('tick_value')}): "
                                                      ),
                                                      "Tick value",
                                                      minimum=0,
                                                      minimum_is_strict=True,
                                                      default=current.get(
                                                            "tick_value"
                                                      )
                                                )
                                          )

                                    new_entry = prompt_futures_price(
                                          (
                                                "Entry price "
                                                f"(current: "
                                                f"${current['entry']}): "
                                          ),
                                          "Entry price",
                                          new_tick_size,
                                          default=current["entry"]
                                    )

                                    new_exit = prompt_futures_price(
                                          (
                                                "Exit price "
                                                f"(current: "
                                                f"${current['exit']}): "
                                          ),
                                          "Exit price",
                                          new_tick_size,
                                          default=current["exit"]
                                    )
                              else:
                                    recognized_profile = (
                                          get_known_futures_profile(
                                                new_symbol
                                          )
                                    )

                                    if recognized_profile is not None:
                                          known_tick_size = (
                                                recognized_profile[
                                                      "tick_size"
                                                ]
                                          )
                                          known_tick_value = (
                                                recognized_profile[
                                                      "tick_value"
                                                ]
                                          )

                                          print_futures_instrument_profile(
                                                recognized_profile
                                          )

                                          implied_point_value = (
                                                known_tick_value
                                                / known_tick_size
                                          )

                                          existing_point_value = (
                                                current.get(
                                                      "point_value"
                                                )
                                          )

                                          if (
                                                existing_point_value
                                                is not None
                                                and abs(
                                                      implied_point_value
                                                      - existing_point_value
                                                )
                                                >= FLOATING_POINT_TOLERANCE
                                          ):
                                                print(
                                                      "The built-in "
                                                      "specification "
                                                      "for "
                                                      f"{recognized_profile['root']} "
                                                      "implies a point "
                                                      "value of "
                                                      f"${implied_point_value:,.2f}, "
                                                      "which is "
                                                      "inconsistent "
                                                      "with this "
                                                      "trade's existing "
                                                      "point value of "
                                                      f"${existing_point_value:,.2f}. "
                                                      "This would "
                                                      "change its "
                                                      "historical gross "
                                                      "P/L, so the edit "
                                                      "was not applied."
                                                )

                                                return

                                          new_tick_size = known_tick_size
                                          new_tick_value = known_tick_value

                                          new_entry = prompt_futures_price(
                                                (
                                                      "Entry price "
                                                      f"(current: "
                                                      f"${current['entry']}): "
                                                ),
                                                "Entry price",
                                                new_tick_size,
                                                default=current["entry"]
                                          )

                                          new_exit = prompt_futures_price(
                                                (
                                                      "Exit price "
                                                      f"(current: "
                                                      f"${current['exit']}): "
                                                ),
                                                "Exit price",
                                                new_tick_size,
                                                default=current["exit"]
                                          )
                                    else:
                                          print(
                                                "This contract is not "
                                                "in the built-in "
                                                "specifications. Tick "
                                                "size and tick value "
                                                "are unspecified for "
                                                "this legacy trade. "
                                                "Leave both blank to "
                                                "keep them "
                                                "unspecified."
                                          )

                                          tick_size_input = input(
                                                "Tick size (current: N/A): "
                                          ).strip()

                                          tick_value_input = input(
                                                "Tick value (current: N/A): "
                                          ).strip()

                                          if (
                                                tick_size_input == ""
                                                and tick_value_input == ""
                                          ):
                                                new_tick_size = None
                                                new_tick_value = None

                                                new_point_value = (
                                                      prompt_finite_number(
                                                            (
                                                                  "Point value "
                                                                  f"(current: "
                                                                  f"${current.get('point_value')}): "
                                                            ),
                                                            "Point value",
                                                            minimum=0,
                                                            minimum_is_strict=True,
                                                            default=current.get(
                                                                  "point_value"
                                                            )
                                                      )
                                                )

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
                                          elif (
                                                tick_size_input == ""
                                                or tick_value_input == ""
                                          ):
                                                print(
                                                      "Tick size and tick "
                                                      "value must both be "
                                                      "provided together."
                                                )

                                                return
                                          else:
                                                new_tick_size = (
                                                      get_finite_number(
                                                            tick_size_input,
                                                            "Tick size",
                                                            0,
                                                            True
                                                      )
                                                )

                                                new_tick_value = (
                                                      get_finite_number(
                                                            tick_value_input,
                                                            "Tick value",
                                                            0,
                                                            True
                                                      )
                                                )

                                                implied_point_value = (
                                                      new_tick_value
                                                      / new_tick_size
                                                )

                                                existing_point_value = (
                                                      current.get(
                                                            "point_value"
                                                      )
                                                )

                                                if (
                                                      existing_point_value
                                                      is not None
                                                      and abs(
                                                            implied_point_value
                                                            - existing_point_value
                                                      )
                                                      >= FLOATING_POINT_TOLERANCE
                                                ):
                                                      print(
                                                            "Tick size and "
                                                            "tick value imply "
                                                            "a point value of "
                                                            f"${implied_point_value}, "
                                                            "which is "
                                                            "inconsistent "
                                                            "with this "
                                                            "trade's existing "
                                                            "point value of "
                                                            f"${existing_point_value}. "
                                                            "This would "
                                                            "change its "
                                                            "historical gross "
                                                            "P/L, so the edit "
                                                            "was not applied."
                                                      )

                                                      return

                                                new_entry = prompt_futures_price(
                                                      (
                                                            "Entry price "
                                                            f"(current: "
                                                            f"${current['entry']}): "
                                                      ),
                                                      "Entry price",
                                                      new_tick_size,
                                                      default=current["entry"]
                                                )

                                                new_exit = prompt_futures_price(
                                                      (
                                                            "Exit price "
                                                            f"(current: "
                                                            f"${current['exit']}): "
                                                      ),
                                                      "Exit price",
                                                      new_tick_size,
                                                      default=current["exit"]
                                                )
                        else:
                              new_contracts = (
                                    prompt_positive_integer(
                                          "Contracts: ",
                                          "Contracts"
                                    )
                              )

                              new_tick_size, new_tick_value = (
                                    resolve_futures_tick_metadata(
                                          new_symbol
                                    )
                              )

                              new_entry = prompt_futures_price(
                                    (
                                          "Entry price "
                                          f"(current: "
                                          f"${current['entry']}): "
                                    ),
                                    "Entry price",
                                    new_tick_size,
                                    default=current["entry"]
                              )

                              new_exit = prompt_futures_price(
                                    (
                                          "Exit price "
                                          f"(current: "
                                          f"${current['exit']}): "
                                    ),
                                    "Exit price",
                                    new_tick_size,
                                    default=current["exit"]
                              )
                  else:
                        if current_market_type == "forex":
                              new_lot_size = (
                                    prompt_finite_number(
                                          (
                                                "Lot size "
                                                f"(current: "
                                                f"{current.get('lot_size')}): "
                                          ),
                                          "Lot size",
                                          minimum=0,
                                          minimum_is_strict=True,
                                          default=current.get(
                                                "lot_size"
                                          )
                                    )
                              )

                              standard_profile = (
                                    get_standard_forex_pip_profile(
                                          new_symbol
                                    )
                              )

                              if standard_profile is not None:
                                    new_pip_size = standard_profile[
                                          "pip_size"
                                    ]
                                    new_price_precision = (
                                          standard_profile[
                                                "price_precision"
                                          ]
                                    )

                                    print(
                                          f"Standard pair detected. "
                                          f"Using pip size "
                                          f"{new_pip_size} and price "
                                          f"precision "
                                          f"{new_price_precision}."
                                    )
                              else:
                                    default_pip_size = current.get(
                                          "pip_size"
                                    )
                                    default_price_precision = current.get(
                                          "price_precision"
                                    )

                                    pip_size_input = input(
                                          (
                                                "Pip size "
                                                f"(current: "
                                                f"{default_pip_size}): "
                                          )
                                    ).strip()

                                    precision_input = input(
                                          (
                                                "Price precision "
                                                f"(current: "
                                                f"{default_price_precision}): "
                                          )
                                    ).strip()

                                    if (
                                          pip_size_input == ""
                                          and precision_input == ""
                                    ):
                                          new_pip_size = default_pip_size
                                          new_price_precision = (
                                                default_price_precision
                                          )
                                    else:
                                          new_pip_size = get_finite_number(
                                                pip_size_input
                                                if pip_size_input != ""
                                                else default_pip_size,
                                                "Pip size",
                                                0,
                                                True
                                          )

                                          new_price_precision = (
                                                get_positive_integer(
                                                      precision_input
                                                      if precision_input != ""
                                                      else default_price_precision,
                                                      "Price precision"
                                                )
                                          )

                              new_entry = prompt_forex_price(
                                    (
                                          "Entry price "
                                          f"(current: "
                                          f"{format_trade_price(current, 'entry')}): "
                                    ),
                                    "Entry price",
                                    new_price_precision,
                                    default=current["entry"]
                              )

                              new_exit = prompt_forex_price(
                                    (
                                          "Exit price "
                                          f"(current: "
                                          f"{format_trade_price(current, 'exit')}): "
                                    ),
                                    "Exit price",
                                    new_price_precision,
                                    default=current["exit"]
                              )
                        else:
                              new_lot_size = prompt_finite_number(
                                    "Lot size: ",
                                    "Lot size",
                                    minimum=0,
                                    minimum_is_strict=True
                              )

                              standard_profile = (
                                    get_standard_forex_pip_profile(
                                          new_symbol
                                    )
                              )

                              if standard_profile is not None:
                                    new_pip_size = standard_profile[
                                          "pip_size"
                                    ]
                                    new_price_precision = (
                                          standard_profile[
                                                "price_precision"
                                          ]
                                    )

                                    print(
                                          f"Standard pair detected. "
                                          f"Using pip size "
                                          f"{new_pip_size} and price "
                                          f"precision "
                                          f"{new_price_precision}."
                                    )
                              else:
                                    new_price_precision = (
                                          prompt_positive_integer(
                                                (
                                                      "Price precision "
                                                      "(decimal "
                                                      "places): "
                                                ),
                                                "Price precision"
                                          )
                                    )

                                    new_pip_size = (
                                          prompt_finite_number(
                                                "Pip size: ",
                                                "Pip size",
                                                minimum=0,
                                                minimum_is_strict=True
                                          )
                                    )

                              new_entry = prompt_forex_price(
                                    (
                                          "Entry price "
                                          f"(current: "
                                          f"${current['entry']}): "
                                    ),
                                    "Entry price",
                                    new_price_precision,
                                    default=current["entry"]
                              )

                              new_exit = prompt_forex_price(
                                    (
                                          "Exit price "
                                          f"(current: "
                                          f"${current['exit']}): "
                                    ),
                                    "Exit price",
                                    new_price_precision,
                                    default=current["exit"]
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

                  if new_market_type == "forex":
                        new_pip_value_info = (
                              resolve_forex_pip_value_for_edit(
                                    current=current,
                                    new_symbol=new_symbol,
                                    new_pip_size=new_pip_size,
                                    new_price_precision=new_price_precision,
                                    new_lot_size=new_lot_size,
                                    new_entry=new_entry,
                                    new_exit=new_exit,
                                    new_direction=new_direction,
                                    new_trade_date=new_trade_date,
                                    new_exit_time=new_exit_time,
                                    account=account,
                              )
                        )

                        if new_pip_value_info is None:
                              return

                        new_pip_value = (
                              new_pip_value_info["pip_value"]
                        )
                        new_account_currency = account.get(
                              "account_currency"
                        )
                        new_conversion_rate = (
                              new_pip_value_info[
                                    "conversion_rate"
                              ]
                        )
                        new_conversion_pair = (
                              new_pip_value_info[
                                    "conversion_pair"
                              ]
                        )
                        new_conversion_timestamp = (
                              new_pip_value_info[
                                    "conversion_timestamp"
                              ]
                        )
                        new_conversion_rate_source = (
                              new_pip_value_info[
                                    "conversion_rate_source"
                              ]
                        )
                  else:
                        new_account_currency = None
                        new_conversion_rate = None
                        new_conversion_pair = None
                        new_conversion_timestamp = None
                        new_conversion_rate_source = None

            except ValueError:
                  print("Invalid time format. Please use HH:MM.")
                  return

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


            updated_trade_input = dict(current)

            updated_trade_input.update({
                  "symbol": new_symbol,
                  "direction": new_direction,
                  "market_type": new_market_type,

                  "entry": new_entry,
                  "exit": new_exit,

                  "contracts": new_contracts,
                  "tick_size": new_tick_size,
                  "tick_value": new_tick_value,
                  "point_value": new_point_value,

                  "lot_size": new_lot_size,
                  "pip_size": new_pip_size,
                  "pip_value": new_pip_value,
                  "price_precision": new_price_precision,

                  "standard_lot_units": STANDARD_LOT_UNITS,
                  "account_currency": new_account_currency,
                  "conversion_rate": new_conversion_rate,
                  "conversion_pair": new_conversion_pair,
                  "conversion_timestamp": new_conversion_timestamp,
                  "conversion_rate_source": new_conversion_rate_source,

                  "commission": new_commission,
                  "risk_amount": new_risk_amount,

                  "trade_date": new_trade_date,
                  "entry_time": new_entry_time,
                  "exit_time": new_exit_time,

                  "strategy_methods": new_strategy_methods,
                  "setup_components": new_setup_components,
                  "notes": new_notes,
                  "mistake": new_mistake
            })

            updated_trade, errors = validate_and_normalize_trade(
                  updated_trade_input
            )

            if errors:
                  print(
                        "Trade was not updated due "
                        "to the following errors:"
                  )

                  for error in errors:
                        print(f"  - {error}")

                  return

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

def handle_delete_trade(trades):
      if len(trades) == 0:
            print("No trades to delete.")
      else:
            for i in range(len(trades)):
                  trade = trades[i]
                  print(f"{i + 1}. {trade['symbol']} {trade['direction']} {format_trade_unit_summary(trade)}")

            try:
                  trade_number = int(input("Which trade number would you like to delete? "))
            except ValueError:
                  print("Invalid trade number.")
                  return

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
                        f"{format_trade_unit_summary(trade_to_delete)})? "
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

def handle_trading_statistics(trades):
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

            best_dollar_trade = trades[0]
            worst_dollar_trade = trades[0]
            best_net_trade = trades[0]
            worst_net_trade = trades[0]
            best_dollar_idx = 0
            worst_dollar_idx = 0
            best_net_idx = 0
            worst_net_idx = 0

            for i, trade in enumerate(trades):
                  dollar_pnl = trade.get('dollar_pnl', 0)
                  commission = trade.get('commission', 0)
                  net_dollar_pnl = trade.get(
                        "net_dollar_pnl",
                        trade.get("dollar_pnl", 0)
                  )
                  result = trade['result']

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

            unit_performance_stats = compute_unit_performance_stats(
                  list(enumerate(trades))
            )

            print_unit_performance_stats(
                  unit_performance_stats
            )

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

def handle_search_trades(trades):
      if len(trades) == 0:
            print("No trades to search")
      else:
            print("\nMulti-Filter Search.")
            print("Press Enter to skip any filter.")

            symbol_filter = input("Symbol: ").lower().strip()
            direction_filter = input ("Direction: ").lower().strip()

            while True:
                  market_type_filter = input(
                        "Market Type (futures/forex, "
                        "leave blank for all): "
                  ).lower().strip()

                  if (
                        market_type_filter == ""
                        or market_type_filter in VALID_MARKET_TYPES
                  ):
                        break

                  print(
                        "Market type must be futures "
                        "or forex."
                  )

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
                  return

            found = False
            match_count = 0

            for i in range(len(trades)):
                  trade = trades[i]
                  matches = True

                  if (
                        symbol_filter != ""
                        and normalize_forex_symbol(trade.get("symbol", ""))
                        != normalize_forex_symbol(symbol_filter)
                  ):
                        matches = False
                  if direction_filter != "" and trade.get("direction", "").lower().strip() != direction_filter:
                        matches = False

                  if (
                        market_type_filter != ""
                        and trade.get("market_type", "futures")
                        != market_type_filter
                  ):
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

                        print(f"Market Type: {trade.get('market_type', 'futures')}")
                        print(f"Entry: {format_trade_price(trade, 'entry')}")
                        print(f"Exit: {format_trade_price(trade, 'exit')}")

                        print_trade_unit_detail(trade)

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

def handle_filtered_statistics(trades):
      if len(trades) == 0: 
            print("No trades to calculate filtered statistics.")
      else: 
            print("\nFiltered Statistics")
            print("Press Enter to skip any filter. ")

            symbol_filter = input("Symbol: ").lower().strip()
            direction_filter = input ("Direction: ").lower().strip()

            while True:
                  market_type_filter = input(
                        "Market Type (futures/forex, "
                        "leave blank for all): "
                  ).lower().strip()

                  if (
                        market_type_filter == ""
                        or market_type_filter in VALID_MARKET_TYPES
                  ):
                        break

                  print(
                        "Market type must be futures "
                        "or forex."
                  )

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
                  return

            filtered_trades = []
            filtered_indices = []

            for idx, trade in enumerate(trades): 
                  matches = True 

                  if (
                        symbol_filter != ""
                        and normalize_forex_symbol(trade.get("symbol", ""))
                        != normalize_forex_symbol(symbol_filter)
                  ):
                        matches = False
                  if direction_filter != "" and trade.get("direction", "").lower().strip() != direction_filter:
                        matches = False

                  if (
                        market_type_filter != ""
                        and trade.get("market_type", "futures")
                        != market_type_filter
                  ):
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

                  total_dollar_pnl = 0
                  total_commission = 0
                  total_net_dollar_pnl = 0

                  total_risk = 0
                  total_realized_r = 0
                  risk_trades = 0

                  best_dollar_trade = filtered_trades[0]
                  worst_dollar_trade = filtered_trades[0]
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
                        dollar_pnl = trade.get("dollar_pnl", 0)
                        commission = trade.get("commission", 0)
                        net_dollar_pnl = trade.get(
                              "net_dollar_pnl",
                              trade.get("dollar_pnl", 0)
                        )
                        result = trade["result"]

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

                  average_dollar_win = gross_dollar_profit / wins if wins > 0 else 0
                  average_dollar_loss = gross_dollar_loss / losses if losses > 0 else 0

                  if gross_dollar_loss > 0:
                        dollar_profit_factor = gross_dollar_profit / gross_dollar_loss
                  else:
                        dollar_profit_factor = None

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

                  unit_performance_stats = compute_unit_performance_stats(
                        list(
                              zip(
                                    filtered_indices,
                                    filtered_trades
                              )
                        )
                  )

                  print_unit_performance_stats(
                        unit_performance_stats
                  )

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

def handle_session_analytics(trades):
      display_session_analytics(trades)

def handle_setup_and_strategy_analytics(trades):
      display_setup_analytics(trades)
      display_strategy_method_analytics(trades)

def handle_time_based_analytics(trades):
      display_time_based_analytics(trades)

def handle_equity_drawdown_history(trades, account):
      display_equity_drawdown_history(
            trades,
            account
      )

def handle_save_trades(trades):
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

def handle_export_csv(trades):
      export_trades_to_csv(trades)

def handle_quit():
      print("Goodbye.")

def run_menu(trades, account):
      while True:
            show_menu()
            choice = input("Choose an option: ").strip()

            if choice == "1":
                  account = handle_account_status(trades, account)
            elif choice == "2":
                  account = handle_edit_account(account, trades)
            elif choice == "3":
                  handle_add_trade(trades, account)
            elif choice == "4":
                  handle_view_trades(trades)
            elif choice == "5":
                  handle_edit_trade(trades, account)
            elif choice == "6":
                  handle_delete_trade(trades)
            elif choice == "7":
                  handle_trading_statistics(trades)
            elif choice == "8":
                  handle_search_trades(trades)
            elif choice == "9":
                  handle_filtered_statistics(trades)
            elif choice == "10":
                  handle_session_analytics(trades)
            elif choice == "11":
                  handle_setup_and_strategy_analytics(trades)
            elif choice == "12":
                  handle_time_based_analytics(trades)
            elif choice == "13":
                  handle_equity_drawdown_history(trades, account)
            elif choice == "14":
                  handle_save_trades(trades)
            elif choice == "15":
                  handle_export_csv(trades)
            elif choice == "16":
                  handle_quit()
                  break
            else:
                  print("Invalid choice.")
