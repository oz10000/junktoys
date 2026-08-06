# firm_signals_omega/settings.py
"""
Configuración específica de Firm Signals Ω
"""

FIRM_SIGNALS_CONFIG = {
    'enabled': False,
    'quality_thresholds': {
        'BTC/USDT': {'min_score': 0.65, 'min_adx': 25, 'min_ker': 0.45},
        'ETH/USDT': {'min_score': 0.60, 'min_adx': 22, 'min_ker': 0.40},
        'SOL/USDT': {'min_score': 0.55, 'min_adx': 20, 'min_ker': 0.38},
    },
    'confirmation_thresholds': {
        'BTC/USDT': {'min_timeframes': 3},
        'ETH/USDT': {'min_timeframes': 3},
        'SOL/USDT': {'min_timeframes': 2},
    },
    'microstructure_thresholds': {
        'min_imbalance': 0.3,
        'max_funding_rate': 0.01,
        'min_oi_growth': 0.02,
    },
    'hour_filter': {'start': 8, 'end': 20},
    'weekday_filter': [0, 1, 2, 3, 4],
    'trailing_config': {
        'mode': 'sin_activacion',
        'distance': 0.003,
        'break_even_trigger': 0.002,
        'break_even_buffer': 0.0005,
    }
}
