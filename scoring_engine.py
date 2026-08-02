# scoring_engine.py
import numpy as np
import pandas as pd
from config import SCORING_WEIGHTS, REGIME_SCORES
from support_resistance import compute_sr_strength
from amplitude_analyzer import predict_amplitude

def compute_advanced_score(signal, historical_metrics, market_data, sr_data):
    """
    Calcula un score normalizado (0-1) basado en múltiples factores
    """
    w = SCORING_WEIGHTS
    score = 0.0
    details = {}
    
    # 1. RÉGIMEN
    regime_score = REGIME_SCORES.get(signal.regime, 0.5)
    details['regime'] = regime_score
    score += w['regime'] * regime_score
    
    # 2. CALIDAD DE TENDENCIA
    adx_norm = min(signal.adx / 50, 1.0)
    ker_norm = min(signal.ker / 0.8, 1.0)
    trend_quality = (adx_norm * 0.5 + ker_norm * 0.5)
    details['trend_quality'] = trend_quality
    score += w['trend_quality'] * trend_quality
    
    # 3. VOLATILIDAD
    atr_opt = 0.02
    vol_score = 1 - abs(signal.atr_pct - atr_opt) / 0.04
    vol_score = max(0, min(1, vol_score))
    details['volatility'] = vol_score
    score += w['volatility'] * vol_score
    
    # 4. WIN RATE HISTÓRICO
    win_rate = historical_metrics.get('win_rate', 0.5)
    details['win_rate'] = win_rate
    score += w['historical_winrate'] * win_rate
    
    # 5. PROFIT FACTOR
    pf = min(historical_metrics.get('profit_factor', 1.0) / 2.0, 1.0)
    details['profit_factor'] = pf
    score += w['historical_profit_factor'] * pf
    
    # 6. EXPECTANCY
    exp = historical_metrics.get('expectancy', 0.0)
    exp_norm = min(exp / 0.02, 1.0)
    details['expectancy'] = exp_norm
    score += w['expectancy'] * exp_norm
    
    # 7. RIESGO
    max_dd = historical_metrics.get('max_dd', 0.1)
    risk_score = 1 - min(max_dd / 0.2, 1.0)
    details['risk'] = risk_score
    score += w['risk'] * risk_score
    
    # 8. CALIDAD ESTADÍSTICA
    n = historical_metrics.get('n_trades', 0)
    stat_score = min(np.log(n + 1) / np.log(100), 1.0)
    details['statistical'] = stat_score
    score += w['statistical_quality'] * stat_score
    
    # 9. MICROESTRUCTURA
    if market_data:
        spread = market_data.get('spread', 0.001)
        volume = market_data.get('volume', 0)
        spread_score = 1 - min(spread / 0.01, 1.0)
        volume_score = min(volume / 1e7, 1.0)
        micro_score = spread_score * 0.5 + volume_score * 0.5
    else:
        micro_score = 0.5
    details['microstructure'] = micro_score
    score += w['microstructure'] * micro_score
    
    # 10. SOPORTES Y RESISTENCIAS
    if sr_data:
        sup, res, sr_strength = sr_data
        details['sr_strength'] = sr_strength
        score += w['support_resistance'] * sr_strength
    
    return np.clip(score, 0, 1), details

def compute_confidence(score, signal, historical_metrics):
    """
    Calcula la confianza asociada al score
    """
    confidence = score
    n = historical_metrics.get('n_trades', 0)
    n_factor = min(n / 50, 1.0)
    confidence *= (0.7 + 0.3 * n_factor)
    win_rate = historical_metrics.get('win_rate', 0.5)
    consistency = 1 - abs(win_rate - 0.5) * 2
    confidence *= (0.8 + 0.2 * consistency)
    regime_factor = 1.0 if signal.regime != 'Chop' else 0.7
    confidence *= regime_factor
    return np.clip(confidence, 0, 1)
