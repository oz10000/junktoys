# firm_signals_omega/helpers.py
"""
Funciones auxiliares para Firm Signals Ω
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple

from .next_trade_engine import NextTradeEngine

def estimate_next_opportunity(
    best_signal: Dict,
    signal_history: List[Dict],
    firm_history: List[Dict] = None
) -> Dict:
    """
    Estima el tiempo y probabilidad hasta la próxima señal de alta calidad.
    Utiliza NextTradeEngine para una estimación dinámica.
    """
    engine = NextTradeEngine({})
    engine.update_history(signal_history, firm_history or [])

    regime = best_signal.get('regime', 'Normal')
    adx = best_signal.get('adx', 20)
    atr_pct = best_signal.get('atr_pct', 0.1)
    now = datetime.now()
    current_minute = (now.minute % 5)
    last_signal_time = signal_history[-1]['timestamp'] if signal_history else None

    result = engine.estimate(regime, adx, atr_pct, current_minute, last_signal_time, is_firm=False)

    return {
        'remaining_minutes': result['expected_time_minutes'],
        'probability_15min': result['probability_15min'],
        'probability_30min': result['probability_30min'],
        'probability_1h': result['probability_60min'],
        'probability_3h': result['probability_180min'],
        'confidence': result['confidence'],
        'status': result['status'],
        'countdown': result['countdown'],
        'recommendation': result['recommendation']
    }

def calculate_support_resistance(
    df: pd.DataFrame,
    price: float,
    window: int = 20
) -> Dict:
    if df is None or df.empty or len(df) < window:
        return {'support': None, 'resistance': None, 'distance_support': None, 'distance_resistance': None}

    try:
        from support_resistance import find_pivots
        supports, resistances = find_pivots(df, window=window)
    except ImportError:
        supports = [(df['low'].iloc[-window:].min(), 0.5)]
        resistances = [(df['high'].iloc[-window:].max(), 0.5)]

    nearest_support = None
    nearest_resistance = None
    for sup, qual in supports:
        if sup < price:
            if nearest_support is None or (price - sup) < (price - nearest_support[0]):
                nearest_support = (sup, qual)
    for res, qual in resistances:
        if res > price:
            if nearest_resistance is None or (res - price) < (nearest_resistance[0] - price):
                nearest_resistance = (res, qual)

    return {
        'support': nearest_support[0] if nearest_support else None,
        'resistance': nearest_resistance[0] if nearest_resistance else None,
        'distance_support': (price - nearest_support[0]) / price * 100 if nearest_support else None,
        'distance_resistance': (nearest_resistance[0] - price) / price * 100 if nearest_resistance else None,
        'support_quality': nearest_support[1] if nearest_support else None,
        'resistance_quality': nearest_resistance[1] if nearest_resistance else None,
    }

def suggest_leverage(
    volatility: float,
    confidence: float,
    max_leverage: int = 10,
    min_leverage: int = 1
) -> Dict:
    if volatility <= 0:
        return {'recommended': min_leverage, 'max_allowed': max_leverage, 'reason': 'Volatilidad cero'}

    base = 5
    vol_factor = 0.5 / volatility
    conf_factor = 0.5 + 0.5 * confidence
    raw = base * (vol_factor / 10) * conf_factor
    recommended = max(min_leverage, min(max_leverage, int(round(raw))))

    reason = (
        f"Volatilidad {volatility*100:.2f}% → factor {vol_factor/10:.2f}, "
        f"Confianza {confidence*100:.0f}% → factor {conf_factor:.2f}"
    )
    return {
        'recommended': recommended,
        'max_allowed': max_leverage,
        'reason': reason
    }

def format_signal_reason(signal: Dict) -> str:
    if not signal or not signal.get('is_valid', False):
        return "Señal no válida"

    parts = []
    if signal.get('score', 0) >= 0.30:
        parts.append(f"Score {signal['score']:.2f} ≥ 0.30")
    else:
        parts.append(f"Score {signal['score']:.2f} < 0.30 (no aprobada)")

    if signal.get('adx', 0) >= 22:
        parts.append(f"ADX {signal['adx']:.1f} ≥ 22")
    else:
        parts.append(f"ADX {signal['adx']:.1f} < 22 (no aprobada)")

    if signal.get('ker', 0) >= 0.42:
        parts.append(f"KER {signal['ker']:.2f} ≥ 0.42")
    else:
        parts.append(f"KER {signal['ker']:.2f} < 0.42 (no aprobada)")

    if signal.get('regime') not in ['Chop', 'Rango']:
        parts.append(f"Régimen {signal['regime']} permitido")
    else:
        parts.append(f"Régimen {signal['regime']} no permitido (no aprobada)")

    return " | ".join(parts) if parts else "Condiciones no especificadas"
