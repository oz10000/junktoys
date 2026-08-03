# data_engine.py
import ccxt
import pandas as pd
import os
import time
import pickle
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config import (
    EXCHANGE_PRIORITY, EXCHANGE_CONFIGS,
    CACHE_DIR, OHLCV_DIR, TIMEFRAME, LOOKBACK_DAYS
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataEngine:
    def __init__(self):
        os.makedirs(OHLCV_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)

        self.exchanges = {}
        self.exchange_status = {}

        for ex_id in EXCHANGE_PRIORITY:
            config = EXCHANGE_CONFIGS.get(ex_id)
            if not config:
                continue
            self._connect_exchange(ex_id, config)

        self.primary = self._get_primary_exchange()
        self._cache = {}
        self._cache_timestamps = {}
        self._universe_cache = None
        self._universe_by_exchange = {}

        if not self.primary:
            logger.error("❌ No se pudo conectar a ningún exchange.")
        else:
            logger.info(f"✅ DataEngine listo. Primary: {self.primary}")

    def _connect_exchange(self, ex_id: str, config: dict):
        for attempt in range(3):
            try:
                ex_class = getattr(ccxt, config['class'])
                exchange = ex_class({
                    'enableRateLimit': True,
                    'options': config['options']
                })
                exchange.load_markets()
                self.exchanges[ex_id] = exchange
                self.exchange_status[ex_id] = 'connected'
                logger.info(f"✅ Conectado a {ex_id}")
                return
            except Exception as e:
                logger.warning(f"Intento {attempt+1}/3 para {ex_id} falló: {e}")
                time.sleep(2)
        self.exchange_status[ex_id] = 'failed'
        logger.error(f"❌ No se pudo conectar a {ex_id}")

    def _get_primary_exchange(self) -> Optional[str]:
        for ex_id in EXCHANGE_PRIORITY:
            if self.exchanges.get(ex_id) is not None:
                return ex_id
        return None

    def get_available_exchanges(self) -> List[str]:
        return [ex_id for ex_id, ex in self.exchanges.items() if ex is not None]

    def get_common_pairs(self, min_volume_usd=200000, max_pairs=500, force_refresh=False) -> List[str]:
        if not force_refresh and self._universe_cache is not None:
            return self._universe_cache

        all_pairs = {}
        for ex_id, exchange in self.exchanges.items():
            if exchange is None:
                continue
            try:
                logger.info(f"📊 Obteniendo pares de {ex_id}...")
                markets = exchange.load_markets()
                pairs = []
                for symbol, market in markets.items():
                    # Detectar USDT según el formato de cada exchange
                    is_usdt = False
                    if ex_id == 'okx' and ('-USDT-SWAP' in symbol or ('-USDT-' in symbol and 'SWAP' in symbol)):
                        is_usdt = True
                    elif ex_id == 'kucoin' and (symbol.endswith('USDTM') or symbol.endswith('USDT')):
                        is_usdt = True
                    elif ex_id == 'mexc' and (symbol.endswith('_USDT') or symbol.endswith('USDT')):
                        is_usdt = True
                    elif ex_id == 'kraken' and symbol.endswith('/USDT'):
                        is_usdt = True
                    if not is_usdt:
                        continue
                    # Filtrar por tipo de mercado
                    if ex_id == 'okx' and not market.get('swap', False):
                        continue
                    if ex_id in ('kucoin', 'mexc') and not market.get('future', False):
                        continue
                    if ex_id == 'kraken' and not market.get('spot', False):
                        continue
                    pairs.append(symbol)
                # Filtrar por volumen (opcional)
                if min_volume_usd > 0:
                    try:
                        tickers = exchange.fetch_tickers()
                        if tickers:
                            filtered = []
                            for sym in pairs:
                                ticker = tickers.get(sym)
                                if ticker:
                                    vol = ticker.get('quoteVolume', 0) or ticker.get('turnover', 0)
                                    if vol >= min_volume_usd:
                                        filtered.append(sym)
                            pairs = filtered
                    except Exception as e:
                        logger.warning(f"Error filtrando volumen en {ex_id}: {e}")
                all_pairs[ex_id] = set(pairs)
                logger.info(f"✅ {ex_id}: {len(pairs)} pares USDT")
            except Exception as e:
                logger.error(f"Error en {ex_id}: {e}")

        if not all_pairs:
            logger.error("❌ No se obtuvieron pares de ningún exchange")
            self._universe_cache = []
            return []

        common = set.intersection(*all_pairs.values()) if len(all_pairs) > 1 else set(list(all_pairs.values())[0])
        common = sorted(list(common))[:max_pairs]
        self._universe_by_exchange = {ex_id: sorted(list(pairs & set(common))) for ex_id, pairs in all_pairs.items()}
        self._universe_cache = common
        logger.info(f"✅ Universo consolidado: {len(common)} pares comunes")
        return common

    def get_universe(self) -> List[str]:
        if self._universe_cache is None:
            self.get_common_pairs()
        return self._universe_cache or []

    def fetch_ohlcv(self, symbol: str, timeframe: str = TIMEFRAME, limit: int = 300,
                    force_refresh: bool = False) -> Optional[pd.DataFrame]:
        for ex_id in EXCHANGE_PRIORITY:
            exchange = self.exchanges.get(ex_id)
            if exchange is None:
                continue

            cache_key = hashlib.md5(f"{symbol}_{timeframe}_{limit}_{ex_id}".encode()).hexdigest()
            cache_path = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
            if not force_refresh and os.path.exists(cache_path):
                try:
                    with open(cache_path, 'rb') as f:
                        df = pickle.load(f)
                    if not df.empty:
                        logger.info(f"📦 Caché para {symbol} desde {ex_id}")
                        return df
                except Exception:
                    pass

            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                if not ohlcv:
                    continue
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                with open(cache_path, 'wb') as f:
                    pickle.dump(df, f)
                logger.info(f"✅ {len(df)} velas reales para {symbol} desde {ex_id}")
                return df
            except Exception as e:
                logger.warning(f"Error en {ex_id} para {symbol}: {e}")
                continue

        logger.error(f"❌ No se pudo obtener {symbol} de ningún exchange")
        return None

    def fetch_historical(self, symbol: str, timeframe: str = TIMEFRAME,
                         days: int = LOOKBACK_DAYS) -> Optional[pd.DataFrame]:
        for ex_id in EXCHANGE_PRIORITY:
            exchange = self.exchanges.get(ex_id)
            if exchange is None:
                continue
            try:
                if timeframe.endswith('m'):
                    minutes = int(timeframe[:-1])
                    candles_per_day = 1440 // minutes
                else:
                    candles_per_day = 288
                limit = days * candles_per_day + 100
                since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
                if not ohlcv:
                    continue
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                cutoff = datetime.now() - timedelta(days=days)
                df = df[df.index >= cutoff]
                logger.info(f"✅ {len(df)} velas históricas para {symbol} desde {ex_id} ({days} días)")
                return df
            except Exception as e:
                logger.warning(f"Error en {ex_id} para histórico de {symbol}: {e}")
                continue
        logger.error(f"❌ No se pudo obtener histórico de {symbol}")
        return None

    def get_status(self) -> Dict:
        return {
            'connected': self.get_available_exchanges(),
            'status': self.exchange_status,
            'universe_size': len(self._universe_cache) if self._universe_cache else 0,
            'primary': self.primary,
        }

    def clear_cache(self):
        self._cache.clear()
        self._cache_timestamps.clear()
        for f in os.listdir(CACHE_DIR):
            try:
                os.remove(os.path.join(CACHE_DIR, f))
            except:
                pass
        logger.info("🧹 Caché limpiada")
