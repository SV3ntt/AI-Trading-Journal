from journal.constants import (
    FUTURES_INSTRUMENT_PROFILES,
    FUTURES_MONTH_CODES,
    STANDARD_FOREX_CURRENCIES,
    STANDARD_LOT_UNITS,
)


def match_known_futures_root(symbol):
      normalized_symbol = str(symbol).strip().upper()

      for root in FUTURES_INSTRUMENT_PROFILES:
            if normalized_symbol == root:
                  return root

            if not normalized_symbol.startswith(root):
                  continue

            suffix = normalized_symbol[len(root):]

            if suffix in ("1!", "!"):
                  return root

            if (
                  len(suffix) >= 2
                  and suffix[0] in FUTURES_MONTH_CODES
                  and suffix[1:].isdigit()
                  and len(suffix[1:]) <= 2
            ):
                  return root

      return None

def get_known_futures_profile(symbol):
      root = match_known_futures_root(symbol)

      if root is None:
            return None

      return dict(
            FUTURES_INSTRUMENT_PROFILES[root],
            root=root
      )

def get_known_futures_tick_size(symbol):
      profile = get_known_futures_profile(symbol)

      if profile is None:
            return None

      return profile["tick_size"]

def get_known_futures_tick_value(symbol):
      profile = get_known_futures_profile(symbol)

      if profile is None:
            return None

      return profile["tick_value"]

def normalize_forex_symbol(symbol):
      text = str(symbol).strip().upper()
      text = text.replace("-", "/").replace(" ", "")

      if "/" in text:
            base, _, quote = text.partition("/")
      elif len(text) == 6:
            base, quote = text[:3], text[3:]
      else:
            return str(symbol).strip().lower()

      if len(base) == 3 and len(quote) == 3:
            return f"{base.lower()}/{quote.lower()}"

      return str(symbol).strip().lower()

def get_forex_pair_currencies(symbol):
      normalized_symbol = normalize_forex_symbol(symbol)

      if "/" not in normalized_symbol:
            return None

      base, _, quote = normalized_symbol.partition("/")

      if len(base) != 3 or len(quote) != 3:
            return None

      return base.upper(), quote.upper()

def get_standard_forex_pip_profile(symbol):
      currencies = get_forex_pair_currencies(symbol)

      if currencies is None:
            return None

      base, quote = currencies

      if (
            base not in STANDARD_FOREX_CURRENCIES
            or quote not in STANDARD_FOREX_CURRENCIES
      ):
            return None

      if quote == "JPY":
            return {
                  "pip_size": 0.01,
                  "price_precision": 3,
            }

      return {
            "pip_size": 0.0001,
            "price_precision": 5,
      }

def calculate_forex_pip_value(pip_size, conversion_rate):
      return pip_size * STANDARD_LOT_UNITS * conversion_rate

def _fx_provider_lookup(from_currency, to_currency, timestamp):
      # No market-data provider is currently configured. Once one is
      # connected, this should return (pair_label, rate, source_label),
      # where pair_label is "BASE/QUOTE" for the rate as quoted by the
      # provider (get_fx_conversion_rate below handles inverting it if
      # the provider only quotes the opposite direction), source_label
      # is "historical_market_data" for a past timestamp or
      # "latest_market_data" for a current one, or None if unavailable.
      return None

def get_fx_conversion_rate(
      from_currency,
      to_currency,
      timestamp
):
      if from_currency == to_currency:
            return 1.0, "not_required"

      quote = _fx_provider_lookup(
            from_currency,
            to_currency,
            timestamp
      )

      if quote is None:
            return None, None

      pair_label, rate, source_label = quote
      quote_base, _, quote_quote = pair_label.partition("/")

      if (
            quote_base == from_currency
            and quote_quote == to_currency
      ):
            return rate, source_label

      if (
            quote_base == to_currency
            and quote_quote == from_currency
            and rate not in (None, 0)
      ):
            return 1.0 / rate, source_label

      return None, None

