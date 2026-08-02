# utils.py
import pandas as pd
import pytz
from config import TIMEZONE, HOUR_FILTER_START, HOUR_FILTER_END

def apply_hour_filter(df, start_hour=HOUR_FILTER_START, end_hour=HOUR_FILTER_END):
    if start_hour == 0 and end_hour == 23:
        return df
    if df.empty:
        return df
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(TIMEZONE)
    else:
        df = df.tz_convert(TIMEZONE)
    hour = df.index.hour
    return df[(hour >= start_hour) & (hour <= end_hour)]

def calculate_hourly_profit(total_return, total_hours):
    if total_hours == 0:
        return 0.0
    return (total_return / total_hours) * 100

def format_currency(value):
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"

def format_percentage(value):
    if value is None:
        return "0.00%"
    return f"{value:.2%}"

def safe_float(value, default=0.0):
    try:
        return float(value)
    except:
        return default

def safe_int(value, default=0):
    try:
        return int(value)
    except:
        return default
