import math
from datetime import datetime

from journal.constants import (
    FOREX_ONLY_FIELDS,
    FUTURES_ONLY_FIELDS,
    STANDARD_FOREX_CURRENCIES,
    STANDARD_LOT_UNITS,
    VALID_ACCOUNT_TYPES,
    VALID_MARKET_TYPES,
    valid_directions,
)
from journal.calculations import (
    calculate_dollar_pnl,
    calculate_duration,
    calculate_net_dollar_pnl,
    calculate_net_result,
    calculate_pips_pnl,
    calculate_points_pnl,
    calculate_realized_r,
    calculate_result,
    calculate_ticks_pnl,
    get_finite_number,
    get_positive_integer,
    is_multiple_of,
    normalize_date_value,
    normalize_time_value,
)
from journal.markets import (
    get_known_futures_tick_size,
    get_standard_forex_pip_profile,
    normalize_forex_symbol,
)
from journal.analytics import determine_session, get_setup_components, get_strategy_methods


def validate_and_normalize_trade(trade):
      if not isinstance(trade, dict):
            return None, [
                  "Trade record must be a "
                  "JSON object."
            ]

      errors = []

      raw_symbol_text = str(
            trade.get("symbol", "")
      ).strip()

      if raw_symbol_text == "":
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

      market_type = str(
            trade.get("market_type", "")
      ).strip().lower()

      if market_type == "":
            market_type = "futures"

      if market_type not in VALID_MARKET_TYPES:
            errors.append(
                  "Market type must be futures or "
                  "forex."
            )
            market_type = "futures"

      if market_type == "forex" and raw_symbol_text != "":
            symbol = normalize_forex_symbol(raw_symbol_text)
      else:
            symbol = raw_symbol_text.lower()

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

      contracts = None
      tick_size = None
      tick_value = None
      point_value = None

      lot_size = None
      pip_size = None
      pip_value = None
      price_precision = None

      account_currency = None
      conversion_rate = None
      conversion_pair = None
      conversion_timestamp = None
      conversion_rate_source = None

      if market_type == "futures":
            try:
                  contracts = get_positive_integer(
                        trade.get("contracts"),
                        "Contracts"
                  )

            except ValueError as error:
                  errors.append(str(error))
                  contracts = None

            has_tick_metadata = (
                  trade.get("tick_size") not in (None, "")
                  and trade.get("tick_value") not in (None, "")
            )

            if has_tick_metadata:
                  try:
                        tick_size = get_finite_number(
                              trade.get("tick_size"),
                              "Tick size",
                              0,
                              True
                        )
                  except ValueError as error:
                        errors.append(str(error))
                        tick_size = None

                  try:
                        tick_value = get_finite_number(
                              trade.get("tick_value"),
                              "Tick value",
                              0,
                              True
                        )
                  except ValueError as error:
                        errors.append(str(error))
                        tick_value = None

                  if (
                        tick_size is not None
                        and tick_value is not None
                  ):
                        point_value = tick_value / tick_size

                        for (
                              price_field,
                              price_label
                        ) in (
                              ("entry", "Entry price"),
                              ("exit", "Exit price"),
                        ):
                              price_value = numeric_values.get(
                                    price_field
                              )

                              if (
                                    price_value is not None
                                    and not is_multiple_of(
                                          price_value,
                                          tick_size
                                    )
                              ):
                                    errors.append(
                                          f"{price_label} must "
                                          f"align with a tick "
                                          f"size of {tick_size}."
                                    )
            else:
                  known_tick_size = get_known_futures_tick_size(
                        symbol
                  )

                  try:
                        point_value = get_finite_number(
                              trade.get("point_value"),
                              "Point value",
                              0,
                              True
                        )
                  except ValueError as error:
                        errors.append(str(error))
                        point_value = None

                  if (
                        known_tick_size is not None
                        and point_value is not None
                  ):
                        tick_size = known_tick_size
                        tick_value = point_value * known_tick_size

      else:
            try:
                  lot_size = get_finite_number(
                        trade.get("lot_size"),
                        "Lot size",
                        0,
                        True
                  )
            except ValueError as error:
                  errors.append(str(error))
                  lot_size = None

            standard_profile = get_standard_forex_pip_profile(
                  symbol
            )

            pip_size_raw = trade.get("pip_size")
            price_precision_raw = trade.get("price_precision")

            if standard_profile is not None:
                  pip_size = standard_profile["pip_size"]
                  price_precision = standard_profile[
                        "price_precision"
                  ]
            else:
                  try:
                        pip_size = get_finite_number(
                              pip_size_raw,
                              "Pip size",
                              0,
                              True
                        )
                  except ValueError as error:
                        errors.append(str(error))
                        pip_size = None

                  try:
                        price_precision = get_positive_integer(
                              price_precision_raw,
                              "Price precision"
                        )
                  except ValueError as error:
                        errors.append(str(error))
                        price_precision = None

            try:
                  pip_value = get_finite_number(
                        trade.get("pip_value"),
                        "Pip value",
                        0,
                        True
                  )
            except ValueError as error:
                  errors.append(str(error))
                  pip_value = None

            if price_precision is not None:
                  for (
                        price_field,
                        price_label
                  ) in (
                        ("entry", "Entry price"),
                        ("exit", "Exit price"),
                  ):
                        price_value = numeric_values.get(
                              price_field
                        )

                        if (
                              price_value is not None
                              and not is_multiple_of(
                                    price_value,
                                    10 ** -price_precision
                              )
                        ):
                              errors.append(
                                    f"{price_label} cannot "
                                    f"exceed {price_precision} "
                                    "decimal places for this "
                                    "pair."
                              )

            account_currency_raw = trade.get(
                  "account_currency"
            )

            if account_currency_raw in (None, ""):
                  account_currency = None
            else:
                  account_currency = str(
                        account_currency_raw
                  ).strip().upper()

            conversion_rate_raw = trade.get(
                  "conversion_rate"
            )

            if conversion_rate_raw in (None, ""):
                  conversion_rate = None
            else:
                  try:
                        conversion_rate = get_finite_number(
                              conversion_rate_raw,
                              "Conversion rate",
                              0,
                              True
                        )
                  except ValueError as error:
                        errors.append(str(error))
                        conversion_rate = None

            conversion_pair = (
                  trade.get("conversion_pair") or None
            )
            conversion_timestamp = (
                  trade.get("conversion_timestamp") or None
            )
            conversion_rate_source = (
                  trade.get("conversion_rate_source") or None
            )

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

      if market_type == "futures":
            ticks_pnl = (
                  calculate_ticks_pnl(points_pnl, tick_size)
                  if tick_size not in (None, 0)
                  else None
            )
            pips_pnl = None

            dollar_pnl = calculate_dollar_pnl(
                  points_pnl,
                  point_value,
                  contracts
            )
      else:
            pips_pnl = calculate_pips_pnl(points_pnl, pip_size)
            ticks_pnl = None

            dollar_pnl = calculate_dollar_pnl(
                  pips_pnl,
                  pip_value,
                  lot_size
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
            "market_type": market_type,

            "entry": (
                  numeric_values["entry"]
            ),

            "exit": (
                  numeric_values["exit"]
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

      if market_type == "futures":
            normalized_trade.update({
                  "contracts": contracts,
                  "tick_size": tick_size,
                  "tick_value": tick_value,
                  "point_value": point_value,
                  "ticks_pnl": ticks_pnl,
            })

            for stale_field in FOREX_ONLY_FIELDS:
                  normalized_trade.pop(stale_field, None)
      else:
            normalized_trade.update({
                  "lot_size": lot_size,
                  "pip_size": pip_size,
                  "pip_value": pip_value,
                  "price_precision": price_precision,
                  "pips_pnl": pips_pnl,

                  "standard_lot_units": STANDARD_LOT_UNITS,
                  "account_currency": account_currency,
                  "conversion_rate": conversion_rate,
                  "conversion_pair": conversion_pair,
                  "conversion_timestamp": conversion_timestamp,
                  "conversion_rate_source": conversion_rate_source,
            })

            for stale_field in FUTURES_ONLY_FIELDS:
                  normalized_trade.pop(stale_field, None)

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

      account_currency_raw = account.get(
            "account_currency"
      )

      if account_currency_raw in (None, ""):
            account_currency = None
      else:
            account_currency_text = str(
                  account_currency_raw
            ).strip().upper()

            if (
                  len(account_currency_text) == 3
                  and account_currency_text.isalpha()
                  and account_currency_text
                  in STANDARD_FOREX_CURRENCIES
            ):
                  account_currency = account_currency_text
            else:
                  account_currency = None

      normalized_account = dict(account)

      normalized_account.update({
            "name": account_name,
            "type": account_type,

            "starting_balance": (
                  starting_balance
            ),

            "high_water_mark": (
                  high_water_mark
            ),

            "account_currency": account_currency,
      })

      return normalized_account, []

_WEEKDAY_NAMES = (
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
      "Sunday",
)

def _futures_time_implausibility_reason(weekday, minutes_since_midnight):
      if weekday == 5:
            return "Futures markets are closed all day Saturday."

      if weekday == 6 and minutes_since_midnight < 18 * 60:
            return (
                  "Futures markets have not yet reopened for "
                  "the week (Sunday before 18:00 ET)."
            )

      if weekday == 4 and minutes_since_midnight >= 17 * 60:
            return (
                  "Futures markets are closed for the weekend "
                  "(Friday at or after 17:00 ET)."
            )

      if (
            weekday in (0, 1, 2, 3)
            and 17 * 60 <= minutes_since_midnight < 18 * 60
      ):
            return (
                  "This falls in the daily Futures maintenance "
                  "break (17:00-18:00 ET)."
            )

      return None

def _forex_time_implausibility_reason(weekday, minutes_since_midnight):
      if weekday == 5:
            return "Forex markets are closed all day Saturday."

      if weekday == 6 and minutes_since_midnight < 17 * 60:
            return (
                  "Forex markets have not yet reopened for "
                  "the week (Sunday before 17:00 ET)."
            )

      if weekday == 4 and minutes_since_midnight >= 17 * 60:
            return (
                  "Forex markets are closed for the weekend "
                  "(Friday at or after 17:00 ET)."
            )

      return None

def get_trade_time_warnings(
      market_type,
      trade_date,
      entry_time,
      exit_time
):
      try:
            date_value = datetime.strptime(
                  trade_date,
                  "%Y-%m-%d"
            )
            entry_value = datetime.strptime(
                  entry_time,
                  "%H:%M"
            )
            exit_value = datetime.strptime(
                  exit_time,
                  "%H:%M"
            )
      except (TypeError, ValueError):
            return []

      entry_weekday = date_value.weekday()
      entry_minutes = (
            entry_value.hour * 60
            + entry_value.minute
      )
      exit_minutes = (
            exit_value.hour * 60
            + exit_value.minute
      )

      # An exit clock time earlier than the entry clock time on the same
      # trade_date is treated as crossing midnight into the next day --
      # this mirrors calculate_duration()'s own overnight handling, so an
      # overnight trade is never flagged as "exit before entry".
      exit_weekday = (
            (entry_weekday + 1) % 7
            if exit_minutes < entry_minutes
            else entry_weekday
      )

      checker = (
            _futures_time_implausibility_reason
            if market_type == "futures"
            else _forex_time_implausibility_reason
      )

      messages = []

      entry_reason = checker(entry_weekday, entry_minutes)
      if entry_reason is not None:
            messages.append(
                  f"Entry time ({_WEEKDAY_NAMES[entry_weekday]} "
                  f"{entry_time} ET, approximate): {entry_reason}"
            )

      exit_reason = checker(exit_weekday, exit_minutes)
      if exit_reason is not None:
            messages.append(
                  f"Exit time ({_WEEKDAY_NAMES[exit_weekday]} "
                  f"{exit_time} ET, approximate): {exit_reason}"
            )

      return list(dict.fromkeys(messages))

