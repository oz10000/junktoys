# risk_engine.py
import numpy as np
from config import MAX_LEVERAGE_GLOBAL, RISK_PER_TRADE, MAX_DAILY_LOSS_PCT

def get_optimal_leverage(symbol, atr_pct, confidence, max_leverage=None):
    """
    Calcula el apalancamiento óptimo basado en volatilidad, confianza y métricas.
    Si no se pasa max_leverage, usa el valor global de config.
    """
    max_lev = max_leverage if max_leverage is not None else MAX_LEVERAGE_GLOBAL

    if atr_pct <= 0 or confidence <= 0:
        return 1

    # Fórmula: apalancamiento inversamente proporcional a la volatilidad
    # y directamente proporcional a la confianza
    base_leverage = min(max_lev, 0.25 / (atr_pct * (1 - 0.85)))  # objetivo Win Rate 85%
    leverage = base_leverage * (0.5 + 0.5 * confidence)

    leverage = max(1, min(max_lev, int(round(leverage))))
    return leverage

def get_position_size(capital, leverage, entry_price, risk_per_trade=None):
    """
    Calcula el tamaño de posición en unidades del activo.
    """
    risk_pct = risk_per_trade if risk_per_trade is not None else RISK_PER_TRADE
    position_value = capital * leverage
    size = position_value / entry_price
    return size

def get_max_daily_loss(capital, daily_loss_pct=None):
    """
    Retorna el límite máximo de pérdida diaria.
    """
    loss_pct = daily_loss_pct if daily_loss_pct is not None else MAX_DAILY_LOSS_PCT
    return capital * loss_pct

def calculate_risk_of_ruin(win_rate, profit_factor, initial_capital, risk_per_trade=0.02):
    """
    Calcula el Risk of Ruin (probabilidad de perder más del 50% del capital).
    """
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
