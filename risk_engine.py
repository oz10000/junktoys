# risk_engine.py
import numpy as np
from config import MAX_LEVERAGE_GLOBAL, RISK_PER_TRADE, MAX_DAILY_LOSS_PCT

def get_optimal_leverage(symbol, atr_pct, confidence, metrics, max_leverage=None):
    """
    Calcula el apalancamiento óptimo basado en:
    - volatilidad (ATR%)
    - confianza de la señal
    - métricas históricas del activo
    - límite máximo por activo

    Si atr_pct es un dict (por ejemplo, de amplitude_analyzer), se extrae el valor numérico.
    """
    # Asegurar que atr_pct sea un número
    if isinstance(atr_pct, dict):
        # Intentar extraer el valor de 'avg_candle_range' o similar
        if 'avg_candle_range' in atr_pct:
            atr_pct = atr_pct['avg_candle_range']
        else:
            # Tomar el primer valor numérico
            values = [v for v in atr_pct.values() if isinstance(v, (int, float))]
            if values:
                atr_pct = values[0]
            else:
                atr_pct = 0.01  # valor por defecto
    # Si aún es dict (no se pudo extraer), usar valor por defecto
    if isinstance(atr_pct, dict):
        atr_pct = 0.01

    try:
        atr_pct = float(atr_pct)
    except (TypeError, ValueError):
        atr_pct = 0.01

    # Limitar atr_pct a un rango razonable (0.001% a 5%)
    atr_pct = max(0.001, min(5.0, atr_pct))

    max_lev = max_leverage or MAX_LEVERAGE_GLOBAL
    if max_lev is None:
        max_lev = 10  # valor por defecto

    # Fórmula: apalancamiento inversamente proporcional a la volatilidad
    # y proporcional a la confianza
    base_leverage = min(max_lev, 0.25 / (atr_pct * 0.15))  # target Win Rate 85%
    confidence_factor = 0.5 + 0.5 * confidence
    leverage = base_leverage * confidence_factor
    leverage = max(1, min(max_lev, int(round(leverage))))
    return leverage

def get_position_size(capital, leverage, entry_price, risk_per_trade=None):
    risk_pct = risk_per_trade or RISK_PER_TRADE
    position_value = capital * leverage
    size = position_value / entry_price
    return size

def get_max_daily_loss(capital, daily_loss_pct=None):
    loss_pct = daily_loss_pct or MAX_DAILY_LOSS_PCT
    return capital * loss_pct

def calculate_risk_of_ruin(win_rate, profit_factor, initial_capital, risk_per_trade=0.02):
    if win_rate <= 0 or profit_factor <= 0:
        return 1.0
    kelly = win_rate - (1 - win_rate) / profit_factor if profit_factor > 0 else 0
    kelly = max(0, min(1, kelly))
    if kelly <= 0:
        return 1.0
    risk_ratio = risk_per_trade / kelly
    if risk_ratio <= 0:
        return 1.0
    ruin_prob = np.exp(-2 * kelly * risk_ratio)
    return min(ruin_prob, 1.0)
