# amplitude_analyzer.py
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from config import AMPLITUDE_LOOKBACK, AMPLITUDE_BUCKETS

def compute_amplitudes(df: pd.DataFrame, lookback: int = AMPLITUDE_LOOKBACK) -> Dict:
    """
    Calcula amplitudes de precio y tiempo para el DataFrame dado.
    Retorna métricas para el timeframe del DataFrame.
    """
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
        'buckets': _compute_buckets(candle_range[-lookback:], AMPLITUDE_BUCKETS),
        'candle_range': candle_range[-lookback:].tolist(),
    }

def _compute_buckets(values: np.ndarray, n_buckets: int = AMPLITUDE_BUCKETS) -> Dict:
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

def predict_amplitude(amplitudes: Dict, regime: str, direction: str = 'neutral') -> float:
    """Predice la amplitud esperada para la próxima operación."""
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

    return base * volatility_factor * regime_factor * direction_factor

def define_zones(avg_range: float, current_price: float) -> Dict:
    """Define zonas de entrada A, B, C basadas en la amplitud promedio."""
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

def get_amplitudes_by_timeframe(data_dict: Dict, timeframes: Optional[List[str]] = None) -> Dict:
    """
    Obtiene amplitudes para múltiples timeframes.
    data_dict: {timeframe: DataFrame}
    Si no se proporciona, usa el principal y aplica heurística para otros.
    """
    if timeframes is None:
        timeframes = ['5m', '1h', '4h']

    result = {}
    if not data_dict:
        return result

    # Si solo hay un DataFrame, usar ese como base y extrapolar
    if len(data_dict) == 1:
        tf = list(data_dict.keys())[0]
        df = data_dict[tf]
        base_amp = compute_amplitudes(df).get('avg_candle_range', 0)
        # Factores de escalado heurísticos para otros timeframes
        scaling = {
            '5m': 1.0,
            '15m': 1.8,
            '30m': 2.5,
            '1h': 3.5,
            '4h': 7.0,
            '1d': 15.0,
        }
        for target_tf in timeframes:
            factor = scaling.get(target_tf, 1.0)
            result[target_tf] = base_amp * factor
    else:
        # Calcular para cada timeframe disponible
        for tf, df in data_dict.items():
            if not df.empty:
                result[tf] = compute_amplitudes(df).get('avg_candle_range', 0)
        # Completar los faltantes con extrapolación
        # (Implementación simplificada; en producción se puede mejorar)
        if timeframes:
            available = list(result.keys())
            if available:
                base_tf = available[0]
                base_val = result[base_tf]
                scaling = {
                    '5m': 1.0,
                    '15m': 1.8,
                    '30m': 2.5,
                    '1h': 3.5,
                    '4h': 7.0,
                    '1d': 15.0,
                }
                for tf in timeframes:
                    if tf not in result:
                        factor = scaling.get(tf, 1.0)
                        result[tf] = base_val * factor

    return result
