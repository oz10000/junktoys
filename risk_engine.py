# risk_engine.py
import numpy as np
from config import MAX_LEVERAGE_GLOBAL, RISK_PER_TRADE, MAX_DAILY_LOSS_PCT

def get_optimal_leverage(symbol, atr_pct, confidence, metrics, max_leverage=None):
    """
    Calcula el apalancamiento óptimo basado en estadísticas del sistema
    """
    max_lev = max_leverage or MAX_LEVERAGE_GLOBAL
    
    if atr_pct <= 0:
        return 1
    
    # Factor base por volatilidad
    vol_factor = 0.25 / (atr_pct * 100 * 2)
    
    # Factor por confianza
    conf_factor = 0.5 + 0.5 * confidence
    
    # Factor por métricas históricas
    win_rate = metrics.get('win_rate', 0.5)
    profit_factor = min(metrics.get('profit_factor', 1.0), 3.0)
    hist_factor = 0.3 + 0.7 * (win_rate * 0.6 + (profit_factor / 3.0) * 0.4)
    
    # Factor por riesgo (drawdown)
    max_dd = metrics.get('max_dd', 0.1)
    risk_factor = 1 - min(max_dd / 0.2, 0.5)
    
    leverage = vol_factor * conf_factor * hist_factor * risk_factor * 10
    leverage = max(1, min(max_lev, int(round(leverage))))
    return leverage

def get_position_size(capital, leverage, entry_price, risk_per_trade=None):
    """
    Calcula el tamaño de posición óptimo (en unidades del activo)
    """
    risk_pct = risk_per_trade or RISK_PER_TRADE
    position_value = capital * leverage
    size = position_value / entry_price
    return size

def get_max_daily_loss(capital, daily_loss_pct=None):
    """Retorna el límite máximo de pérdida diaria"""
    loss_pct = daily_loss_pct or MAX_DAILY_LOSS_PCT
    return capital * loss_pct

def calculate_risk_of_ruin(win_rate, profit_factor, initial_capital, risk_per_trade=0.02):
    """
    Calcula el Risk of Ruin (probabilidad de perder más del 50% del capital)
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
