# firm_signals_omega/config.py
"""
Firm Signals Ω — Configuración de Certificación
"""

# ============================================================
# UMBRALES DE CALIDAD POR ACTIVO
# ============================================================
QUALITY_THRESHOLDS = {
    'BTC/USDT': {
        'min_score': 0.65,
        'min_adx': 25,
        'min_ker': 0.45,
        'min_volume_ratio': 1.2,
        'min_cvd': 0,
        'min_timeframes_aligned': 3,
        'max_hold_minutes': 90,
    },
    'ETH/USDT': {
        'min_score': 0.60,
        'min_adx': 22,
        'min_ker': 0.40,
        'min_volume_ratio': 1.15,
        'min_cvd': 0,
        'min_timeframes_aligned': 3,
        'max_hold_minutes': 75,
    },
    'SOL/USDT': {
        'min_score': 0.55,
        'min_adx': 20,
        'min_ker': 0.38,
        'min_volume_ratio': 1.1,
        'min_cvd': 0,
        'min_timeframes_aligned': 2,
        'max_hold_minutes': 60,
    },
}

# ============================================================
# CONFIRMACIONES MULTI-TIMEFRAME
# ============================================================
TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h']
PRIMARY_TF = '5m'
CONFIRMATION_TFS = ['15m', '30m']

# ============================================================
# MICROESTRUCTURA
# ============================================================
MICROSTRUCTURE_THRESHOLDS = {
    'min_imbalance': 0.3,
    'max_funding_rate': 0.01,  # 1% máximo
    'min_oi_growth': 0.02,     # 2% mínimo de crecimiento OI
    'max_spread': 0.0005,      # 0.05% máximo de spread
    'min_depth': 100,          # 100 USDT mínimo de profundidad
}

# ============================================================
# FILTROS TEMPORALES
# ============================================================
HOUR_FILTER = {
    'start': 8,   # 08:00 UTC
    'end': 20     # 20:00 UTC
}

WEEKDAY_FILTER = [0, 1, 2, 3, 4]  # Lunes a Viernes

# ============================================================
# EVENTOS MACRO A EVITAR (ventana de 2h antes/después)
# ============================================================
MACRO_EVENTS = ['FOMC', 'CPI', 'NFP', 'PPI', 'Unemployment', 'GDP']

# ============================================================
# TRAILING STOP — CONFIGURACIÓN OPTIMIZADA
# ============================================================
TRAILING_CONFIG = {
    'mode': 'sin_activacion',  # 'sin_activacion' o 'con_activacion'
    'distance': 0.003,         # 0.3%
    'break_even_trigger': 0.002,  # 0.2%
    'break_even_buffer': 0.0005,  # 0.05%
    'activation_pct': 0.012,   # 1.2% (solo si mode = 'con_activacion')
}

# ============================================================
# APALANCAMIENTO
# ============================================================
LEVERAGE_CONFIG = {
    'BTC/USDT': {'recommended': 5, 'max_reasonable': 8},
    'ETH/USDT': {'recommended': 4, 'max_reasonable': 6},
    'SOL/USDT': {'recommended': 3, 'max_reasonable': 5},
    'default': {'recommended': 3, 'max_reasonable': 5},
}

# ============================================================
# REGÍMENES PERMITIDOS
# ============================================================
ALLOWED_REGIMES = ['Tendencia Fuerte', 'Expansión', 'Tendencia Débil']
REJECTED_REGIMES = ['Chop', 'Rango', 'Compresión']

# ============================================================
# RANGOS DE OPTIMIZACIÓN
# ============================================================
OPTIMIZATION_RANGES = {
    'adx_min': (20, 35),
    'score_min': (0.50, 0.75),
    'ker_min': (0.35, 0.55),
    'volume_ratio': (1.0, 1.5),
    'trailing_distance': (0.001, 0.008),
    'break_even_trigger': (0.001, 0.005),
    'tp_multiplier': (1.0, 3.0),
    'sl_multiplier': (0.3, 1.2),
}

# ============================================================
# VALIDACIÓN
# ============================================================
VALIDATION_CONFIG = {
    'walk_forward_splits': 5,
    'monte_carlo_simulations': 1000,
    'cross_validation_folds': 5,
    'test_size': 0.3,
}

# ============================================================
# CACHÉ Y DATOS
# ============================================================
CACHE_DIR = 'data/firm_cache'
OHLCV_DIR = 'data/ohlcv'
MACRO_DATA_DIR = 'data/macro'

# ============================================================
# LIMITES DE EJECUCIÓN
# ============================================================
MAX_SYMBOLS = 100
MAX_TIMEFRAMES = 6
MAX_HISTORICAL_DAYS = 180  # para certificación