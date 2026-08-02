# amplitude_analyzer.py
import numpy as np
import pandas as pd
from config import AMPLITUDE_LOOKBACK, AMPLITUDE_BUCKETS

def compute_amplitudes(df, lookback=AMPLITUDE_LOOKBACK):
    if df.empty or len(df) < lookback:
        return {}
    
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    volume = df['volume'].values
    
    candle_range = (high - low) / close * 100
    avg_range = np.mean(candle_range[-lookback:])
    std_range = np.std(candle_range[-lookback:])
    
    window_max = pd.Series(high).rolling(lookback).max()
    window_min = pd.Series(low).rolling(lookback).min()
    movement_amplitude = (window_max - window_min) / close * 100
    avg_movement = np.nanmean(movement_amplitude.iloc[-lookback:])
    
    avg_volume = np.mean(volume[-lookback:])
    std_volume = np.std(volume[-lookback:])
    volume_amplitude = std_volume / avg_volume if avg_volume > 0 else 0
    
    time_amplitudes = []
    for i in range(10, len(close) - 10):
        if high[i] == max(high[i-10:i+11]):
            for j in range(i+1, min(i+50, len(close))):
                if low[j] == min(low[j-10:j+11]):
                    time_amplitudes.append(j - i)
                    break
    
    avg_time = np.mean(time_amplitudes) if time_amplitudes else 0
    
    ratios = {
        'range_to_movement': avg_range / avg_movement if avg_movement > 0 else 0,
        'volume_to_price': volume_amplitude / avg_range if avg_range > 0 else 0,
        'time_to_range': avg_time / avg_range if avg_range > 0 else 0,
    }
    
    return {
        'avg_candle_range': avg_range,
        'std_candle_range': std_range,
        'avg_movement': avg_movement,
        'avg_volume': avg_volume,
        'volume_amplitude': volume_amplitude,
        'avg_time_amplitude': avg_time,
        'ratios': ratios,
        'buckets': _compute_buckets(candle_range[-lookback:], AMPLITUDE_BUCKETS)
    }

def _compute_buckets(values, n_buckets=AMPLITUDE_BUCKETS):
    if len(values) == 0:
        return {}
    hist, bins = np.histogram(values, bins=n_buckets)
    return {
        'bins': bins.tolist(),
        'hist': hist.tolist(),
        'percentiles': {
            '25': np.percentile(values, 25),
            '50': np.percentile(values, 50),
            '75': np.percentile(values, 75),
            '90': np.percentile(values, 90),
            '95': np.percentile(values, 95),
        }
    }

def predict_amplitude(amplitudes, regime, direction='neutral'):
    base = amplitudes.get('avg_candle_range', 0.5)
    volatility_factor = amplitudes.get('volume_amplitude', 1.0)
    
    regime_factors = {
        'Expansión': 1.5,
        'Tendencia Fuerte': 1.3,
        'Tendencia': 1.1,
        'Normal': 1.0,
        'Chop': 0.7,
    }
    regime_factor = regime_factors.get(regime, 1.0)
    direction_factor = 1.1 if direction == 'Long' else 1.05 if direction == 'Short' else 1.0
    predicted = base * volatility_factor * regime_factor * direction_factor
    return predicted

def define_zones(avg_range, current_price):
    zones = {}
    zone_configs = {
        'A': 0.3,
        'B': 0.6,
        'C': 1.0,
    }
    for name, factor in zone_configs.items():
        distance = avg_range * factor / 100 * current_price
        zones[name] = {
            'distance': distance,
            'pct': avg_range * factor / 100,
            'support': current_price - distance,
            'resistance': current_price + distance,
        }
    return zones
