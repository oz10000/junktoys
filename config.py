# config.py
import pytz

# ============================================================
# VERSIÓN Y NOMBRE
# ============================================================
VERSION = "6.5.0"
PROJECT_NAME = "Junk Toys — Multi-Exchange"

# ============================================================
# EXCHANGES QUE FUNCIONAN EN GITHUB ACTIONS
# ============================================================
EXCHANGE_PRIORITY = [
    'okx',      # ✅ Funciona (swap)
    'kucoin',   # ✅ Funciona (future)
    'mexc',     # ✅ Funciona (future)
    'kraken',   # ✅ Funciona (spot)
]

EXCHANGE_CONFIGS = {
    'okx': {
        'class': 'okx',
        'options': {'defaultType': 'swap'},
        'description': 'OKX Swap',
    },
    'kucoin': {
        'class': 'kucoin',
        'options': {'defaultType': 'future'},
        'description': 'KuCoin Futures',
    },
    'mexc': {
        'class': 'mexc',
        'options': {'defaultType': 'future'},
        'description': 'MEXC Futures',
    },
    'kraken': {
        'class': 'kraken',
        'options': {'defaultType': 'spot'},
        'description': 'Kraken Spot',
    },
}

# ============================================================
# LISTA DE RESPALDO DE SÍMBOLOS (cuando la API no devuelve nada)
# ============================================================
FALLBACK_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT',
    'LINK/USDT', 'ADA/USDT', 'DOT/USDT', 'AVAX/USDT', 'DOGE/USDT',
    'MATIC/USDT', 'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'BCH/USDT'
]

# ============================================================
# TIMEFRAME Y DATOS
# ============================================================
TIMEFRAME = '5m'
TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
PRIMARY_TF = '5m'
LOOKBACK_DAYS = 365
INITIAL_CAPITAL = 10000.0
COMMISSION = 0.0004
SLIPPAGE = 0.0005
TIMEZONE = pytz.timezone('America/Argentina/Buenos_Aires')

# ============================================================
# RIESGO Y APALANCAMIENTO
# ============================================================
MAX_LEVERAGE_GLOBAL = 10
RISK_PER_TRADE = 0.02
MAX_DAILY_LOSS_PCT = 0.08
MAX_POSITIONS = 3
MIN_RISK_REWARD_RATIO = 1.5

# ============================================================
# FILTRO HORARIO
# ============================================================
HOUR_FILTER_START = 10
HOUR_FILTER_END = 17
USE_HOUR_FILTER = True

# ============================================================
# PARÁMETROS GLOBALES OPTIMIZADOS
# ============================================================
DEFAULT_PARAMS = {
    'min_score': 0.32,
    'adx_threshold': 22,
    'ker_threshold': 0.42,
    'tp_mult': 2.5,
    'sl_mult': 1.0,
    'trailing_distance': 0.008,
    'trailing_activation': 0.012,
    'trailing_callback': 0.003,
    'break_even_trigger': 0.008,
    'break_even_buffer': 0.002,
    'max_hold_minutes': 120,
    'rotation_confidence_gap': 0.15,
}

