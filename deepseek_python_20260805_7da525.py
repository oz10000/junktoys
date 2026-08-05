# firm_signals_omega/signal_generator.py
"""
Generador de Señales — Firm Signals Ω

Genera señales candidatas a partir de datos de mercado.
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from .config import QUALITY_THRESHOLDS, TIMEFRAMES

logger = logging.getLogger(__name__)

class SignalGenerator:
    """
    Generador de señales candidatas para certificación
    """
    
    def __init__(self, data_engine):
        self.data_engine = data_engine
        self.candidates = []
    
    def generate_candidates(self, symbols: List[str]) -> List[Dict]:
        """
        Genera señales candidatas para todos los símbolos
        """
        candidates = []
        
        for symbol in symbols:
            try:
                candidate = self._analyze_symbol(symbol)
                if candidate:
                    candidates.append(candidate)
            except Exception as e:
                logger.warning(f"Error analizando {symbol}: {e}")
        
        # Ordenar por score
        candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
        self.candidates = candidates
        return candidates
    
    def _analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Analiza un símbolo y genera una señal candidata
        """
        # Obtener datos multi-timeframe
        data = self.data_engine.fetch_ohlcv_multiframe(symbol)
        if not data:
            return None
        
        # Obtener datos del timeframe principal
        df = data.get('5m')
        if df is None or df.empty:
            return None
        
        # Calcular indicadores
        score = self._calculate_score(df)
        adx = self._calculate_adx(df)
        adx_slope = self._calculate_adx_slope(df)
        ker = self._calculate_ker(df)
        regime = self._classify_regime(df)
        volume_ratio = self._calculate_volume_ratio(df)
        volume_accel = self._calculate_volume_accel(df)
        cvd = self._calculate_cvd(df)
        
        # Verificar umbrales mínimos
        thresholds = QUALITY_THRESHOLDS.get(symbol, QUALITY_THRESHOLDS.get('BTC/USDT', {}))
        
        # Si no cumple umbrales, descartar
        if abs(score) < thresholds.get('min_score', 0.65) * 0.7:
            return None
        
        # Determinar dirección
        direction = 'LONG' if score > 0 else 'SHORT'
        
        # Calcular price levels
        entry_price = df['close'].iloc[-1]
        atr = self._calculate_atr(df)
        sl_price = entry_price * (1 - 0.005) if direction == 'LONG' else entry_price * (1 + 0.005)
        tp_price = entry_price * (1 + 0.008) if direction == 'LONG' else entry_price * (1 - 0.008)
        
        # Timeframes alineados
        timeframes_aligned = self._check_timeframe_alignment(data, direction)
        
        return {
            'symbol': symbol,
            'direction': direction,
            'score': abs(score),
            'adx': adx,
            'adx_slope': adx_slope,
            'ker': ker,
            'regime': regime,
            'volume_ratio': volume_ratio,
            'volume_accel': volume_accel,
            'cvd': cvd,
            'entry_price': entry_price,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'atr': atr,
            'timeframes_aligned': timeframes_aligned,
            'timestamp': pd.Timestamp.now().isoformat(),
        }
    
    def _calculate_score(self, df: pd.DataFrame) -> float:
        """Calcula PiDelta Score"""
        close = df['close']
        atr = self._calculate_atr(df)
        ema22 = close.ewm(span=22).mean()
        
        if atr == 0:
            return 0
        
        trend = np.tanh((close.iloc[-1] - ema22.iloc[-1]) / atr)
        return float(trend)
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula ADX"""
        high = df['high']; low = df['low']; close = df['close']
        
        plus_dm = high.diff()
        minus_dm = low.diff().abs()
        plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
        minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)
        
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(period).mean()
        
        return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 0
    
    def _calculate_adx_slope(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula pendiente del ADX"""
        adx = self._calculate_adx(df, period)
        return adx - self._calculate_adx(df.iloc[-5:], period) if adx else 0
    
    def _calculate_ker(self, df: pd.DataFrame, period: int = 10) -> float:
        """Calcula KER"""
        close = df['close']
        change = abs(close.diff(period))
        volatility = close.diff().abs().rolling(period).sum()
        ker = change / (volatility + 1e-9)
        return float(ker.iloc[-1]) if not pd.isna(ker.iloc[-1]) else 0
    
    def _classify_regime(self, df: pd.DataFrame) -> str:
        """Clasifica régimen de mercado"""
        adx = self._calculate_adx(df)
        if adx > 35:
            return 'Tendencia Fuerte'
        elif adx > 25:
            return 'Tendencia Débil'
        elif adx < 20:
            return 'Rango'
        else:
            return 'Normal'
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula ATR"""
        high, low, close = df['high'], df['low'], df['close']
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0
    
    def _calculate_volume_ratio(self, df: pd.DataFrame) -> float:
        """Calcula ratio de volumen actual vs MA20"""
        vol = df['volume']
        ma20 = vol.rolling(20).mean()
        return float(vol.iloc[-1] / ma20.iloc[-1]) if ma20.iloc[-1] > 0 else 1
    
    def _calculate_volume_accel(self, df: pd.DataFrame) -> float:
        """Calcula aceleración de volumen"""
        vol = df['volume']
        ma5 = vol.rolling(5).mean()
        accel = ma5.diff().diff().iloc[-1]
        return float(accel) if not pd.isna(accel) else 0
    
    def _calculate_cvd(self, df: pd.DataFrame) -> float:
        """Calcula Cumulative Volume Delta"""
        delta = df['volume'] * np.sign(df['close'] - df['open'])
        cvd = delta.cumsum()
        return float(cvd.iloc[-1]) if not pd.isna(cvd.iloc[-1]) else 0
    
    def _check_timeframe_alignment(self, data: Dict, direction: str) -> int:
        """Verifica alineación entre timeframes"""
        aligned = 0
        for tf, df in data.items():
            if tf == '5m':
                continue
            if len(df) < 20:
                continue
            score = self._calculate_score(df)
            if (direction == 'LONG' and score > 0) or (direction == 'SHORT' and score < 0):
                aligned += 1
        return aligned