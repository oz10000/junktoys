# exchange_aggregator.py
import pandas as pd
from data_engine import DataEngine
from config import UNIVERSE, UNIVERSE_BY_EXCHANGE

class ExchangeAggregator:
    """Agrega y consolida información de activos entre exchanges"""
    
    def __init__(self, data_engine=None):
        self.data_engine = data_engine or DataEngine()
        self.assets = {}
        self._build_asset_list()
    
    def _build_asset_list(self):
        """Construye lista consolidada de activos con información por exchange"""
        common_pairs = self.data_engine.get_common_pairs()
        exchange_pairs = UNIVERSE_BY_EXCHANGE
        
        for symbol in common_pairs:
            available_on = []
            for ex_id, pairs in exchange_pairs.items():
                if symbol in pairs:
                    available_on.append(ex_id)
            
            self.assets[symbol] = {
                'symbol': symbol,
                'available_on': available_on,
                'exchanges': available_on,
                'primary_exchange': self.data_engine.get_exchange_for_symbol(symbol),
                'status': 'approved'
            }
        
        # Identificar activos no comunes (exclusivos de algunos exchanges)
        for ex_id, pairs in exchange_pairs.items():
            for sym in pairs:
                if sym not in self.assets:
                    self.assets[sym] = {
                        'symbol': sym,
                        'available_on': [ex_id],
                        'exchanges': [ex_id],
                        'primary_exchange': ex_id,
                        'status': 'exclusive'
                    }
    
    def get_approved_assets(self):
        """Retorna activos aprobados (comunes a todos o la mayoría)"""
        return {s: info for s, info in self.assets.items() 
                if info['status'] == 'approved' and len(info['available_on']) >= 2}
    
    def get_recommended_assets(self):
        """Retorna activos recomendados (alto volumen, múltiples exchanges)"""
        # Filtrar por disponibilidad en al menos 3 exchanges
        recommended = {s: info for s, info in self.assets.items()
                       if len(info['available_on']) >= 3 and info['status'] == 'approved'}
        return recommended
    
    def get_rejected_assets(self):
        """Retorna activos descartados"""
        return {s: info for s, info in self.assets.items()
                if info['status'] == 'exclusive' or len(info['available_on']) < 2}
    
    def get_asset_summary(self):
        """Resumen consolidado de activos"""
        total = len(self.assets)
        approved = len(self.get_approved_assets())
        recommended = len(self.get_recommended_assets())
        rejected = len(self.get_rejected_assets())
        
        return {
            'total': total,
            'approved': approved,
            'recommended': recommended,
            'rejected': rejected,
            'by_exchange': {
                ex_id: len([s for s, info in self.assets.items() if ex_id in info['available_on']])
                for ex_id in self.data_engine.get_available_exchanges()
            }
        }
    
    def display_asset_table(self):
        """Genera tabla de activos con disponibilidad por exchange"""
        rows = []
        for symbol, info in list(self.assets.items())[:50]:
            row = {'Activo': symbol}
            for ex_id in ['binance', 'bybit', 'okx', 'kraken', 'kucoin', 'bitget']:
                row[ex_id] = '✅' if ex_id in info['available_on'] else '❌'
            row['Estado'] = info['status']
            rows.append(row)
        return pd.DataFrame(rows)
