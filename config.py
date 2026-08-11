# config.py
import os

# ============================================================
# PROYECTO
# ============================================================
PROJECT_NAME = "🧸 Junk Toys"
VERSION = "6.2.1"

# ============================================================
# ZONA HORARIA Y FILTROS
# ============================================================
TIMEZONE = 'America/Argentina/Buenos_Aires'
HOUR_FILTER_START = 9
HOUR_FILTER_END = 18

# ============================================================
# CONSTANTES PRINCIPALES
# ============================================================
TIMEFRAME = '5m'
INITIAL_CAPITAL = 10000.0
MAX_HOLD = 120
RISK_PER_TRADE = 0.02
LEVERAGE = 5

# ============================================================
# DIRECTORIOS
# ============================================================
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ROOT_DIR, 'cache')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')

# ============================================================
# ACTIVOS
# ============================================================
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 'AVAX/USDT', 'MATIC/USDT',
    'VET/USDT', 'UNI/USDT', 'ATOM/USDT', 'FIL/USDT', 'ICP/USDT',
    'NEAR/USDT', 'APT/USDT'
]

FALLBACK_SYMBOLS = SYMBOLS + [
    'ARB/USDT', 'OP/USDT', 'INJ/USDT', 'SEI/USDT', 'SUI/USDT',
    'APE/USDT', 'FTM/USDT', 'ALGO/USDT', 'ETC/USDT', 'LTC/USDT',
    'DOGE/USDT', 'BCH/USDT'
]

# ============================================================
# EXCHANGES
# ============================================================
EXCHANGE_PRIORITY = ['binance', 'okx', 'kucoin', 'mexc', 'kraken', 'bybit']
EXCHANGES = {
    'binance': {'type': 'spot', 'priority': 1},
    'okx': {'type': 'spot', 'priority': 2},
    'kucoin': {'type': 'spot', 'priority': 3},
    'mexc': {'type': 'spot', 'priority': 4},
    'kraken': {'type': 'spot', 'priority': 5},
    'bybit': {'type': 'spot', 'priority': 6},
}

# ============================================================
# PARÁMETROS DE ESTRATEGIA
# ============================================================
MIN_SCORE = 0.35
ADX_THRESHOLD = 22
KER_THRESHOLD = 0.42
SL_MULT = 1.0
TP_MULT = 2.5
TP_TREND_BONUS = 1.1
TRAILING_ACTIVATION = 0.012
TRAILING_DISTANCE = 0.008
BE_TRIGGER = 0.008
BE_BUFFER = 0.002

# ============================================================
# PARÁMETROS POR DEFECTO (para Signal)
# ============================================================
DEFAULT_PARAMS = {
    'min_score': MIN_SCORE,
    'adx_threshold': ADX_THRESHOLD,
    'ker_threshold': KER_THRESHOLD,
    'sl_mult': SL_MULT,
    'tp_mult': TP_MULT,
    'tp_trend_bonus': TP_TREND_BONUS,
    'trailing_activation': TRAILING_ACTIVATION,
    'trailing_distance': TRAILING_DISTANCE,
    'be_trigger': BE_TRIGGER,
    'be_buffer': BE_BUFFER,
    'max_hold': MAX_HOLD,
    'risk_per_trade': RISK_PER_TRADE,
    'leverage': LEVERAGE,
    'timeframe': TIMEFRAME,
}

# ============================================================
# ZONAS DE ENTRADA
# ============================================================
ENTRY_ZONES = {
    'A': {'color': '#4CAF50', 'desc': 'Zona de entrada fuerte'},
    'B': {'color': '#FF9800', 'desc': 'Zona de entrada media'},
    'C': {'color': '#F44336', 'desc': 'Zona de entrada débil'},
}

# ============================================================
# KILL SWITCH
# ============================================================
KILL_SWITCH = False

# ============================================================
# AMPLITUD (para amplitude_analyzer.py)
# ============================================================
AMPLITUDE_LOOKBACK = 20
AMPLITUDE_BUCKETS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# ============================================================
# PARÁMETROS DEEPSYNC (opcionales)
# ============================================================
USE_ADAPTIVE_TP = False
USE_ADAPTIVE_TRAILING = False
USE_DYNAMIC_LEVERAGE = False

