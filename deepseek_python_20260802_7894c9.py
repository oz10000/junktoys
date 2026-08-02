# core_engine.py
import pandas as pd
import numpy as np

def compute_adx(df, period=14):
    if df.empty:
        return pd.Series(dtype=float)
    high, low, close = df['high'], df['low'], df['close']
    plus_dm = high.diff()
    minus_dm = low.diff().abs() * -1
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = minus_dm.abs()
    tr = pd.DataFrame({
        'hl': high - low,
        'hc': (high - close.shift()).abs(),
        'lc': (low - close.shift()).abs()
    }).max(axis=1)
    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    return dx.rolling(period).mean()

def compute_ker(df, period=10):
    if df.empty:
        return pd.Series(dtype=float)
    close = df['close']
    change = abs(close.diff(period))
    volatility = close.diff().abs().rolling(period).sum()
    return (change / volatility).fillna(0)

def compute_atr(df, period=14):
    if df.empty:
        return pd.Series(dtype=float)
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.DataFrame({
        'hl': high - low,
        'hc': (high - close.shift()).abs(),
        'lc': (low - close.shift()).abs()
    }).max(axis=1)
    return tr.rolling(period).mean()

def compute_regime(df, atr_period=14):
    if df.empty:
        return 'Chop'
    adx_series = compute_adx(df)
    atr_series = compute_atr(df, atr_period)
    if adx_series.empty or atr_series.empty:
        return 'Chop'
    adx = adx_series.iloc[-1]
    atr_pct = atr_series.iloc[-1] / df['close'].iloc[-1]
    if adx > 40 and atr_pct > 0.02:
        return 'Expansión'
    elif adx > 30:
        return 'Tendencia Fuerte'
    elif adx > 20:
        return 'Tendencia'
    else:
        return 'Chop'

def compute_pidelta_score(df, ema_period=22, atr_period=14):
    if df.empty or len(df) < 30:
        return 0.0
    close = df['close']
    ema = close.ewm(span=ema_period, adjust=False).mean()
    atr = compute_atr(df, atr_period)
    adx = compute_adx(df)
    ker = compute_ker(df, 10)
    if atr.empty or adx.empty or ker.empty:
        return 0.0
    trend = np.tanh((close.iloc[-1] - ema.iloc[-1]) / atr.iloc[-1])
    strength = min(1.0, adx.iloc[-1] / 40)
    ker_val = ker.iloc[-1]
    atr_rel = min(1.0, (atr.iloc[-1] / close.iloc[-1]) / 0.035)
    mom = close.pct_change(5).iloc[-1] if len(close) >= 5 else 0.0
    mom_norm = np.tanh(mom * 5)
    raw = 0.25 * trend + 0.20 * strength + 0.15 * ker_val + 0.10 * atr_rel + 0.10 * mom_norm
    return float(np.tanh(raw))