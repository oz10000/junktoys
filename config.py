# config.py
import pytz
import numpy as np
from datetime import timedelta

# ============================================================
# VERSIÓN
# ============================================================
VERSION = "6.1.0"
PROJECT_NAME = "Junk Toys v6.1 — Laboratorio de Ejecución Manual Óptima"

# ============================================================
# DATOS Y TIMEFRAMES
# ============================================================
TIMEFRAME = '5m'
TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
PRIMARY_TF = '5m'
LOOKBACK_DAYS = 365  # <--- ESTA VARIABLE FALTABA
INITIAL_CAPITAL = 10000.0
COMMISSION = 0.0004
SLIPPAGE = 0.0005

TIMEZONE = pytz.timezone('America/Argentina/Buenos_Aires')

# ============================================================
# EXCHANGES
# ============================================================
EXCHANGE_PRIORITY = ['okx', 'kucoin', 'mexc', 'kraken', 'binance', 'bybit']  # <--- ESTA FALTABA

EXCHANGE_CONFIGS = {  # <--- ESTA FALTABA
    'okx': {'type': 'swap', 'symbol_format': '{base}-{quote}-SWAP'},
    'kucoin': {'type': 'linear', 'symbol_format': '{base}{quote}M'},
    'mexc': {'type': 'swap', 'symbol_format': '{base}_{quote}'},
    'kraken': {'type': 'spot', 'symbol_format': '{base}/{quote}'},
    'binance': {'type': 'spot', 'symbol_format': '{base}/{quote}'},
    'bybit': {'type': 'linear', 'symbol_format': '{base}/{quote}'},
}

FALLBACK_SYMBOLS = [  # <--- ESTA FALTABA
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT', 'MATIC/USDT',
    'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'BCH/USDT', 'NEAR/USDT',
    'ALGO/USDT', 'VET/USDT', 'ICP/USDT', 'FTM/USDT', 'ARB/USDT',
    'XAU/USD'  # <--- ORO añadido
]

# ============================================================
# DIRECTORIOS DE CACHÉ
# ============================================================
CACHE_DIR = 'data/cache'      # <--- ESTA FALTABA
OHLCV_DIR = 'data/ohlcv'      # <--- ESTA FALTABA
RESULTS_DIR = 'data/results'
WISE_DATA_DIR = 'data/wise'

# ============================================================
# FILTRO HORARIO (Argentina)
# ============================================================
HOUR_FILTER_START = 10
HOUR_FILTER_END = 17
USE_HOUR_FILTER = True

# ============================================================
# PARÁMETROS POR DEFECTO
# ============================================================
DEFAULT_PARAMS = {
    'min_score': 0.30,
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
# PESOS DEL SCORING
# ============================================================
SCORING_WEIGHTS = {
    'regime': 0.15,
    'trend_quality': 0.15,
    'volatility': 0.10,
    'historical_winrate': 0.10,
    'historical_profit_factor': 0.08,
    'expectancy': 0.08,
    'risk': 0.08,
    'statistical_quality': 0.06,
    'microstructure': 0.06,
    'support_resistance': 0.06,
    'liquidity': 0.04,
    'correlation': 0.04,
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
# RÉGIMENES
# ============================================================
REGIME_SCORES = {
    'Expansión': 1.0,
    'Tendencia Fuerte': 0.9,
    'Tendencia': 0.7,
    'Normal': 0.5,
    'Chop': 0.2,
}

# ============================================================
# OPTIMIZACIÓN
# ============================================================
OPTIMIZATION_ITERATIONS = 100
WALK_FORWARD_SPLITS = 5
MONTE_CARLO_SIMULATIONS = 1000
BAYESIAN_INITIAL_POINTS = 20
BAYESIAN_N_CALLS = 50

# ============================================================
# RIESGO
# ============================================================
MAX_LEVERAGE_GLOBAL = 10
RISK_PER_TRADE = 0.02
MAX_POSITIONS = 3
MAX_DAILY_LOSS_PCT = 0.08
MIN_RISK_REWARD_RATIO = 1.5

# ============================================================
# SOPORTES Y RESISTENCIAS
# ============================================================
SR_WINDOW = 20
SR_VOLUME_THRESHOLD = 1.5
SR_CLUSTER_TOLERANCE = 0.005
SR_MAX_LEVELS = 10

# ============================================================
# AMPLITUD
# ============================================================
AMPLITUDE_LOOKBACK = 100
AMPLITUDE_BUCKETS = 10

# ============================================================
# EDGE
# ============================================================
EDGE_THRESHOLDS = {
    'maximo': 0.70,
    'medio': 0.50,
    'minimo': 0.30,
}

# ============================================================
# PROBABILIDAD
# ============================================================
MIN_PROBABILITY = 0.55
MIN_CONFIDENCE = 0.60

# ============================================================
# WISE
# ============================================================
WISE_SUPPORTED_CURRENCIES = [
    'USD', 'EUR', 'GBP', 'CHF', 'AUD', 'CAD', 'NZD', 'SGD', 'JPY',
    'BRL', 'MXN', 'COP', 'ARS', 'CLP', 'PEN', 'TRY', 'INR', 'CNY'
]

# ============================================================
# KILL SWITCH (para detener ejecución si es necesario)
# ============================================================
KILL_SWITCH = False

# ============================================================
# ACTIVOS ESPECIALES (XAU, etc.)
# ============================================================
SPECIAL_ASSETS = {
    'XAU/USD': {
        'exchange': 'coingecko',
        'symbol': 'gold',
        'vs_currency': 'usd',
    },
    'XAU/USDT': {
        'exchange': 'cryptocom',
        'symbol': 'XAU_USDT',
    }
}
