# firm_signals_omega/data_engine.py
"""
Firm Data Engine — Motor de Datos para Firm Signals Ω

Gestiona la descarga, caché y validación de datos de múltiples fuentes.
"""

import os
import time
import pickle
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import CACHE_DIR, OHLCV_DIR, MACRO_DATA_DIR, TIMEFRAMES
from data_engine import DataEngine  # Reutiliza el motor existente

logger = logging.getLogger(__name__)

class FirmDataEngine:
    """
    Motor de datos optimizado para Firm Signals Ω
    Soporta caché, descarga incremental y múltiples fuentes
    """
    
    def __init__(self, data_engine=None):
        self.base_engine = data_engine or DataEngine()
        self.cache = {}
        self.cache_timestamps = {}
        self._ensure_directories()
        self.symbol_universe = None
        
    def _ensure_directories(self):
        """Crea directorios necesarios"""
        for d in [CACHE_DIR, OHLCV_DIR, MACRO_DATA_DIR]:
            os.makedirs(d, exist_ok=True)
    
    def get_symbols(self, max_symbols=100, force_refresh=False) -> List[str]:
        """Obtiene lista de símbolos del exchange"""
        if not force_refresh and self.symbol_universe is not None:
            return self.symbol_universe
        
        symbols = self.base_engine.get_common_pairs(max_pairs=max_symbols, force_refresh=force_refresh)
        # Filtrar solo los principales si son demasiados
        if len(symbols) > max_symbols:
            symbols = symbols[:max_symbols]
        
        self.symbol_universe = symbols
        logger.info(f"📊 Universo Firm Signals: {len(symbols)} símbolos")
        return symbols
    
    def fetch_ohlcv_multiframe(self, symbol: str, timeframes: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Obtiene OHLCV para múltiples timeframes con caché inteligente
        """
        if timeframes is None:
            timeframes = TIMEFRAMES
        
        result = {}
        for tf in timeframes:
            df = self._fetch_with_cache(symbol, tf, limit=500)
            if df is not None and not df.empty:
                result[tf] = df
        
        return result
    
    def _fetch_with_cache(self, symbol: str, timeframe: str, limit: int = 500, 
                          force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Obtiene datos con caché y descarga incremental
        """
        cache_key = hashlib.md5(f"firm_{symbol}_{timeframe}".encode()).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
        
        # Intentar cargar desde caché
        if not force_refresh and os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    df = pickle.load(f)
                if not df.empty:
                    # Verificar si hay datos nuevos
                    last_ts = df.index[-1]
                    if (datetime.now() - last_ts).total_seconds() > 3600:
                        # Actualizar incrementalmente
                        new_df = self._fetch_incremental(symbol, timeframe, last_ts)
                        if new_df is not None and not new_df.empty:
                            df = pd.concat([df, new_df]).drop_duplicates()
                            with open(cache_path, 'wb') as f:
                                pickle.dump(df, f)
                    return df
            except Exception as e:
                logger.warning(f"Error leyendo caché {symbol}: {e}")
        
        # Descarga completa
        df = self.base_engine.fetch_ohlcv(symbol, timeframe, limit=limit)
        if df is not None and not df.empty:
            with open(cache_path, 'wb') as f:
                pickle.dump(df, f)
            return df
        
        return None
    
    def _fetch_incremental(self, symbol: str, timeframe: str, since: datetime) -> Optional[pd.DataFrame]:
        """Descarga solo datos nuevos desde una fecha"""
        try:
            return self.base_engine.fetch_ohlcv(symbol, timeframe, 
                                               limit=500, 
                                               since=since)
        except Exception as e:
            logger.warning(f"Error en descarga incremental {symbol}: {e}")
            return None
    
    def fetch_macro_data(self, symbol: str, days: int = 90) -> Optional[pd.DataFrame]:
        """
        Obtiene datos macro (S&P 500, Nasdaq, DXY, VIX, Oro, etc.)
        """
        # Implementación simplificada - en producción usar Stooq o Yahoo Finance
        cache_key = f"macro_{symbol}_{days}"
        cache_path = os.path.join(MACRO_DATA_DIR, f"{cache_key}.pkl")
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        
        # Fallback: generar datos sintéticos para demostración
        # En producción, aquí se usaría una API real
        data = self._generate_macro_demo(symbol, days)
        
        if data is not None:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        
        return data
    
    def _generate_macro_demo(self, symbol: str, days: int) -> pd.DataFrame:
        """
        Genera datos macro de demostración (para desarrollo)
        En producción se reemplaza con API real
        """
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=days, freq='1D')
        
        base_price = {
            'SPX': 5600,
            'IXIC': 18500,
            'DXY': 104,
            'VIX': 15,
            'XAU': 2400,
            'US10Y': 4.2,
        }.get(symbol, 100)
        
        # Simular movimiento browniano
        returns = np.random.normal(0, 0.005, days)
        price = base_price * np.cumprod(1 + returns)
        
        return pd.DataFrame({
            'close': price,
            'open': price * (1 + np.random.normal(0, 0.001, days)),
            'high': price * (1 + np.abs(np.random.normal(0, 0.002, days))),
            'low': price * (1 - np.abs(np.random.normal(0, 0.002, days))),
            'volume': np.random.lognormal(10, 1, days)
        }, index=dates)
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Valida la integridad de los datos
        """
        if df is None or df.empty:
            return False, "DataFrame vacío"
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                return False, f"Columna faltante: {col}"
        
        if df.isnull().any().any():
            return False, "Existen valores NaN"
        
        if (df['high'] < df['low']).any():
            return False, "High < Low detectado"
        
        if (df['close'] <= 0).any():
            return False, "Precios negativos o cero"
        
        return True, "Datos válidos"
    
    def clear_cache(self, older_than_days: int = 7):
        """Limpia caché de datos antiguos"""
        now = time.time()
        for d in [CACHE_DIR, OHLCV_DIR, MACRO_DATA_DIR]:
            if os.path.exists(d):
                for f in os.listdir(d):
                    path = os.path.join(d, f)
                    if os.path.isfile(path):
                        mtime = os.path.getmtime(path)
                        if (now - mtime) > older_than_days * 86400:
                            try:
                                os.remove(path)
                            except:
                                pass
        logger.info("🧹 Caché limpiada")