ASSET_TP_MULT = {
    'BTC/USDT': 2.8, 'ETH/USDT': 3.0, 'SOL/USDT': 3.2,
    'XRP/USDT': 2.6, 'ADA/USDT': 3.1, 'DOT/USDT': 3.1,
    'LINK/USDT': 3.0, 'AVAX/USDT': 3.4, 'MATIC/USDT': 3.1,
    'VET/USDT': 3.2, 'UNI/USDT': 2.9, 'ATOM/USDT': 3.0,
    'FIL/USDT': 3.3, 'ICP/USDT': 3.5, 'NEAR/USDT': 3.4,
    'APT/USDT': 3.6, 'ARB/USDT': 3.2, 'OP/USDT': 3.3,
    'INJ/USDT': 3.5, 'SEI/USDT': 3.4, 'SUI/USDT': 3.5,
    'APE/USDT': 3.3, 'FTM/USDT': 3.2, 'ALGO/USDT': 3.0,
    'ETC/USDT': 3.1, 'LTC/USDT': 2.8, 'DOGE/USDT': 3.0,
    'BCH/USDT': 3.0,
}
DEFAULT_TP_MULT = 3.0

ASSET_TRAILING_DIST = {
    'BTC/USDT': 1.2, 'ETH/USDT': 1.4, 'SOL/USDT': 1.6,
    'XRP/USDT': 1.1, 'ADA/USDT': 1.5, 'DOT/USDT': 1.5,
    'LINK/USDT': 1.4, 'AVAX/USDT': 1.7, 'MATIC/USDT': 1.5,
    'VET/USDT': 1.6, 'UNI/USDT': 1.3, 'ATOM/USDT': 1.5,
    'FIL/USDT': 1.7, 'ICP/USDT': 1.8, 'NEAR/USDT': 1.7,
    'APT/USDT': 1.8, 'ARB/USDT': 1.6, 'OP/USDT': 1.7,
    'INJ/USDT': 1.8, 'SEI/USDT': 1.7, 'SUI/USDT': 1.8,
    'APE/USDT': 1.7, 'FTM/USDT': 1.6, 'ALGO/USDT': 1.5,
    'ETC/USDT': 1.5, 'LTC/USDT': 1.3, 'DOGE/USDT': 1.5,
    'BCH/USDT': 1.5,
}
DEFAULT_TRAILING_DIST = 1.5

ASSET_TRAILING_ACT = {
    'BTC/USDT': 1.8, 'ETH/USDT': 2.0, 'SOL/USDT': 2.4,
    'XRP/USDT': 1.6, 'ADA/USDT': 2.2, 'DOT/USDT': 2.3,
    'LINK/USDT': 2.1, 'AVAX/USDT': 2.6, 'MATIC/USDT': 2.2,
    'VET/USDT': 2.4, 'UNI/USDT': 2.0, 'ATOM/USDT': 2.2,
    'FIL/USDT': 2.5, 'ICP/USDT': 2.7, 'NEAR/USDT': 2.6,
    'APT/USDT': 2.8, 'ARB/USDT': 2.4, 'OP/USDT': 2.5,
    'INJ/USDT': 2.7, 'SEI/USDT': 2.6, 'SUI/USDT': 2.7,
    'APE/USDT': 2.5, 'FTM/USDT': 2.4, 'ALGO/USDT': 2.2,
    'ETC/USDT': 2.2, 'LTC/USDT': 1.9, 'DOGE/USDT': 2.2,
    'BCH/USDT': 2.2,
}
DEFAULT_TRAILING_ACT = 2.2

REGIME_TRAILING_FACTOR = {
    'Tendencia Fuerte': 0.9, 'Expansión': 0.95,
    'Tendencia': 1.0, 'Normal': 1.0, 'Chop': 1.6,
}
REGIME_TP_FACTOR = {
    'Tendencia Fuerte': 0.9, 'Expansión': 0.9,
    'Tendencia': 1.0, 'Normal': 1.0, 'Chop': 1.15,
}

ADX_TRAILING_FACTOR = {
    (0, 20): 1.15, (20, 30): 1.0, (30, 40): 0.92, (40, 100): 0.85,
}
VOLATILITY_TRAILING_FACTOR = {'low': 0.9, 'medium': 1.0, 'high': 1.15}

LEVERAGE_PROFILE = {'conservative': 0.5, 'moderate': 0.7, 'aggressive': 1.0}
DEFAULT_LEVERAGE_PROFILE = 'moderate'
LEVERAGE_SAFETY_MULT = 3.0

