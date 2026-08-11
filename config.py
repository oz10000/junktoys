# ============================================================
# CONFIGURACIÓN — JUNK TOYS v6.2.1
# ============================================================

# --- Parámetros de la estrategia (valores originales) ---
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
MAX_HOLD = 120
RISK_PER_TRADE = 0.02

# ===== LEVERAGE (añadido para resolver error de importación) =====
LEVERAGE = 5   # <-- ESTA LÍNEA ES LA CLAVE

# --- Universo de activos (original) ---
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 'AVAX/USDT', 'MATIC/USDT',
    'VET/USDT', 'UNI/USDT', 'ATOM/USDT', 'FIL/USDT', 'ICP/USDT',
    'NEAR/USDT', 'APT/USDT'
]

FALLBACK_SYMBOLS = SYMBOLS + ['ARB/USDT', 'OP/USDT', 'INJ/USDT', 'SEI/USDT', 'SUI/USDT', 'APE/USDT', 'FTM/USDT', 'ALGO/USDT', 'ETC/USDT', 'LTC/USDT', 'DOGE/USDT', 'BCH/USDT']

# ============================================================
# PARÁMETROS AJUSTADOS NUEVOS (DeepSync)
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
