import os


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

VALID_MARKET_TYPES = (
      "futures",
      "forex",
)

FUTURES_ONLY_FIELDS = (
      "contracts",
      "tick_size",
      "tick_value",
      "point_value",
      "points_pnl",
      "ticks_pnl",
)

FOREX_ONLY_FIELDS = (
      "lot_size",
      "pip_size",
      "pip_value",
      "price_precision",
      "pips_pnl",
      "standard_lot_units",
      "account_currency",
      "conversion_rate",
      "conversion_pair",
      "conversion_timestamp",
      "conversion_rate_source",
)

FUTURES_INSTRUMENT_PROFILES = {
      "ES": {
            "name": "E-mini S&P 500",
            "tick_size": 0.25,
            "tick_value": 12.50,
            "point_value": 50.00,
      },
      "MES": {
            "name": "Micro E-mini S&P 500",
            "tick_size": 0.25,
            "tick_value": 1.25,
            "point_value": 5.00,
      },
      "NQ": {
            "name": "E-mini Nasdaq-100",
            "tick_size": 0.25,
            "tick_value": 5.00,
            "point_value": 20.00,
      },
      "MNQ": {
            "name": "Micro E-mini Nasdaq-100",
            "tick_size": 0.25,
            "tick_value": 0.50,
            "point_value": 2.00,
      },
      "YM": {
            "name": "E-mini Dow",
            "tick_size": 1.0,
            "tick_value": 5.00,
            "point_value": 5.00,
      },
      "MYM": {
            "name": "Micro E-mini Dow",
            "tick_size": 1.0,
            "tick_value": 0.50,
            "point_value": 0.50,
      },
      "RTY": {
            "name": "E-mini Russell 2000",
            "tick_size": 0.10,
            "tick_value": 5.00,
            "point_value": 50.00,
      },
      "M2K": {
            "name": "Micro E-mini Russell 2000",
            "tick_size": 0.10,
            "tick_value": 0.50,
            "point_value": 5.00,
      },
      "CL": {
            "name": "WTI Crude Oil",
            "tick_size": 0.01,
            "tick_value": 10.00,
            "point_value": 1000.00,
      },
      "MCL": {
            "name": "Micro WTI Crude Oil",
            "tick_size": 0.01,
            "tick_value": 1.00,
            "point_value": 100.00,
      },
      "GC": {
            "name": "Gold",
            "tick_size": 0.10,
            "tick_value": 10.00,
            "point_value": 100.00,
      },
      "MGC": {
            "name": "Micro Gold",
            "tick_size": 0.10,
            "tick_value": 1.00,
            "point_value": 10.00,
      },
      "SI": {
            "name": "Silver",
            "tick_size": 0.005,
            "tick_value": 25.00,
            "point_value": 5000.00,
      },
      "SIL": {
            "name": "Micro Silver",
            "tick_size": 0.005,
            "tick_value": 5.00,
            "point_value": 1000.00,
      },
}

for _profile_root, _profile in FUTURES_INSTRUMENT_PROFILES.items():
      assert (
            abs(
                  _profile["point_value"]
                  - _profile["tick_value"] / _profile["tick_size"]
            )
            < 1e-9
      ), (
            f"{_profile_root} profile is inconsistent: "
            "point_value must equal tick_value / tick_size."
      )

FUTURES_MONTH_CODES = set("FGHJKMNQUVXZ")

STANDARD_FOREX_CURRENCIES = {
      "USD",
      "EUR",
      "GBP",
      "JPY",
      "CHF",
      "CAD",
      "AUD",
      "NZD",
}

FLOATING_POINT_TOLERANCE = 1e-6

STANDARD_LOT_UNITS = 100000

CONVERSION_SOURCE_LABELS = {
      "not_required": "quote currency match",
      "trade_exit_price": "Trade exit price",
      "historical_market_data": "Historical market data",
      "latest_market_data": "Latest market data",
      "manual": "Manually supplied",
}
