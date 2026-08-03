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
from typing import Dict, List, Optional, Tuple
from config import (
    EXCHANGE_PRIORITY, EXCHANGE_CONFIGS, CACHE_DIR, OHLCV_DIR,
    TIMEFRAME, LOOKBACK_DAYS, UNIVERSE, UNIVERSE_BY_EXCHANGE
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataEngine:
    """
    Motor de datos multi-exchange.
    Utiliza exclusivamente los exchanges que funcionaron en la verificación:
    OKX, KuCoin, MEXC, Kraken (orden de prioridad).
    Si un exchange falla, pasa al siguiente automáticamente.
    Nunca utiliza datos sintéticos ni fallbacks hardcodeados.
    """

    def __init__(self):
        os.makedirs(OHLCV_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)

        self.exchanges = {}
        self.exchange_status = {}
        self.symbol_maps = {}
        self._connect_exchanges()

        self.primary = self._get_primary_exchange()
        self._cache = {}
        self._cache_timestamps = {}
        self._universe_cache = None
        self._universe_by_exchange = {}

        if not self.primary:
            logger.error("❌ No se pudo conectar a ningún exchange")
        else:
            logger.info(f"✅ DataEngine listo. Primary: {self.primary}")

    def _connect_exchanges(self):
        """Conecta a todos los exchanges configurados (solo los habilitados)."""
        for ex_id in EXCHANGE_PRIORITY:
            config = EXCHANGE_CONFIGS.get(ex_id)
            if not config or config.get('enabled') is False:
                continue

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
                    self.symbol_maps[ex_id] = {
                        m['symbol']: m for m in exchange.markets.values()
                    }
                    logger.info(f"✅ Conectado a {ex_id} ({config['description']})")
                    break
                except Exception as e:
                    logger.warning(f"Intento {attempt+1}/3 para {ex_id} falló: {e}")
                    time.sleep(2)

            if ex_id not in self.exchanges:
                self.exchange_status[ex_id] = 'failed'
                logger.error(f"❌ No se pudo conectar a {ex_id}")

    def _get_primary_exchange(self) -> Optional[str]:
        """Retorna el primer exchange conectado (según orden de prioridad)."""
        for ex_id in EXCHANGE_PRIORITY:
            if self.exchanges.get(ex_id) is not None:
                return ex_id
        return None

    def get_available_exchanges(self) -> List[str]:
        """Retorna lista de exchanges conectados."""
        return [ex_id for ex_id, ex in self.exchanges.items() if ex is not None]

    def get_common_pairs(self, min_volume_usd=200000, max_pairs=500, force_refresh=False) -> List[str]:
        """
        Construye el universo común a partir de la intersección de TODOS los exchanges conectados.
        Si falla, retorna lista vacía (no hay fallback).
        """
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
                    if not symbol.endswith('/USDT'):
                        continue

                    # Filtrar por tipo de mercado según configuración
                    ex_type = EXCHANGE_CONFIGS.get(ex_id, {}).get('options', {}).get('defaultType', 'spot')
                    if ex_type == 'spot' and not market.get('spot', False):
                        continue
                    if ex_type in ('future', 'linear') and not market.get('future', False) and not market.get('linear', False):
                        continue
                    if ex_type == 'swap' and not market.get('swap', False):
                        continue
                    pairs.append(symbol)

                # Filtrar por volumen (opcional)
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
                        logger.warning(f"Error filtrando por volumen en {ex_id}: {e}")

                all_pairs[ex_id] = set(pairs)
                logger.info(f"✅ {ex_id}: {len(pairs)} pares USDT")

            except Exception as e:
                logger.error(f"Error obteniendo pares de {ex_id}: {e}")

        if not all_pairs:
            logger.error("❌ No se obtuvieron pares de ningún exchange")
            self._universe_cache = []
            return []

        # Intersección de todos los exchanges con datos
        common = set.intersection(*all_pairs.values()) if len(all_pairs) > 1 else set(list(all_pairs.values())[0])
        common = sorted(list(common))[:max_pairs]

        self._universe_by_exchange = {ex_id: sorted(list(pairs & set(common))) for ex_id, pairs in all_pairs.items()}
        self._universe_cache = common

        # Actualizar config global
        global UNIVERSE, UNIVERSE_BY_EXCHANGE
        UNIVERSE = common
        UNIVERSE_BY_EXCHANGE = self._universe_by_exchange

        logger.info(f"✅ Universo consolidado: {len(common)} pares comunes")
        return common

    def get_exchange_for_symbol(self, symbol: str) -> Optional[str]:
        """Retorna el mejor exchange para un símbolo (el que lo tiene en su lista)."""
        if self._universe_by_exchange:
            for ex_id in EXCHANGE_PRIORITY:
                if ex_id in self._universe_by_exchange and symbol in self._universe_by_exchange.get(ex_id, []):
                    return ex_id
        return self.primary

    def fetch_ohlcv(self, symbol: str, timeframe: str = TIMEFRAME, limit: int = 300,
                    exchange_id: Optional[str] = None, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Descarga OHLCV reales del primer exchange que funcione.
        Si falla, prueba con el siguiente en orden de prioridad.
        NUNCA retorna datos sintéticos.
        """
        # Determinar orden de intentos
        if exchange_id:
            order = [exchange_id] + [ex for ex in EXCHANGE_PRIORITY if ex != exchange_id]
        else:
            order = EXCHANGE_PRIORITY

        last_error = None
        for ex_id in order:
            exchange = self.exchanges.get(ex_id)
            if exchange is None:
                continue

            # Verificar caché
            cache_key = hashlib.md5(f"{symbol}_{timeframe}_{limit}_{ex_id}".encode()).hexdigest()
            cache_path = os.path.join(CACHE_DIR, f"{cache_key}.pkl")

            if not force_refresh and os.path.exists(cache_path):
                try:
                    with open(cache_path, 'rb') as f:
                        df = pickle.load(f)
                    if not df.empty:
                        logger.info(f"📦 Caché para {symbol} ({timeframe}) desde {ex_id}")
                        return df
                except Exception:
                    pass

            try:
                # Normalizar símbolo para el exchange
                markets = exchange.load_markets()
                if symbol not in markets:
                    # Buscar por ID
                    found = None
                    for sym, market in markets.items():
                        if market.get('id') == symbol or sym == symbol:
                            found = sym
                            break
                    if found:
                        symbol = found
                    else:
                        raise ValueError(f"Símbolo {symbol} no encontrado en {ex_id}")

                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                if not ohlcv:
                    logger.warning(f"⚠️ Sin datos para {symbol} en {ex_id}")
                    continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)

                # Guardar en caché
                with open(cache_path, 'wb') as f:
                    pickle.dump(df, f)

                logger.info(f"✅ {len(df)} velas reales para {symbol} desde {ex_id}")
                return df

            except Exception as e:
                last_error = f"{ex_id}: {str(e)[:80]}"
                logger.warning(f"Error en {ex_id} para {symbol}: {e}")
                continue

        logger.error(f"❌ No se pudo descargar {symbol} de ningún exchange. Último error: {last_error}")
        return None  # NUNCA retorna datos sintéticos

    def fetch_historical(self, symbol: str, timeframe: str = TIMEFRAME,
                         days: int = LOOKBACK_DAYS, exchange_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Descarga histórico real con paginación.
        Prueba exchanges en orden hasta conseguir datos.
        """
        # Determinar orden de intentos
        if exchange_id:
            order = [exchange_id] + [ex for ex in EXCHANGE_PRIORITY if ex != exchange_id]
        else:
            order = EXCHANGE_PRIORITY

        # Calcular límite
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
            candles_per_day = 1440 // minutes
        else:
            candles_per_day = 288
        limit = days * candles_per_day + 100

        for ex_id in order:
            exchange = self.exchanges.get(ex_id)
            if exchange is None:
                continue

            try:
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

        logger.error(f"❌ No se pudo obtener histórico de {symbol} de ningún exchange")
        return None

    def fetch_multi_timeframe(self, symbol: str, timeframes: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """Obtiene velas para múltiples temporalidades."""
        if timeframes is None:
            timeframes = ['5m', '15m', '30m', '1h']

        result = {}
        for tf in timeframes:
            df = self.fetch_ohlcv(symbol, timeframe=tf, limit=300)
            if df is not None and not df.empty:
                result[tf] = df
        return result

    def get_symbols(self) -> List[str]:
        """Retorna el universo de símbolos."""
        return self._universe_cache or []

    def clear_cache(self):
        """Limpia la caché."""
        self._cache.clear()
        self._cache_timestamps.clear()
        for f in os.listdir(CACHE_DIR):
            try:
                os.remove(os.path.join(CACHE_DIR, f))
            except:
                pass
        logger.info("🧹 Caché limpiada")

    def get_status(self) -> Dict:
        """Retorna estado de los exchanges."""
        return {
            'connected': self.get_available_exchanges(),
            'status': self.exchange_status,
            'universe_size': len(self._universe_cache) if self._universe_cache else 0,
            'primary': self.primary,
        }
