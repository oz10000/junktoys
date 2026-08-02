# data_engine.py
import ccxt
import pandas as pd
import numpy as np
import os
import time
import pickle
import hashlib
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import (
    EXCHANGES, EXCHANGE_PRIORITY, CACHE_DIR, OHLCV_DIR,
    TIMEFRAME, LOOKBACK_DAYS, UNIVERSE, UNIVERSE_BY_EXCHANGE
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataEngine:
    """Motor de datos con soporte para múltiples exchanges"""
    
    def __init__(self, exchanges=None):
        os.makedirs(OHLCV_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        self.exchanges = {}
        self.exchange_status = {}
        self.symbol_maps = {}
        
        if exchanges is None:
            exchanges = EXCHANGE_PRIORITY
        
        for ex_id in exchanges:
            if not EXCHANGES.get(ex_id, {}).get('enabled', True):
                continue
            self._connect_exchange(ex_id)
        
        self.primary = self._get_primary_exchange()
        self._cache = {}
        self._cache_timestamps = {}
        self._universe_cache = None
        self._universe_by_exchange = {}
        
        logger.info(f"✅ DataEngine inicializado. Primary: {self.primary}")
    
    def _connect_exchange(self, ex_id):
        """Conecta a un exchange con reintentos"""
        for attempt in range(3):
            try:
                ex_class = getattr(ccxt, ex_id)
                options = {'enableRateLimit': True}
                
                if ex_id == 'binance':
                    options['options'] = {'defaultType': 'spot'}
                elif ex_id == 'bybit':
                    options['options'] = {'defaultType': 'linear'}
                elif ex_id == 'okx':
                    options['options'] = {'defaultType': 'swap'}
                elif ex_id == 'bitget':
                    options['options'] = {'defaultType': 'swap'}
                else:
                    options['options'] = {'defaultType': 'spot'}
                
                exchange = ex_class(options)
                exchange.load_markets()
                self.exchanges[ex_id] = exchange
                self.exchange_status[ex_id] = 'connected'
                self.symbol_maps[ex_id] = {
                    m['symbol']: m for m in exchange.markets.values()
                }
                logger.info(f"✅ Conectado a {ex_id}")
                return
            except Exception as e:
                logger.warning(f"Intento {attempt+1}/3 para {ex_id} falló: {e}")
                time.sleep(2)
        
        self.exchanges[ex_id] = None
        self.exchange_status[ex_id] = 'failed'
        logger.error(f"❌ No se pudo conectar a {ex_id}")
    
    def _get_primary_exchange(self):
        """Obtiene el exchange primario disponible"""
        for ex_id in EXCHANGE_PRIORITY:
            if self.exchanges.get(ex_id) is not None:
                return ex_id
        return None
    
    def get_available_exchanges(self):
        """Retorna lista de exchanges conectados"""
        return [ex_id for ex_id, ex in self.exchanges.items() if ex is not None]
    
    def get_common_pairs(self, min_volume_usd=200000, max_pairs=500, force_refresh=False):
        """
        Obtiene la intersección de pares USDT entre todos los exchanges
        """
        if not force_refresh and self._universe_cache is not None:
            return self._universe_cache
        
        all_pairs = {}
        pair_exchanges = {}
        
        for ex_id, exchange in self.exchanges.items():
            if exchange is None:
                continue
            
            try:
                markets = exchange.load_markets()
                pairs = []
                for symbol, market in markets.items():
                    if symbol.endswith('/USDT'):
                        # Verificar que sea spot o derivado según el tipo
                        ex_type = EXCHANGES.get(ex_id, {}).get('type', 'spot')
                        if ex_type == 'spot' and not market.get('spot', False):
                            continue
                        if ex_type == 'linear' and not market.get('linear', False):
                            continue
                        if ex_type == 'swap' and not market.get('swap', False):
                            continue
                        pairs.append(symbol)
                
                # Filtrar por volumen si es posible
                if min_volume_usd > 0:
                    try:
                        tickers = exchange.fetch_tickers()
                        filtered = []
                        for sym in pairs:
                            ticker = tickers.get(sym)
                            if ticker:
                                vol = ticker.get('quoteVolume', 0) or ticker.get('turnover', 0)
                                if vol >= min_volume_usd:
                                    filtered.append(sym)
                        pairs = filtered
                    except:
                        pass
                
                all_pairs[ex_id] = set(pairs)
                for sym in pairs:
                    if sym not in pair_exchanges:
                        pair_exchanges[sym] = []
                    pair_exchanges[sym].append(ex_id)
                
                logger.info(f"📊 {ex_id}: {len(pairs)} pares USDT")
                
            except Exception as e:
                logger.warning(f"Error obteniendo pares de {ex_id}: {e}")
        
        # Intersección de todos los exchanges
        if all_pairs:
            common = set.intersection(*all_pairs.values()) if len(all_pairs) > 1 else set(list(all_pairs.values())[0])
            common = sorted(list(common))[:max_pairs]
        else:
            common = self._fallback_pairs()
        
        # Guardar por exchange
        self._universe_by_exchange = {ex_id: sorted(list(pairs & set(common))) 
                                      for ex_id, pairs in all_pairs.items()}
        self._universe_cache = common
        
        # Actualizar config
        global UNIVERSE, UNIVERSE_BY_EXCHANGE
        UNIVERSE = common
        UNIVERSE_BY_EXCHANGE = self._universe_by_exchange
        
        logger.info(f"✅ Universo consolidado: {len(common)} pares comunes")
        return common
    
    def _fallback_pairs(self):
        """Lista de respaldo"""
        return [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
            'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
            'MATIC/USDT', 'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'BCH/USDT',
            'NEAR/USDT', 'ALGO/USDT', 'VET/USDT', 'ICP/USDT', 'FTM/USDT',
        ]
    
    def get_exchange_for_symbol(self, symbol):
        """Retorna el mejor exchange para un símbolo"""
        for ex_id in EXCHANGE_PRIORITY:
            if ex_id in self._universe_by_exchange:
                if symbol in self._universe_by_exchange.get(ex_id, []):
                    return ex_id
        return self.primary
    
    def fetch_ohlcv(self, symbol, timeframe=TIMEFRAME, limit=300, exchange_id=None, force_refresh=False):
        """Descarga OHLCV con caché y soporte multi-exchange"""
        ex_id = exchange_id or self.get_exchange_for_symbol(symbol)
        exchange = self.exchanges.get(ex_id)
        
        if exchange is None:
            # Intentar con otro exchange
            for alt_id in EXCHANGE_PRIORITY:
                if alt_id != ex_id and self.exchanges.get(alt_id) is not None:
                    exchange = self.exchanges[alt_id]
                    ex_id = alt_id
                    break
            if exchange is None:
                logger.error(f"No hay exchange disponible para {symbol}")
                return None
        
        cache_key = hashlib.md5(f"{symbol}_{timeframe}_{limit}_{ex_id}".encode()).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
        
        if not force_refresh and os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    df = pickle.load(f)
                if not df.empty:
                    return df
            except:
                pass
        
        try:
            # Normalizar símbolo para el exchange
            markets = exchange.load_markets()
            if symbol not in markets:
                # Intentar encontrar el símbolo correcto
                for sym, market in markets.items():
                    if sym == symbol or market.get('id') == symbol:
                        symbol = sym
                        break
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(df, f)
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo OHLCV de {symbol} en {ex_id}: {e}")
            return None
    
    def fetch_historical(self, symbol, timeframe=TIMEFRAME, days=LOOKBACK_DAYS, exchange_id=None):
        """Descarga histórico completo con paginación"""
        ex_id = exchange_id or self.get_exchange_for_symbol(symbol)
        exchange = self.exchanges.get(ex_id)
        
        if exchange is None:
            return None
        
        # Calcular límite
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
            candles_per_day = 1440 // minutes
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            candles_per_day = 24 // hours
        else:
            candles_per_day = 288
        
        limit = days * candles_per_day + 100
        
        try:
            since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            if not ohlcv:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            cutoff = datetime.now() - timedelta(days=days)
            df = df[df.index >= cutoff]
            
            return df
            
        except Exception as e:
            logger.error(f"Error en histórico de {symbol}: {e}")
            return None
    
    def fetch_multi_timeframe(self, symbol, timeframes=None):
        """Obtiene velas para múltiples temporalidades"""
        if timeframes is None:
            timeframes = ['5m', '15m', '30m', '1h']
        
        result = {}
        for tf in timeframes:
            df = self.fetch_ohlcv(symbol, timeframe=tf, limit=300)
            if df is not None and not df.empty:
                result[tf] = df
        return result
    
    def fetch_ticker(self, symbol, exchange_id=None):
        """Obtiene ticker actual de un símbolo"""
        ex_id = exchange_id or self.get_exchange_for_symbol(symbol)
        exchange = self.exchanges.get(ex_id)
        if exchange is None:
            return None
        try:
            return exchange.fetch_ticker(symbol)
        except:
            return None
    
    def fetch_balance(self, exchange_id=None):
        """Obtiene balance de un exchange"""
        ex_id = exchange_id or self.primary
        exchange = self.exchanges.get(ex_id)
        if exchange is None:
            return None
        try:
            return exchange.fetch_balance()
        except:
            return None
    
    def get_bybit_funding_rate(self, symbol):
        """Obtiene tasa de funding de Bybit"""
        bybit = self.exchanges.get('bybit')
        if bybit is None:
            return 0.0
        try:
            funding = bybit.fetch_funding_rate(symbol)
            return funding.get('fundingRate', 0.0)
        except:
            return 0.0
    
    def clear_cache(self):
        """Limpia la caché"""
        self._cache.clear()
        self._cache_timestamps.clear()
        for f in os.listdir(CACHE_DIR):
            try:
                os.remove(os.path.join(CACHE_DIR, f))
            except:
                pass
        logger.info("🧹 Caché limpiada")
