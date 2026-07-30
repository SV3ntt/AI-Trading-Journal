import math
from datetime import datetime, timedelta

from journal.constants import FLOATING_POINT_TOLERANCE


def calculate_points_pnl(direction, entry, exit_price):
      if direction == "long":
            return exit_price - entry
      else:
            return entry - exit_price
      
def calculate_dollar_pnl(points_pnl, point_value, contracts):
      return points_pnl * point_value * contracts

def calculate_net_dollar_pnl(dollar_pnl, commission):
      return dollar_pnl - commission

def calculate_realized_r(dollar_pnl, risk_amount):
      if risk_amount > 0:
            return dollar_pnl / risk_amount
      else:
            return 0

def calculate_result(points_pnl):
      if points_pnl > 0:
            return "Win"
      elif points_pnl < 0:
            return "Loss"
      else:
            return "Break-even"

def calculate_net_result(net_dollar_pnl):
      if net_dollar_pnl > 0:
            return "Win"
      elif net_dollar_pnl < 0:
            return "Loss"
      else:
            return "Break-even"

def is_multiple_of(value, unit, tolerance=FLOATING_POINT_TOLERANCE):
      if unit <= 0:
            return False

      ratio = value / unit

      return abs(ratio - round(ratio)) < tolerance

def clean_float_noise(value, tolerance=FLOATING_POINT_TOLERANCE):
      nearest_int = round(value)

      if abs(value - nearest_int) < tolerance:
            return float(nearest_int) + 0.0

      for decimals in range(1, 9):
            rounded = round(value, decimals)

            if abs(value - rounded) < tolerance:
                  return rounded + 0.0

      return value

def calculate_ticks_pnl(points_pnl, tick_size):
      return clean_float_noise(points_pnl / tick_size)

def calculate_pips_pnl(points_pnl, pip_size):
      return clean_float_noise(points_pnl / pip_size)

def calculate_duration(entry_time, exit_time):
      entry_datetime = datetime.strptime(entry_time, "%H:%M")
      exit_datetime = datetime.strptime(exit_time, "%H:%M")

      if exit_datetime < entry_datetime:
            exit_datetime = exit_datetime + timedelta(days=1)

      duration = exit_datetime - entry_datetime
      duration_minutes = int(duration.total_seconds() / 60)

      return duration_minutes

def get_finite_number(
      value,
      field_name,
      minimum=None,
      minimum_is_strict=False,
):
      if isinstance(value, bool):
            raise ValueError(
                  f"{field_name} must be a number. "
            )

      try:
            number = float(value)
      
      except (TypeError, ValueError):
            raise ValueError(
                  f"{field_name} must be a number. "
            )

      if not math.isfinite(number):
            raise ValueError(
                  f"{field_name} must be a finite "
                  "number. "
            )

      if minimum is not None:
            if (
                  minimum_is_strict
                  and number <= minimum
            ):
                  raise ValueError(
                        f"{field_name} must be "
                        f"greater than {minimum}. "
                  )

            if (
                  not minimum_is_strict
                  and number < minimum 
            ):

                  raise ValueError(
                        f"{field_name} must be "
                        f"greater than or equal to "
                        f"{minimum}. "
                  )

      return number

def get_positive_integer(
      value,
      field_name
):

      if isinstance(value, bool):
            raise ValueError(
                  f"{field_name} must be a whole "
                  "number greater than 0."
            )

      try:
            number = float(value)

      except (TypeError, ValueError):
            raise ValueError(
                  f"{field_name} must be a whole "
                  "number greater than 0."
            )

      if (
            not math.isfinite(number)
            or not number.is_integer()
            or number <= 0
      ):
            raise ValueError(
                  f"{field_name} must be a whole "
                  "number greater than 0."
            )

      return int(number)

def normalize_date_value(value):
      date_text = (
            str(value)
            .strip()
            .replace (" ", "-")
      )

      parsed_date = datetime.strptime(
            date_text, 
            "%Y-%m-%d"
      )

      return parsed_date.strftime(
            "%Y-%m-%d"
      )

def normalize_time_value(value):
      time_text = str(value).strip()

      parsed_time = datetime.strptime(
            time_text,
            "%H:%M"
      )

      return parsed_time.strftime(
            "%H:%M"
      )