# ============================================================
# PARÁMETROS POR ACTIVO
# ============================================================
ASSET_PARAMS = {
    'BTC/USDT': {'min_score': 0.28, 'adx_threshold': 18, 'ker_threshold': 0.38, 'tp_mult': 2.8, 'sl_mult': 0.9, 'trailing_distance': 0.006, 'trailing_activation': 0.012, 'break_even_trigger': 0.008, 'leverage': 6},
    'ETH/USDT': {'min_score': 0.30, 'adx_threshold': 20, 'ker_threshold': 0.40, 'tp_mult': 2.5, 'sl_mult': 1.0, 'trailing_distance': 0.007, 'trailing_activation': 0.014, 'break_even_trigger': 0.009, 'leverage': 5},
    'SOL/USDT': {'min_score': 0.35, 'adx_threshold': 24, 'ker_threshold': 0.45, 'tp_mult': 2.2, 'sl_mult': 1.1, 'trailing_distance': 0.009, 'trailing_activation': 0.018, 'break_even_trigger': 0.012, 'leverage': 4},
    'XRP/USDT': {'min_score': 0.32, 'adx_threshold': 22, 'ker_threshold': 0.42, 'tp_mult': 2.4, 'sl_mult': 1.0, 'trailing_distance': 0.008, 'trailing_activation': 0.016, 'break_even_trigger': 0.010, 'leverage': 4},
    'BNB/USDT': {'min_score': 0.33, 'adx_threshold': 22, 'ker_threshold': 0.43, 'tp_mult': 2.3, 'sl_mult': 1.0, 'trailing_distance': 0.008, 'trailing_activation': 0.015, 'break_even_trigger': 0.010, 'leverage': 4},
    'LINK/USDT': {'min_score': 0.34, 'adx_threshold': 23, 'ker_threshold': 0.44, 'tp_mult': 2.3, 'sl_mult': 1.0, 'trailing_distance': 0.008, 'trailing_activation': 0.016, 'break_even_trigger': 0.011, 'leverage': 4},
    'ADA/USDT': {'min_score': 0.38, 'adx_threshold': 26, 'ker_threshold': 0.48, 'tp_mult': 2.0, 'sl_mult': 1.2, 'trailing_distance': 0.010, 'trailing_activation': 0.020, 'break_even_trigger': 0.014, 'leverage': 3},
    'DOT/USDT': {'min_score': 0.36, 'adx_threshold': 25, 'ker_threshold': 0.46, 'tp_mult': 2.1, 'sl_mult': 1.1, 'trailing_distance': 0.009, 'trailing_activation': 0.018, 'break_even_trigger': 0.013, 'leverage': 3},
    'AVAX/USDT': {'min_score': 0.40, 'adx_threshold': 28, 'ker_threshold': 0.50, 'tp_mult': 1.9, 'sl_mult': 1.2, 'trailing_distance': 0.012, 'trailing_activation': 0.022, 'break_even_trigger': 0.015, 'leverage': 3},
    'DOGE/USDT': {'min_score': 0.42, 'adx_threshold': 30, 'ker_threshold': 0.52, 'tp_mult': 1.8, 'sl_mult': 1.3, 'trailing_distance': 0.014, 'trailing_activation': 0.025, 'break_even_trigger': 0.018, 'leverage': 2},
}

# ============================================================
# RÉGIMEN Y FILTROS
# ============================================================
REGIME_FILTER = ['Tendencia Fuerte', 'Expansión', 'Tendencia']
REGIME_SCORES = {
    'Expansión': 1.0,
    'Tendencia Fuerte': 0.9,
    'Tendencia': 0.7,
    'Normal': 0.5,
    'Chop': 0.2,
}

# ============================================================
# HORARIOS ÓPTIMOS
# ============================================================
OPTIMAL_HOURS = {'best': [(5, 9)], 'good': [(1, 5), (9, 13)], 'caution': [(13, 17)], 'avoid': [(17, 21), (21, 1)]}
OPTIMAL_DAYS = ['Tuesday', 'Wednesday']

# ============================================================
# KILL SWITCH
# ============================================================
KILL_SWITCH = {
    'max_consecutive_losses': 3,
    'max_daily_drawdown_pct': 0.05,
    'max_weekly_drawdown_pct': 0.10,
    'volatility_extreme_atr': 0.08,
    'regime_chop_wait': 3,
    'recovery_wait_hours': 1,
    'recovery_reduce_position': 0.5,
    'recovery_high_score_threshold': 0.50,
    'recovery_top_assets': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
}

# ============================================================
# SCORING WEIGHTS
# ============================================================
SCORING_WEIGHTS = {
    'regime': 0.20,
    'trend_quality': 0.20,
    'volatility': 0.15,
    'historical_winrate': 0.15,
    'historical_profit_factor': 0.10,
    'expectancy': 0.08,
    'risk': 0.07,
    'statistical_quality': 0.05,
}

# ============================================================
# ZONAS DE ENTRADA
# ============================================================
ENTRY_ZONES = {
    'A': {'pct': 0.002, 'desc': 'Muy cercana', 'aggressiveness': 0.3, 'color': '#4CAF50'},
    'B': {'pct': 0.010, 'desc': 'Moderada', 'aggressiveness': 0.6, 'color': '#FF9800'},
    'C': {'pct': 0.025, 'desc': 'Agresiva', 'aggressiveness': 0.9, 'color': '#F44336'},
}

# ============================================================
# WISE
# ============================================================
WISE_SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP', 'CHF', 'AUD', 'CAD', 'NZD', 'SGD', 'JPY', 'BRL', 'MXN', 'COP', 'ARS', 'CLP', 'PEN', 'TRY', 'INR', 'CNY']

# ============================================================
# DIRECTORIOS
# ============================================================
CACHE_DIR = 'data/cache'
OHLCV_DIR = 'data/ohlcv'
RESULTS_DIR = 'data/results'
