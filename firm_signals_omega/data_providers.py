# firm_signals_omega/data_providers.py
"""
Proveedores de datos para Firm Signals Ω
Usa OKX, Kraken, KuCoin, CoinGecko, Yahoo Finance
"""

import ccxt
import pandas as pd
import requests
import yfinance as yf
import os
import pickle
import hashlib
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirmDataProvider:
    def __init__(self, cache_dir='data/firm_cache'):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.providers = {
            'okx': self._fetch_okx,
            'kraken': self._fetch_kraken,
            'kucoin': self._fetch_kucoin,
            'coingecko': self._fetch_coingecko,
            'yahoo': self._fetch_yahoo
        }
        self.fallback_chain = ['okx', 'kraken', 'kucoin']

    def get_ohlcv(self, symbol, timeframe='5m', limit=300):
        """Obtiene OHLCV con failover automático"""
        for provider_name in self.fallback_chain:
            try:
                df = self.providers[provider_name](symbol, timeframe, limit)
                if df is not None and not df.empty:
                    logger.info(f"✅ {symbol} desde {provider_name}")
                    return df
            except Exception as e:
                logger.warning(f"⚠️ {provider_name} falló: {e}")
        # Último recurso: Yahoo Finance
        return self._fetch_yahoo(symbol, timeframe, limit)

    def _fetch_okx(self, symbol, timeframe, limit):
        ex = ccxt.okx({'enableRateLimit': True})
        # OKX usa formato BTC-USDT-SWAP
        okx_sym = symbol.replace('/', '-').replace('USDT', 'USDT-SWAP')
        ohlcv = ex.fetch_ohlcv(okx_sym, timeframe, limit=limit)
        if not ohlcv:
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df.astype(float)

    def _fetch_kraken(self, symbol, timeframe, limit):
        ex = ccxt.kraken({'enableRateLimit': True})
        ohlcv = ex.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df.astype(float)

    def _fetch_kucoin(self, symbol, timeframe, limit):
        ex = ccxt.kucoin({'enableRateLimit': True})
        ohlcv = ex.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df.astype(float)

    def _fetch_coingecko(self, symbol, timeframe, limit):
        # CoinGecko solo da datos diarios/horarios
        coin_id = 'bitcoin' if 'BTC' in symbol else 'ethereum' if 'ETH' in symbol else 'solana'
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        days = limit // 24 if timeframe == '1h' else limit
        params = {'vs_currency': 'usd', 'days': days, 'precision': 'full'}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data:
            return None
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df['volume'] = 0  # CoinGecko no da volumen en este endpoint
        return df

    def _fetch_yahoo(self, symbol, timeframe, limit):
        # yfinance para BTC-USD, ETH-USD, SOL-USD
        yf_sym = symbol.replace('/USDT', '-USD')
        ticker = yf.Ticker(yf_sym)
        period = f"{limit // 12}d" if limit > 100 else "5d"
        df = ticker.history(period=period, interval=timeframe)
        if df.empty:
            return None
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        return df
