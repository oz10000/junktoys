# wise_integration.py
import pandas as pd
import requests
import json
import os
from config import WISE_SUPPORTED_CURRENCIES, WISE_DATA_DIR

class WiseIntegration:
    """Integración con Wise para monedas y divisas"""
    
    def __init__(self):
        os.makedirs(WISE_DATA_DIR, exist_ok=True)
        self.supported_currencies = WISE_SUPPORTED_CURRENCIES
        self.rates = {}
        self._fetch_rates()
    
    def _fetch_rates(self):
        """Obtiene tasas de cambio de Wise (API pública)"""
        try:
            # Wise API pública (sin autenticación para tasas)
            url = "https://api.wise.com/v1/rates"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    source = item.get('source')
                    target = item.get('target')
                    rate = item.get('rate')
                    if source in self.supported_currencies and target in self.supported_currencies:
                        key = f"{source}_{target}"
                        self.rates[key] = rate
                self._save_rates()
            else:
                self._load_cached_rates()
        except:
            self._load_cached_rates()
    
    def _save_rates(self):
        """Guarda tasas en caché"""
        try:
            with open(os.path.join(WISE_DATA_DIR, 'rates.json'), 'w') as f:
                json.dump(self.rates, f)
        except:
            pass
    
    def _load_cached_rates(self):
        """Carga tasas desde caché"""
        try:
            with open(os.path.join(WISE_DATA_DIR, 'rates.json'), 'r') as f:
                self.rates = json.load(f)
        except:
            pass
    
    def get_rate(self, from_currency, to_currency):
        """Obtiene tasa de cambio entre dos monedas"""
        key = f"{from_currency}_{to_currency}"
        if key in self.rates:
            return self.rates[key]
        
        # Intentar inversa
        inv_key = f"{to_currency}_{from_currency}"
        if inv_key in self.rates:
            return 1 / self.rates[inv_key]
        
        # Buscar vía USD
        if from_currency == 'USD' or to_currency == 'USD':
            # Si una es USD, buscar directamente
            return None
        
        # Vía USD
        key1 = f"USD_{from_currency}"
        key2 = f"USD_{to_currency}"
        if key1 in self.rates and key2 in self.rates:
            return self.rates[key2] / self.rates[key1]
        
        return None
    
    def convert(self, amount, from_currency, to_currency):
        """Convierte una cantidad de una moneda a otra"""
        rate = self.get_rate(from_currency, to_currency)
        if rate is None:
            return None
        return amount * rate
    
    def get_wise_supported_list(self):
        """Retorna lista de monedas soportadas por Wise"""
        return self.supported_currencies
    
    def get_crypto_wise_mapping(self):
        """Mapeo entre criptomonedas y monedas Wise"""
        return {
            'BTC/USDT': 'USD',
            'ETH/USDT': 'USD',
            'SOL/USDT': 'USD',
            'USDT': 'USD',
            'USDC': 'USD',
        }
    
    def get_wise_table(self):
        """Genera tabla de monedas Wise soportadas"""
        rows = []
        for currency in self.supported_currencies:
            # Obtener tasa vs USD
            rate_usd = self.get_rate(currency, 'USD')
            rows.append({
                'Moneda': currency,
                'Tasa vs USD': rate_usd if rate_usd else 'N/A',
                'Disponible': '✅',
                'Tipo': 'Fiat'
            })
        return pd.DataFrame(rows)