ASSET_DECIMALS = {
    'BTC/USDT': 2, 'ETH/USDT': 2, 'BNB/USDT': 2, 'SOL/USDT': 2,
    'XRP/USDT': 4, 'ADA/USDT': 4, 'DOT/USDT': 4, 'LINK/USDT': 4,
    'AVAX/USDT': 2, 'MATIC/USDT': 4, 'VET/USDT': 6, 'UNI/USDT': 4,
    'ATOM/USDT': 4, 'FIL/USDT': 4, 'ICP/USDT': 4, 'NEAR/USDT': 4,
    'APT/USDT': 4, 'ARB/USDT': 4, 'OP/USDT': 4, 'INJ/USDT': 4,
    'SEI/USDT': 4, 'SUI/USDT': 4, 'APE/USDT': 4, 'FTM/USDT': 4,
    'ALGO/USDT': 4, 'ETC/USDT': 4, 'LTC/USDT': 2, 'DOGE/USDT': 4,
    'BCH/USDT': 2,
}
DEFAULT_DECIMALS = 4

# ============================================================
# CLASE CONFIG (para imports con from config import CONFIG)
# ============================================================
class CONFIG:
    PROJECT_NAME = PROJECT_NAME
    VERSION = VERSION
    TIMEZONE = TIMEZONE
    HOUR_FILTER_START = HOUR_FILTER_START
    HOUR_FILTER_END = HOUR_FILTER_END
    TIMEFRAME = TIMEFRAME
    INITIAL_CAPITAL = INITIAL_CAPITAL
    MAX_HOLD = MAX_HOLD
    RISK_PER_TRADE = RISK_PER_TRADE
    LEVERAGE = LEVERAGE
    CACHE_DIR = CACHE_DIR
    DATA_DIR = DATA_DIR
    LOGS_DIR = LOGS_DIR
    SYMBOLS = SYMBOLS
    FALLBACK_SYMBOLS = FALLBACK_SYMBOLS
    EXCHANGE_PRIORITY = EXCHANGE_PRIORITY
    EXCHANGES = EXCHANGES
    MIN_SCORE = MIN_SCORE
    ADX_THRESHOLD = ADX_THRESHOLD
    KER_THRESHOLD = KER_THRESHOLD
    SL_MULT = SL_MULT
    TP_MULT = TP_MULT
    TP_TREND_BONUS = TP_TREND_BONUS
    TRAILING_ACTIVATION = TRAILING_ACTIVATION
    TRAILING_DISTANCE = TRAILING_DISTANCE
    BE_TRIGGER = BE_TRIGGER
    BE_BUFFER = BE_BUFFER
    DEFAULT_PARAMS = DEFAULT_PARAMS
    ENTRY_ZONES = ENTRY_ZONES
    KILL_SWITCH = KILL_SWITCH
    AMPLITUDE_LOOKBACK = AMPLITUDE_LOOKBACK
    AMPLITUDE_BUCKETS = AMPLITUDE_BUCKETS
    USE_ADAPTIVE_TP = USE_ADAPTIVE_TP
    USE_ADAPTIVE_TRAILING = USE_ADAPTIVE_TRAILING
    USE_DYNAMIC_LEVERAGE = USE_DYNAMIC_LEVERAGE
    ASSET_TP_MULT = ASSET_TP_MULT
    DEFAULT_TP_MULT = DEFAULT_TP_MULT
    ASSET_TRAILING_DIST = ASSET_TRAILING_DIST
    DEFAULT_TRAILING_DIST = DEFAULT_TRAILING_DIST
    ASSET_TRAILING_ACT = ASSET_TRAILING_ACT
    DEFAULT_TRAILING_ACT = DEFAULT_TRAILING_ACT
    REGIME_TRAILING_FACTOR = REGIME_TRAILING_FACTOR
    REGIME_TP_FACTOR = REGIME_TP_FACTOR
    ADX_TRAILING_FACTOR = ADX_TRAILING_FACTOR
    VOLATILITY_TRAILING_FACTOR = VOLATILITY_TRAILING_FACTOR
    LEVERAGE_PROFILE = LEVERAGE_PROFILE
    DEFAULT_LEVERAGE_PROFILE = DEFAULT_LEVERAGE_PROFILE
    LEVERAGE_SAFETY_MULT = LEVERAGE_SAFETY_MULT
    ASSET_DECIMALS = ASSET_DECIMALS
    DEFAULT_DECIMALS = DEFAULT_DECIMALS
