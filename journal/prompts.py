from datetime import datetime

from journal.constants import (
    CONVERSION_SOURCE_LABELS,
    FLOATING_POINT_TOLERANCE,
    STANDARD_FOREX_CURRENCIES,
)
from journal.calculations import (
    calculate_dollar_pnl,
    calculate_pips_pnl,
    calculate_points_pnl,
    get_finite_number,
    get_positive_integer,
    is_multiple_of,
    normalize_date_value,
    normalize_time_value,
)
from journal.markets import (
    calculate_forex_pip_value,
    get_forex_pair_currencies,
    get_fx_conversion_rate,
    get_known_futures_profile,
    get_standard_forex_pip_profile,
)
from journal.validation import get_trade_time_warnings
from journal.storage import save_account
from journal.display import print_futures_instrument_profile


def resolve_forex_pair_profile(symbol):
      standard_profile = get_standard_forex_pip_profile(symbol)

      if standard_profile is not None:
            return (
                  standard_profile["pip_size"],
                  standard_profile["price_precision"],
                  True
            )

      price_precision = prompt_positive_integer(
            "Enter price precision (decimal places): ",
            "Price precision"
      )

      pip_size = prompt_finite_number(
            "Enter pip size: ",
            "Pip size",
            minimum=0,
            minimum_is_strict=True
      )

      return pip_size, price_precision, False

def resolve_forex_pip_value(
      symbol,
      pip_size,
      price_precision,
      is_standard_pair,
      account,
      exit_price,
      exit_date,
      exit_time
):
      account_currency = account["account_currency"]
      currencies = get_forex_pair_currencies(symbol)
      exit_timestamp = f"{exit_date} {exit_time}"

      if is_standard_pair:
            print("Standard pair detected.")

      print(
            f"Pip size: {pip_size} | "
            f"Price precision: {price_precision}"
      )

      base_currency, quote_currency = (
            currencies if currencies is not None else (None, None)
      )

      if quote_currency == account_currency:
            pip_value = calculate_forex_pip_value(pip_size, 1.0)

            print(
                  f"Pip value for 1.00 lot: "
                  f"${pip_value:,.2f} {account_currency}"
            )
            print(
                  f"Source: {account_currency} quote currency"
            )

            return {
                  "pip_value": pip_value,
                  "conversion_rate": 1.0,
                  "conversion_pair": None,
                  "conversion_timestamp": None,
                  "conversion_rate_source": "not_required",
            }

      if base_currency == account_currency:
            conversion_rate = 1.0 / exit_price
            pip_value = calculate_forex_pip_value(
                  pip_size,
                  conversion_rate
            )

            print(
                  f"Pip value for 1.00 lot: "
                  f"approximately ${pip_value:,.2f} "
                  f"{account_currency}"
            )
            print(
                  f"Conversion rate: {symbol.upper()} "
                  f"{exit_price:.{price_precision}f}"
            )
            print("Source: Trade exit price")

            return {
                  "pip_value": pip_value,
                  "conversion_rate": conversion_rate,
                  "conversion_pair": symbol.upper(),
                  "conversion_timestamp": exit_timestamp,
                  "conversion_rate_source": "trade_exit_price",
            }

      conversion_pair_label = (
            f"{quote_currency}/{account_currency}"
      )

      conversion_rate, rate_source = get_fx_conversion_rate(
            quote_currency,
            account_currency,
            exit_timestamp
      )

      if conversion_rate is None:
            print(
                  f"A {conversion_pair_label} conversion "
                  f"rate is required to value this pair in "
                  f"{account_currency}, and no market data "
                  "source is configured."
            )

            conversion_rate = prompt_finite_number(
                  f"Enter {conversion_pair_label} "
                  "conversion rate: ",
                  "Conversion rate",
                  minimum=0,
                  minimum_is_strict=True
            )

            rate_source = "manual"

      pip_value = calculate_forex_pip_value(
            pip_size,
            conversion_rate
      )

      print(
            f"Pip value for 1.00 lot: "
            f"approximately ${pip_value:,.2f} "
            f"{account_currency}"
      )
      print(
            f"Conversion rate: {conversion_pair_label} "
            f"{conversion_rate}"
      )
      print(
            f"Source: "
            f"{CONVERSION_SOURCE_LABELS.get(rate_source, rate_source)}"
      )

      return {
            "pip_value": pip_value,
            "conversion_rate": conversion_rate,
            "conversion_pair": conversion_pair_label,
            "conversion_timestamp": exit_timestamp,
            "conversion_rate_source": rate_source,
      }

def ensure_account_currency(account):
      current_currency = account.get("account_currency")

      if current_currency:
            return current_currency

      print(
            "This account has no currency set. An "
            "account currency is required before adding "
            "a Forex trade."
      )

      while True:
            currency_input = input(
                  "Enter account currency (3-letter code, "
                  "e.g. USD): "
            ).strip().upper()

            if (
                  len(currency_input) == 3
                  and currency_input.isalpha()
                  and currency_input in STANDARD_FOREX_CURRENCIES
            ):
                  break

            print(
                  "Account currency must be a recognized "
                  "three-letter currency code."
            )

      account["account_currency"] = currency_input

      if not save_account(account):
            print(
                  "Warning: account currency could not be "
                  "saved. It will be used for this trade "
                  "only."
            )

      return currency_input

