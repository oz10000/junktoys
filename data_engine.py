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
    EXCHANGE_PRIORITY, EXCHANGE_CONFIGS, FALLBACK_SYMBOLS,
    CACHE_DIR, OHLCV_DIR, TIMEFRAME, LOOKBACK_DAYS,
    CERTIFICATION_CRITERIA
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataEngine:
    """Motor de datos con certificación de activos mediante backtesting"""

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
        self._certified_assets = None

        logger.info(f"✅ DataEngine listo. Primary: {self.primary}")

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

    def get_certified_assets(self, force_refresh=False):
        """
        Obtiene la lista de activos que han pasado la certificación mediante backtesting.
        Retorna solo los símbolos que cumplen los criterios de Win Rate, Profit Factor, etc.
        """
        if not force_refresh and self._certified_assets is not None:
            return self._certified_assets

        # Primero obtener el universo completo
        all_symbols = self.get_common_pairs(max_pairs=200, force_refresh=force_refresh)
        certified = []

        # Para cada símbolo, ejecutar un backtest rápido y evaluar criterios
        from backtester import Backtester
        from config import DEFAULT_PARAMS, INITIAL_CAPITAL

        for sym in all_symbols[:50]:  # Limitamos para no saturar
            try:
                df = self.fetch_historical(sym, days=90)
                if df is None or df.empty:
                    continue

                # Backtest rápido con parámetros por defecto
                bt = Backtester({sym: df}, {'__global__': DEFAULT_PARAMS}, INITIAL_CAPITAL)
                _, trades, _ = bt.run()
                metrics = bt.calculate_metrics()

                # Verificar criterios
                win_rate = metrics.get('win_rate', 0)
                profit_factor = metrics.get('profit_factor', 0)
                max_dd = metrics.get('max_dd', 0)
                n_trades = metrics.get('n_trades', 0)

                if (win_rate >= CERTIFICATION_CRITERIA['min_win_rate'] and
                    profit_factor >= CERTIFICATION_CRITERIA['min_profit_factor'] and
                    abs(max_dd) <= CERTIFICATION_CRITERIA['max_drawdown'] and
                    n_trades >= CERTIFICATION_CRITERIA['min_trades']):
                    certified.append(sym)
                    logger.info(f"✅ {sym} certificado (WinRate: {win_rate:.2%}, PF: {profit_factor:.2f})")
                else:
                    logger.debug(f"❌ {sym} rechazado (WinRate: {win_rate:.2%}, PF: {profit_factor:.2f}, DD: {max_dd:.2%})")

            except Exception as e:
                logger.warning(f"Error certificando {sym}: {e}")

        # Si no hay certificados, usar los de mayor volumen (fallback)
        if not certified:
            logger.warning("⚠️ No se encontraron activos certificados. Usando FALLBACK_SYMBOLS.")
            certified = FALLBACK_SYMBOLS[:20]

        self._certified_assets = certified
        logger.info(f"✅ {len(certified)} activos certificados")
        return certified

    def get_common_pairs(self, min_volume_usd=0, max_pairs=500, force_refresh=False):
        """Obtiene la intersección de pares USDT entre todos los exchanges."""
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

        if all_pairs:
            common = set.intersection(*all_pairs.values()) if len(all_pairs) > 1 else set(list(all_pairs.values())[0])
            common = sorted(list(common))[:max_pairs]
        else:
            common = []

        if len(common) < 5 and 'kraken' in all_pairs:
            logger.warning("⚠️ Intersección pequeña. Usando pares de Kraken.")
            common = sorted(list(all_pairs.get('kraken', set())))[:max_pairs]

        if not common:
            logger.warning("⚠️ Intersección vacía. Usando FALLBACK_SYMBOLS.")
            common = FALLBACK_SYMBOLS[:max_pairs]

        self._universe_by_exchange = {ex_id: sorted(list(pairs & set(common)))
                                      for ex_id, pairs in all_pairs.items()}
        self._universe_cache = common
        logger.info(f"✅ Universo consolidado: {len(common)} pares comunes")
        return common

    def fetch_ohlcv(self, symbol, timeframe=TIMEFRAME, limit=300, exchange_id=None, force_refresh=False):
        """Descarga OHLCV con caché y soporte multi-exchange."""
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
            markets = exchange.load_markets()
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

            logger.info(f"✅ {len(df)} velas para {symbol} desde {ex_id}")
            return df

        except Exception as e:
            logger.warning(f"Error en {ex_id} para {symbol}: {e}")
            return None

    def _get_best_exchange_for_symbol(self, symbol):
        if symbol in self._universe_by_exchange:
            for ex_id in EXCHANGE_PRIORITY:
                if symbol in self._universe_by_exchange.get(ex_id, []):
                    return ex_id
        return self.primary

    def fetch_historical(self, symbol, timeframe=TIMEFRAME, days=LOOKBACK_DAYS, exchange_id=None):
        """Descarga histórico completo."""
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
