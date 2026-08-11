# data_engine.py
import os
import time
import logging
import pandas as pd
import ccxt
from typing import Optional, List

# Importamos la clase CONFIG (contiene todo)
from config import CONFIG

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataEngine:
    """
    Motor de datos con múltiples exchanges, caché y failover.
    Todos los parámetros se obtienen de CONFIG.
    """

    def __init__(self):
        # Usamos CONFIG para todo
        self.cache_dir = CONFIG.CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)
        self.data_dir = CONFIG.DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.logs_dir = CONFIG.LOGS_DIR
        os.makedirs(self.logs_dir, exist_ok=True)

        self.exchanges = {}
        self.primary = None
        self._connect_exchanges()

    def _connect_exchanges(self):
        """Conecta a los exchanges en orden de prioridad."""
        for ex_id in CONFIG.EXCHANGE_PRIORITY:
            try:
                ex_class = getattr(ccxt, ex_id)
                exchange = ex_class({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'},
                    'rateLimit': 1200,
                })
                exchange.load_markets()
                self.exchanges[ex_id] = exchange
                if self.primary is None:
                    self.primary = ex_id
                logger.info(f"✅ Conectado a {ex_id}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo conectar a {ex_id}: {e}")

        if not self.exchanges:
            raise RuntimeError("No se pudo conectar a ningún exchange")

        logger.info(f"✅ DataEngine listo. Primary: {self.primary}")

    def fetch_ohlcv(self, symbol: str, timeframe: str = None, limit: int = 300,
                    use_cache: bool = True, exchange_id: str = None) -> Optional[pd.DataFrame]:
        """
        Obtiene velas OHLCV con caché y failover.
        Si no se especifica timeframe, usa CONFIG.TIMEFRAME.
        """
        if timeframe is None:
            timeframe = CONFIG.TIMEFRAME

        cache_file = os.path.join(
            self.cache_dir,
            f"{symbol.replace('/', '_')}_{timeframe}_{limit}.parquet"
        )

        if use_cache and os.path.exists(cache_file):
            try:
                df = pd.read_parquet(cache_file)
                if (pd.Timestamp.now() - df.index[-1]).total_seconds() < 3600:
                    logger.debug(f"✅ Caché válido para {symbol}")
                    return df
                else:
                    logger.debug(f"⏳ Caché obsoleto para {symbol}, descargando...")
            except Exception as e:
                logger.warning(f"⚠️ Error leyendo caché de {symbol}: {e}")

        # Si se especifica un exchange concreto, usarlo
        if exchange_id:
            exchanges_to_try = {exchange_id: self.exchanges.get(exchange_id)}
            if not exchanges_to_try[exchange_id]:
                logger.error(f"❌ Exchange {exchange_id} no conectado")
                return None
        else:
            exchanges_to_try = self.exchanges

        for ex_id, exchange in exchanges_to_try.items():
            for attempt in range(3):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                    if not ohlcv:
                        logger.warning(f"⚠️ No se obtuvieron velas para {symbol} desde {ex_id}")
                        continue

                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    df.sort_index(inplace=True)

                    if use_cache:
                        try:
                            df.to_parquet(cache_file)
                            logger.debug(f"💾 Caché guardado para {symbol}")
                        except Exception as e:
                            logger.warning(f"⚠️ No se pudo guardar caché de {symbol}: {e}")

                    logger.info(f"✅ {len(df)} velas para {symbol} desde {ex_id}")
                    return df

                except ccxt.RateLimitExceeded:
                    wait = (attempt + 1) * 2
                    logger.warning(f"⏳ Rate limit en {ex_id} (intento {attempt+1}/3). Esperando {wait}s...")
                    time.sleep(wait)

                except ccxt.BadSymbol:
                    logger.warning(f"❌ Símbolo {symbol} no existe en {ex_id}")
                    break

                except Exception as e:
                    logger.error(f"❌ Error en {ex_id} (intento {attempt+1}/3): {e}")
                    time.sleep(1)

            logger.warning(f"⚠️ {ex_id} falló para {symbol}, probando siguiente exchange...")

        logger.error(f"❌ No se pudo descargar {symbol} después de todos los intentos")
        return None

    def fetch_historical(self, symbol: str, days: int = 180, timeframe: str = None) -> Optional[pd.DataFrame]:
        """
        Descarga datos históricos de múltiples velas.
        """
        if timeframe is None:
            timeframe = CONFIG.TIMEFRAME
        # Aproximación: 5m → 12*24 = 288 velas/día
        limit = days * 288
        return self.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def get_certified_assets(self, symbols: Optional[List[str]] = None) -> List[str]:
        """Certifica qué activos existen en el exchange primario."""
        if symbols is None:
            symbols = CONFIG.SYMBOLS

        certified = []
        exchange = self.exchanges.get(self.primary)
        if exchange is None:
            logger.error("❌ No hay exchange primario para certificar activos")
            return certified

        markets = exchange.load_markets()
        for sym in symbols:
            if '/' not in sym:
                sym = f"{sym}/USDT"
            if sym in markets:
                certified.append(sym)
                logger.debug(f"✅ Activo certificado: {sym}")
            else:
                logger.warning(f"⚠️ Activo no encontrado: {sym}")

        # Si no hay certificados, usar fallback
        if not certified:
            logger.warning("⚠️ No se certificaron activos. Usando FALLBACK_SYMBOLS.")
            certified = CONFIG.FALLBACK_SYMBOLS[:10]
        return certified

    def get_common_symbols(self, min_exchanges: int = 2) -> List[str]:
        """Obtiene el universo de símbolos comunes a múltiples exchanges."""
        symbol_sets = []
        for ex_id, exchange in self.exchanges.items():
            try:
                markets = exchange.load_markets()
                usdt_pairs = [s for s in markets if s.endswith('/USDT')]
                symbol_sets.append(set(usdt_pairs))
                logger.info(f"✅ {ex_id}: {len(usdt_pairs)} pares USDT")
            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo pares de {ex_id}: {e}")

        if not symbol_sets:
            logger.warning("⚠️ No se obtuvieron pares de ningún exchange")
            return CONFIG.SYMBOLS

        common = set.intersection(*symbol_sets)
        logger.info(f"✅ Universo consolidado: {len(common)} pares comunes")
        return sorted(common)

    def get_available_exchanges(self) -> List[str]:
        """Retorna la lista de exchanges conectados."""
        return list(self.exchanges.keys())