def resolve_forex_pip_value_for_edit(
      current,
      new_symbol,
      new_pip_size,
      new_price_precision,
      new_lot_size,
      new_entry,
      new_exit,
      new_direction,
      new_trade_date,
      new_exit_time,
      account
):
      account_currency = account.get("account_currency")

      previous_pip_value = current.get("pip_value")

      relevant_field_changed = (
            new_symbol != current.get("symbol")
            or new_exit != current.get("exit")
            or new_lot_size != current.get("lot_size")
            or new_trade_date != current.get("trade_date")
            or new_exit_time != current.get("exit_time")
            or account_currency != current.get("account_currency")
      )

      if (
            not relevant_field_changed
            and previous_pip_value is not None
      ):
            return {
                  "pip_value": previous_pip_value,
                  "conversion_rate": current.get(
                        "conversion_rate"
                  ),
                  "conversion_pair": current.get(
                        "conversion_pair"
                  ),
                  "conversion_timestamp": current.get(
                        "conversion_timestamp"
                  ),
                  "conversion_rate_source": current.get(
                        "conversion_rate_source"
                  ),
            }

      if account_currency is None:
            account_currency = ensure_account_currency(
                  account
            )

      is_standard_pair = (
            get_standard_forex_pip_profile(new_symbol)
            is not None
      )

      new_info = resolve_forex_pip_value(
            symbol=new_symbol,
            pip_size=new_pip_size,
            price_precision=new_price_precision,
            is_standard_pair=is_standard_pair,
            account=account,
            exit_price=new_exit,
            exit_date=new_trade_date,
            exit_time=new_exit_time,
      )

      if (
            previous_pip_value is not None
            and abs(
                  new_info["pip_value"] - previous_pip_value
            )
            >= FLOATING_POINT_TOLERANCE
      ):
            previous_points_pnl = calculate_points_pnl(
                  current.get("direction", new_direction),
                  current.get("entry", new_entry),
                  current.get("exit", new_exit)
            )

            previous_pips_pnl = calculate_pips_pnl(
                  previous_points_pnl,
                  current.get("pip_size", new_pip_size)
            )

            previous_dollar_pnl = calculate_dollar_pnl(
                  previous_pips_pnl,
                  previous_pip_value,
                  current.get("lot_size", new_lot_size)
            )

            new_points_pnl = calculate_points_pnl(
                  new_direction,
                  new_entry,
                  new_exit
            )

            new_pips_pnl = calculate_pips_pnl(
                  new_points_pnl,
                  new_pip_size
            )

            new_dollar_pnl = calculate_dollar_pnl(
                  new_pips_pnl,
                  new_info["pip_value"],
                  new_lot_size
            )

            print(
                  f"Pip value would change from "
                  f"${previous_pip_value:,.4f} to "
                  f"${new_info['pip_value']:,.4f}, which "
                  f"changes gross dollar P/L from "
                  f"${previous_dollar_pnl:,.2f} to "
                  f"${new_dollar_pnl:,.2f}."
            )

            confirm = input(
                  "Apply this change? (yes/no): "
            ).strip().lower()

            if confirm != "yes":
                  print(
                        "Edit cancelled; trade left "
                        "unchanged."
                  )
                  return None

      return new_info

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

def prompt_futures_price(
      prompt,
      field_name,
      tick_size,
      default = None
):

      while True:
            raw_value = input(prompt).strip()

            if (
                  raw_value == ""
                  and default is not None
            ):
                  return default

            try:
                  value = get_finite_number(
                        raw_value,
                        field_name,
                        minimum=0,
                        minimum_is_strict=True
                  )

            except ValueError as error:
                  print(error)
                  continue

            if is_multiple_of(value, tick_size):
                  return value

            print(
                  f"{field_name} must align with a "
                  f"tick size of {tick_size}. "
            )

def prompt_forex_price(
      prompt,
      field_name,
      price_precision,
      default = None
):

      while True:
            raw_value = input(prompt).strip()

            if (
                  raw_value == ""
                  and default is not None
            ):
                  return default

            try:
                  value = get_finite_number(
                        raw_value,
                        field_name,
                        minimum=0,
                        minimum_is_strict=True
                  )

            except ValueError as error:
                  print(error)
                  continue

            typed_decimal_places = (
                  len(raw_value.split(".", 1)[1])
                  if "." in raw_value
                  else 0
            )

            if typed_decimal_places <= price_precision:
                  return value

            print(
                  f"{field_name} cannot exceed "
                  f"{price_precision} decimal places "
                  "for this pair. "
            )

def resolve_futures_tick_metadata(symbol):
      profile = get_known_futures_profile(symbol)

      if profile is not None:
            print_futures_instrument_profile(profile)

            return profile["tick_size"], profile["tick_value"]

      print(
            "This contract is not in the built-in "
            "specifications. Tick size and tick value "
            "must be entered manually."
      )

      tick_size = prompt_finite_number(
            "Enter tick size: ",
            "Tick size",
            minimum=0,
            minimum_is_strict=True
      )

      tick_value = prompt_finite_number(
            "Enter tick value: $",
            "Tick value",
            minimum=0,
            minimum_is_strict=True
      )

      derived_point_value = tick_value / tick_size

      print(
            f"Tick size: {tick_size} | "
            f"Tick value: ${tick_value:,.2f} | "
            f"Point value: ${derived_point_value:,.2f}"
      )

      print(
            "Using a custom Futures profile for this trade "
            "(not one of the built-in instrument "
            "specifications)."
      )

      return tick_size, tick_value

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

def confirm_trade_time_is_plausible(
      market_type,
      trade_date,
      entry_time,
      exit_time
):
      warnings = get_trade_time_warnings(
            market_type,
            trade_date,
            entry_time,
            exit_time
      )

      if not warnings:
            return True

      print(
            "\nThis trade's date/time looks unusual for "
            f"{market_type} markets:"
      )

      for reason in warnings:
            print(f"  - {reason}")

      print(
            "(This is an approximate Eastern Time "
            "market-hours check; actual holidays, brokers, "
            "and exchange sessions can vary.)"
      )

      confirm = input(
            "Save this trade anyway? (y/n): "
      ).strip().lower()

      return confirm == "y"

