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
    (Mantiene compatibilidad con la versión anterior, pero ahora usa NextTradeEngine)
    """
    # Esta función se mantiene por compatibilidad, pero se recomienda usar NextTradeEngine
    # Ahora simplemente llama al motor
    from .next_trade_engine import NextTradeEngine
    engine = NextTradeEngine({})
    engine.update_history(signal_history, [])  # no tenemos firm_history aquí
    # Obtener estado actual desde best_signal y session_state
    regime = best_signal.get('regime', 'Normal')
    adx = best_signal.get('adx', 20)
    atr_pct = best_signal.get('atr_pct', 0.1)
    # calcular minutos dentro de la vela (simplificado)
    now = datetime.now()
    current_minute = (now.minute % 5)  # asumiendo velas de 5m
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
        'countdown': engine.get_countdown(result['expected_time_minutes']),
        'recommendation': engine.get_next_recommendation(result['status'], result['expected_time_minutes'])
    }

def calculate_support_resistance(
    df: pd.DataFrame,
    price: float,
    window: int = 20
) -> Dict:
    # ... (misma función que antes, sin cambios) ...
    pass

def suggest_leverage(
    volatility: float,
    confidence: float,
    max_leverage: int = 10,
    min_leverage: int = 1
) -> Dict:
    # ... (misma función que antes, sin cambios) ...
    pass

def format_signal_reason(signal: Dict) -> str:
    # ... (misma función que antes, sin cambios) ...
    pass
