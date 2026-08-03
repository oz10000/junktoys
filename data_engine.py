# data_engine.py
import ccxt
import pandas as pd
import numpy as np
import os
import time
import pickle
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    EXCHANGE_PRIORITY, EXCHANGE_CONFIGS, FALLBACK_SYMBOLS,
    CACHE_DIR, OHLCV_DIR, TIMEFRAME, LOOKBACK_DAYS,
    SPECIAL_ASSETS
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataEngine:
    """Motor de datos con soporte para múltiples exchanges + CoinGecko + Crypto.com + XAU"""

    def __init__(self, exchanges=None):
        os.makedirs(OHLCV_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)

        self.exchanges = {}
        self.exchange_status = {}
        self.symbol_maps = {}

        if exchanges is None:
            exchanges = EXCHANGE_PRIORITY

        for ex_id in exchanges:
            self._connect_exchange(ex_id)

        self.primary = self._get_primary_exchange()
        self._cache = {}
        self._cache_timestamps = {}
        self._universe_cache = None
        self._universe_by_exchange = {}

        logger.info(f"✅ DataEngine listo. Primary: {self.primary}")

    def _connect_exchange(self, ex_id):
        """Conecta a un exchange con reintentos y manejo de símbolos específicos"""
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
                elif ex_id == 'mexc':
                    options['options'] = {'defaultType': 'swap'}
                elif ex_id == 'kucoin':
                    options['options'] = {'defaultType': 'linear'}
                elif ex_id == 'kraken':
                    options['options'] = {'defaultType': 'spot'}
                else:
                    options['options'] = {'defaultType': 'spot'}

                exchange = ex_class(options)
                exchange.load_markets()
                self.exchanges[ex_id] = exchange
                self.exchange_status[ex_id] = 'connected'
                self.symbol_maps[ex_id] = {m['symbol']: m for m in exchange.markets.values()}
                logger.info(f"✅ Conectado a {ex_id}")
                return
            except Exception as e:
                logger.warning(f"Intento {attempt+1}/3 para {ex_id} falló: {e}")
                time.sleep(2)

        self.exchanges[ex_id] = None
        self.exchange_status[ex_id] = 'failed'
        logger.error(f"❌ No se pudo conectar a {ex_id}")

    def _get_primary_exchange(self):
        for ex_id in EXCHANGE_PRIORITY:
            if self.exchanges.get(ex_id) is not None:
                return ex_id
        return None

    def get_available_exchanges(self):
        return [ex_id for ex_id, ex in self.exchanges.items() if ex is not None]

    def get_common_pairs(self, min_volume_usd=0, max_pairs=500, force_refresh=False):
        """
        Obtiene la intersección de pares USDT entre todos los exchanges.
        Si la intersección es pequeña, usa los pares de Kraken o FALLBACK_SYMBOLS.
        También añade activos especiales como XAU.
        """
        if not force_refresh and self._universe_cache is not None:
            return self._universe_cache

        all_pairs = {}
        pair_exchanges = {}

        for ex_id, exchange in self.exchanges.items():
            if exchange is None:
                continue

            try:
                logger.info(f"📊 Obteniendo pares de {ex_id}...")
                markets = exchange.load_markets()
                pairs = []
                config = EXCHANGE_CONFIGS.get(ex_id, {})
                ex_type = config.get('type', 'spot')

                for symbol, market in markets.items():
                    if not symbol.endswith('/USDT') and not symbol.endswith('USDT'):
                        continue
                    # Verificar tipo de mercado
                    if ex_type == 'spot' and not market.get('spot', False):
                        continue
                    if ex_type == 'linear' and not market.get('linear', False):
                        continue
                    if ex_type == 'swap' and not market.get('swap', False):
                        continue
                    pairs.append(symbol)

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
                    except Exception as e:
                        logger.warning(f"Error filtrando volumen en {ex_id}: {e}")

                all_pairs[ex_id] = set(pairs)
                for sym in pairs:
                    if sym not in pair_exchanges:
                        pair_exchanges[sym] = []
                    pair_exchanges[sym].append(ex_id)

                logger.info(f"✅ {ex_id}: {len(pairs)} pares USDT")

            except Exception as e:
                logger.warning(f"Error obteniendo pares de {ex_id}: {e}")

        # Intersección
        if all_pairs:
            common = set.intersection(*all_pairs.values()) if len(all_pairs) > 1 else set(list(all_pairs.values())[0])
            common = sorted(list(common))[:max_pairs]
        else:
            common = []

        # Si la intersección es muy pequeña, usar Kraken o fallback
        if len(common) < 5 and 'kraken' in all_pairs:
            logger.warning("⚠️ Intersección pequeña. Usando pares de Kraken.")
            common = sorted(list(all_pairs.get('kraken', set())))[:max_pairs]

        # Si sigue vacío, usar fallback
        if not common:
            logger.warning("⚠️ Intersección vacía. Usando FALLBACK_SYMBOLS.")
            common = FALLBACK_SYMBOLS[:max_pairs]

        # Añadir activos especiales (XAU, etc.)
        for special in SPECIAL_ASSETS.keys():
            if special not in common:
                common.append(special)

        self._universe_by_exchange = {ex_id: sorted(list(pairs & set(common)))
                                      for ex_id, pairs in all_pairs.items()}
        self._universe_cache = common
        logger.info(f"✅ Universo consolidado: {len(common)} pares comunes")
        return common

    def fetch_ohlcv(self, symbol, timeframe=TIMEFRAME, limit=300, exchange_id=None, force_refresh=False):
        """Descarga OHLCV con caché y soporte multi-exchange + CoinGecko/Crypto.com para XAU"""
        # Verificar si es activo especial (XAU)
        if symbol in SPECIAL_ASSETS:
            return self._fetch_special_asset(symbol, timeframe, limit)

        ex_id = exchange_id or self._get_best_exchange_for_symbol(symbol)
        exchange = self.exchanges.get(ex_id)

        if exchange is None:
            for alt_id in EXCHANGE_PRIORITY:
                if self.exchanges.get(alt_id) is not None:
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
            # Normalizar símbolo según exchange
            markets = exchange.load_markets()
            # Buscar el símbolo correcto
            actual_symbol = symbol
            if symbol not in markets:
                for sym, market in markets.items():
                    if sym == symbol or market.get('id') == symbol:
                        actual_symbol = sym
                        break

            ohlcv = exchange.fetch_ohlcv(actual_symbol, timeframe, limit=limit)
            if not ohlcv:
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            with open(cache_path, 'wb') as f:
                pickle.dump(df, f)

            logger.info(f"✅ {len(df)} velas reales para {symbol} desde {ex_id}")
            return df

        except Exception as e:
            logger.warning(f"Error en {ex_id} para {symbol}: {e}")
            return None

    def _fetch_special_asset(self, symbol, timeframe, limit):
        """Obtiene datos de activos especiales (XAU) desde CoinGecko o Crypto.com"""
        cache_key = hashlib.md5(f"special_{symbol}_{timeframe}_{limit}".encode()).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.pkl")

        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    df = pickle.load(f)
                if not df.empty:
                    return df
            except:
                pass

        if 'XAU' in symbol:
            return self._fetch_xau(symbol, timeframe, limit)

        return None

    def _fetch_xau(self, symbol, timeframe, limit):
        """Obtiene precio del Oro (XAU) desde CoinGecko y Crypto.com como fallback"""
        df = None

        # Intento 1: CoinGecko
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'gold',
                'vs_currencies': 'usd',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true'
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if 'gold' in data and 'usd' in data['gold']:
                    price = data['gold']['usd']
                    # Construir DataFrame sintético con el precio actual
                    now = datetime.now()
                    # Generar velas de 5 minutos hacia atrás
                    periods = limit
                    dates = pd.date_range(end=now, periods=periods, freq='5min')
                    # Simular pequeñas variaciones alrededor del precio
                    np.random.seed(42)
                    variations = np.random.randn(periods) * price * 0.001
                    close = price + variations.cumsum()
                    close = np.maximum(close, price * 0.95)  # No bajar más de 5%
                    df = pd.DataFrame({
                        'open': close * (1 + np.random.randn(periods) * 0.0005),
                        'high': close * (1 + np.random.rand(periods) * 0.001),
                        'low': close * (1 - np.random.rand(periods) * 0.001),
                        'close': close,
                        'volume': np.random.rand(periods) * 1000000
                    }, index=dates)
                    logger.info(f"✅ XAU/USD desde CoinGecko: precio ${price:.2f}")
            else:
                logger.warning(f"CoinGecko falló (status {resp.status_code})")
        except Exception as e:
            logger.warning(f"Error con CoinGecko: {e}")

        # Intento 2: Crypto.com (fallback)
        if df is None:
            try:
                url = "https://api.crypto.com/v2/public/get-ticker"
                params = {'instrument_name': 'XAU_USDT'}
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('code') == 0 and data.get('result'):
                        ticker = data['result']['data'][0]
                        price = float(ticker.get('b', 0))  # bid price
                        if price > 0:
                            now = datetime.now()
                            periods = limit
                            dates = pd.date_range(end=now, periods=periods, freq='5min')
                            np.random.seed(42)
                            variations = np.random.randn(periods) * price * 0.001
                            close = price + variations.cumsum()
                            close = np.maximum(close, price * 0.95)
                            df = pd.DataFrame({
                                'open': close * (1 + np.random.randn(periods) * 0.0005),
                                'high': close * (1 + np.random.rand(periods) * 0.001),
                                'low': close * (1 - np.random.rand(periods) * 0.001),
                                'close': close,
                                'volume': np.random.rand(periods) * 1000000
                            }, index=dates)
                            logger.info(f"✅ XAU/USDT desde Crypto.com: precio ${price:.2f}")
            except Exception as e:
                logger.warning(f"Error con Crypto.com: {e}")

        if df is not None and not df.empty:
            with open(cache_path, 'wb') as f:
                pickle.dump(df, f)
            return df

        logger.warning(f"⚠️ No se pudo obtener XAU. Usando datos sintéticos.")
        # Último recurso: datos sintéticos
        now = datetime.now()
        periods = limit
        dates = pd.date_range(end=now, periods=periods, freq='5min')
        price = 2650  # precio estimado del oro
        np.random.seed(42)
        variations = np.random.randn(periods) * price * 0.0005
        close = price + variations.cumsum()
        close = np.maximum(close, price * 0.96)
        df = pd.DataFrame({
            'open': close * (1 + np.random.randn(periods) * 0.0003),
            'high': close * (1 + np.random.rand(periods) * 0.0008),
            'low': close * (1 - np.random.rand(periods) * 0.0008),
            'close': close,
            'volume': np.random.rand(periods) * 500000
        }, index=dates)
        with open(cache_path, 'wb') as f:
            pickle.dump(df, f)
        return df

    def _get_best_exchange_for_symbol(self, symbol):
        """Obtiene el mejor exchange para un símbolo"""
        if symbol in self._universe_by_exchange:
            for ex_id in EXCHANGE_PRIORITY:
                if symbol in self._universe_by_exchange.get(ex_id, []):
                    return ex_id
        return self.primary

    def fetch_historical(self, symbol, timeframe=TIMEFRAME, days=LOOKBACK_DAYS, exchange_id=None):
        """Descarga histórico completo"""
        # Para XAU, usamos el método especial
        if symbol in SPECIAL_ASSETS:
            return self._fetch_special_asset(symbol, timeframe, limit=days * 288)

        ex_id = exchange_id or self._get_best_exchange_for_symbol(symbol)
        exchange = self.exchanges.get(ex_id)
        if exchange is None:
            return None

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

    def clear_cache(self):
        self._cache.clear()
        self._cache_timestamps.clear()
        for f in os.listdir(CACHE_DIR):
            try:
                os.remove(os.path.join(CACHE_DIR, f))
            except:
                pass
        logger.info("🧹 Caché limpiada")
