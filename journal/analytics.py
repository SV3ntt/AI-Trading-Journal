from datetime import datetime, time as dt_time

from journal.constants import MAINTENANCE_SESSION_NAME
from journal.calculations import calculate_net_result, calculate_realized_r


UNIT_PERFORMANCE_BUCKETS = (
      (
            "futures_points",
            "FUTURES POINTS PERFORMANCE",
            "points_pnl",
            "pts",
            lambda trade: (
                  trade.get("market_type", "futures") == "futures"
            ),
      ),
      (
            "futures_ticks",
            "FUTURES TICKS PERFORMANCE",
            "ticks_pnl",
            "ticks",
            lambda trade: (
                  trade.get("market_type", "futures") == "futures"
                  and trade.get("ticks_pnl") is not None
            ),
      ),
      (
            "forex_pips",
            "FOREX PIPS PERFORMANCE",
            "pips_pnl",
            "pips",
            lambda trade: (
                  trade.get("market_type") == "forex"
                  and trade.get("pips_pnl") is not None
            ),
      ),
)

def compute_unit_performance_stats(indexed_trades):
      results = {}

      for (
            bucket_key,
            title,
            pnl_field,
            unit_label,
            bucket_filter
      ) in UNIT_PERFORMANCE_BUCKETS:
            matching = [
                  (idx, trade) for (idx, trade) in indexed_trades
                  if bucket_filter(trade)
            ]

            if not matching:
                  results[bucket_key] = None
                  continue

            total = sum(
                  trade.get(pnl_field, 0)
                  for (idx, trade) in matching
            )
            count = len(matching)
            average = total / count

            best_idx, best_trade = max(
                  matching,
                  key=lambda pair: pair[1].get(pnl_field, 0)
            )
            worst_idx, worst_trade = min(
                  matching,
                  key=lambda pair: pair[1].get(pnl_field, 0)
            )

            gross_profit = sum(
                  trade.get(pnl_field, 0)
                  for (idx, trade) in matching
                  if trade.get(pnl_field, 0) > 0
            )
            gross_loss = abs(sum(
                  trade.get(pnl_field, 0)
                  for (idx, trade) in matching
                  if trade.get(pnl_field, 0) < 0
            ))

            wins = sum(
                  1 for (idx, trade) in matching
                  if trade.get(pnl_field, 0) > 0
            )
            losses = sum(
                  1 for (idx, trade) in matching
                  if trade.get(pnl_field, 0) < 0
            )

            average_win = gross_profit / wins if wins > 0 else 0
            average_loss = gross_loss / losses if losses > 0 else 0

            if gross_loss > 0:
                  profit_factor = gross_profit / gross_loss
            else:
                  profit_factor = None

            results[bucket_key] = {
                  "title": title,
                  "unit_label": unit_label,
                  "total": total,
                  "average": average,
                  "best_idx": best_idx,
                  "best_trade": best_trade,
                  "best_value": best_trade.get(pnl_field, 0),
                  "worst_idx": worst_idx,
                  "worst_trade": worst_trade,
                  "worst_value": worst_trade.get(pnl_field, 0),
                  "gross_profit": gross_profit,
                  "gross_loss": gross_loss,
                  "average_win": average_win,
                  "average_loss": average_loss,
                  "profit_factor": profit_factor,
                  "expectancy": average,
            }

      return results

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

