from journal.constants import (
    DURATION_DISPLAY_ORDER,
    MAINTENANCE_SESSION_NAME,
    SESSION_DISPLAY_ORDER,
    WEEKLY_DISPLAY_ORDER,
)
from journal.markets import get_known_futures_profile
from journal.analytics import (
    UNIT_PERFORMANCE_BUCKETS,
    calculate_equity_drawdown_history,
    calculate_session_analysis,
    calculate_setup_analysis,
    calculate_strategy_method_analysis,
    calculate_time_based_analytics,
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

def print_futures_instrument_profile(profile):
      print(
            f"{profile['root']} - {profile['name']}"
      )
      print(
            f"Tick size: {profile['tick_size']} | "
            f"Tick value: ${profile['tick_value']:,.2f} | "
            f"Point value: ${profile['point_value']:,.2f}"
      )

def format_trade_price(trade, field_name):
      value = trade.get(field_name)

      if value is None:
            return "N/A"

      if trade.get("market_type") == "forex":
            price_precision = trade.get("price_precision")

            if price_precision is not None:
                  return f"{value:.{price_precision}f}"

      return str(value)

def format_trade_unit_summary(trade):
      market_type = trade.get("market_type", "futures")

      if market_type == "forex":
            pips_pnl = trade.get("pips_pnl")

            if pips_pnl is None:
                  return "Forex: N/A pips"

            return f"Forex: {pips_pnl:,.1f} pips"

      points_pnl = trade.get("points_pnl", 0)
      ticks_pnl = trade.get("ticks_pnl")

      if ticks_pnl is None:
            return f"Futures: {points_pnl:,.2f} pts"

      return (
            f"Futures: {points_pnl:,.2f} pts "
            f"({ticks_pnl:,.1f} ticks)"
      )

def print_trade_unit_detail(trade):
      market_type = trade.get("market_type", "futures")

      if market_type == "forex":
            lot_size = trade.get("lot_size")
            print(
                  f"Lot Size: "
                  f"{lot_size if lot_size is not None else 'N/A'}"
            )

            pip_size = trade.get("pip_size")
            print(
                  f"Pip Size: "
                  f"{pip_size if pip_size is not None else 'N/A'}"
            )

            pip_value = trade.get("pip_value")

            if pip_value is None:
                  print("Pip Value: N/A")
            else:
                  print(f"Pip Value: ${pip_value:,.2f}")

            pips_pnl = trade.get("pips_pnl")

            if pips_pnl is None:
                  print("Pips P/L: N/A")
            else:
                  print(f"Pips P/L: {pips_pnl:,.1f} pips")

      else:
            recognized_profile = get_known_futures_profile(
                  trade.get("symbol", "")
            )

            if recognized_profile is not None:
                  print(
                        f"Instrument: {recognized_profile['root']} "
                        f"- {recognized_profile['name']}"
                  )

            print(f"Contracts: {trade.get('contracts', 'N/A')}")

            point_value = trade.get("point_value")

            if point_value is None:
                  print("Point Value: N/A")
            else:
                  print(f"Point Value: ${point_value:,.2f}")

            tick_size = trade.get("tick_size")
            tick_value = trade.get("tick_value")
            ticks_pnl = trade.get("ticks_pnl")

            if (
                  tick_size is None
                  or tick_value is None
            ):
                  print("Tick Size: N/A")
                  print("Tick Value: N/A")
                  print("Ticks P/L: N/A")
            else:
                  print(f"Tick Size: {tick_size}")
                  print(f"Tick Value: ${tick_value:,.2f}")
                  print(f"Ticks P/L: {ticks_pnl:,.1f} ticks")

            print(
                  f"Points P/L: "
                  f"{trade.get('points_pnl', 0):,.2f} pts"
            )

def print_unit_performance_stats(unit_stats):
      for (bucket_key, title, pnl_field, unit_label, bucket_filter) in (
            UNIT_PERFORMANCE_BUCKETS
      ):
            stats = unit_stats.get(bucket_key)

            if stats is None:
                  continue

            unit = stats["unit_label"]

            print()
            print("-" * 31)
            print(stats["title"])
            print("-" * 31)
            print()

            print(f"{'Total:':<27}{stats['total']:,.2f} {unit}")
            print(
                  f"{'Average per Trade:':<27}"
                  f"{stats['average']:.2f} {unit}"
            )

            print(
                  f"{'Best Trade:':<27}#{stats['best_idx'] + 1} "
                  f"{stats['best_trade']['symbol']} "
                  f"({stats['best_value']:.2f} {unit})"
            )

            print(
                  f"{'Worst Trade:':<27}#{stats['worst_idx'] + 1} "
                  f"{stats['worst_trade']['symbol']} "
                  f"({stats['worst_value']:.2f} {unit})"
            )

            print(
                  f"{'Gross Profit:':<27}"
                  f"{stats['gross_profit']:,.2f} {unit}"
            )
            print(
                  f"{'Gross Loss:':<27}"
                  f"-{stats['gross_loss']:,.2f} {unit}"
            )
            print(
                  f"{'Average Win:':<27}"
                  f"{stats['average_win']:,.2f} {unit}"
            )
            print(
                  f"{'Average Loss:':<27}"
                  f"-{stats['average_loss']:,.2f} {unit}"
            )

            if stats["profit_factor"] is None:
                  print(
                        f"{'Profit Factor:':<27}"
                        "N/A (no losing trades)"
                  )
            else:
                  print(
                        f"{'Profit Factor:':<27}"
                        f"{stats['profit_factor']:.2f}"
                  )

            print(
                  f"{'Expectancy:':<27}"
                  f"{stats['expectancy']:.2f} {unit}"
            )

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
            "closed-trade equity after commission, "
            "not intratrade floating P/L."
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

