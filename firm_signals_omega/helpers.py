# firm_signals_omega/helpers.py
"""
Funciones auxiliares para Firm Signals Ω
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple

def estimate_next_opportunity(
    best_signal: Dict,
    signal_history: List[Dict]
) -> Dict:
    """
    Estima el tiempo y probabilidad hasta la próxima señal de alta calidad.
    """
    # Si ya hay señal válida, tiempo = 0
    if best_signal and best_signal.get('is_valid', False):
        return {
            'remaining_minutes': 0,
            'probability_15min': 1.0,
            'probability_30min': 1.0,
            'probability_1h': 1.0,
            'probability_3h': 1.0,
            'confidence': 1.0
        }

    # Filtrar historial de señales válidas
    valid_times = [s['timestamp'] for s in signal_history if s.get('is_valid', False)]
    if len(valid_times) < 2:
        # Sin historial suficiente, usar estimación heurística
        return {
            'remaining_minutes': 45,
            'probability_15min': 0.15,
            'probability_30min': 0.35,
            'probability_1h': 0.55,
            'probability_3h': 0.75,
            'confidence': 0.6
        }

    # Calcular intervalos entre señales previas
    intervals = [(valid_times[i+1] - valid_times[i]).total_seconds() / 60
                 for i in range(len(valid_times)-1)]
    avg_interval = np.mean(intervals)
    std_interval = np.std(intervals)

    # Última señal
    last_time = valid_times[-1]
    elapsed = (datetime.now() - last_time).total_seconds() / 60
    remaining = max(0, avg_interval - elapsed)

    # Probabilidades usando distribución normal (aproximación)
    def prob(minutes: int) -> float:
        if avg_interval <= 0:
            return 0.0
        z = (minutes - avg_interval) / std_interval if std_interval > 0 else 0
        # CDF normal aproximada
        return min(0.95, 0.5 * (1 + np.tanh(z * 0.5)))

    return {
        'remaining_minutes': remaining,
        'probability_15min': prob(15),
        'probability_30min': prob(30),
        'probability_1h': prob(60),
        'probability_3h': prob(180),
        'confidence': 1 - (std_interval / avg_interval) if avg_interval > 0 else 0.5
    }

def calculate_support_resistance(
    df: pd.DataFrame,
    price: float,
    window: int = 20
) -> Dict:
    """
    Calcula soporte y resistencia principales basado en pivotes y volumen.
    """
    if df is None or df.empty or len(df) < window:
        return {'support': None, 'resistance': None, 'distance_support': None, 'distance_resistance': None}

    try:
        from support_resistance import find_pivots
        supports, resistances = find_pivots(df, window=window)
    except ImportError:
        # Fallback simple: usar min/max de la ventana
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
    """
    Sugiere apalancamiento dinámico basado en volatilidad y confianza.
    """
    # volatilidad: ATR% (0.01 = 1%)
    # confidence: 0-1
    if volatility <= 0:
        return {'recommended': min_leverage, 'max_allowed': max_leverage, 'reason': 'Volatilidad cero'}

    # Kelly fraccional: apalancamiento = (confianza - (1-confianza)/reward_ratio) * factor
    # Simplificación: inversamente proporcional a volatilidad y proporcional a confianza
    base = 5  # apalancamiento base
    vol_factor = 0.5 / volatility  # si ATR=1%, factor=50; si ATR=2%, factor=25
    conf_factor = 0.5 + 0.5 * confidence
    raw = base * (vol_factor / 10) * conf_factor  # ajuste de escala
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
    """
    Genera una explicación textual de por qué la señal fue aprobada.
    """
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
