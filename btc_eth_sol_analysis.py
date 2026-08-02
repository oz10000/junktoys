# btc_eth_sol_analysis.py
import pandas as pd
import numpy as np
from core_engine import compute_adx, compute_atr, compute_regime

class BTC_ETH_SOL_Analyzer:
    """Análisis independiente de Bitcoin, Ethereum y Solana"""
    
    def __init__(self, data_engine):
        self.data_engine = data_engine
        self.data = {}
        self.analysis = {}
        self._fetch_data()
        self._analyze()
    
    def _fetch_data(self):
        """Obtiene datos de BTC, ETH y SOL"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        for sym in symbols:
            df = self.data_engine.fetch_historical(sym, days=90)
            if df is not None and not df.empty:
                self.data[sym] = df
    
    def _analyze(self):
        """Realiza análisis completo"""
        for sym, df in self.data.items():
            if df is None or df.empty:
                continue
            
            close = df['close']
            adx = compute_adx(df)
            atr = compute_atr(df)
            regime = compute_regime(df)
            
            self.analysis[sym] = {
                'price': close.iloc[-1],
                'change_24h': (close.iloc[-1] - close.iloc[-24]) / close.iloc[-24] * 100 if len(close) > 24 else 0,
                'change_7d': (close.iloc[-1] - close.iloc[-168]) / close.iloc[-168] * 100 if len(close) > 168 else 0,
                'change_30d': (close.iloc[-1] - close.iloc[-30*24]) / close.iloc[-30*24] * 100 if len(close) > 720 else 0,
                'adx': adx.iloc[-1] if not adx.empty else 0,
                'atr_pct': (atr.iloc[-1] / close.iloc[-1] * 100) if not atr.empty else 0,
                'regime': regime,
                'volatility': df['close'].pct_change().std() * np.sqrt(252) * 100,
            }
        
        # Análisis comparativo
        self._compute_relative_analysis()
    
    def _compute_relative_analysis(self):
        """Análisis de fortaleza relativa entre BTC, ETH y SOL"""
        if len(self.analysis) < 2:
            return
        
        # Fortaleza relativa (basada en rendimiento y momentum)
        for sym, data in self.analysis.items():
            performance = data['change_7d'] * 0.5 + data['change_30d'] * 0.5
            momentum = data['adx'] / 50
            data['relative_strength'] = performance * 0.6 + momentum * 0.4
        
        # Identificar cuál es más fuerte/débil
        if self.analysis:
            sorted_by_strength = sorted(
                self.analysis.items(),
                key=lambda x: x[1].get('relative_strength', 0),
                reverse=True
            )
            self.analysis['_strongest'] = sorted_by_strength[0][0] if sorted_by_strength else None
            self.analysis['_weakest'] = sorted_by_strength[-1][0] if len(sorted_by_strength) > 1 else None
            
            # Recomendaciones
            self._generate_recommendations()
    
    def _generate_recommendations(self):
        """Genera recomendaciones de trading para BTC/ETH/SOL"""
        recommendations = []
        for sym, data in self.analysis.items():
            if sym.startswith('_'):
                continue
            
            if data.get('relative_strength', 0) > 0.5:
                if data['regime'] in ['Tendencia Fuerte', 'Expansión']:
                    recommendations.append({
                        'symbol': sym,
                        'action': 'LONG',
                        'strength': data['relative_strength'],
                        'regime': data['regime'],
                        'confidence': min(data['relative_strength'], 1.0)
                    })
                else:
                    recommendations.append({
                        'symbol': sym,
                        'action': 'NEUTRAL',
                        'strength': data['relative_strength'],
                        'regime': data['regime'],
                        'confidence': 0.5
                    })
            else:
                if data['regime'] == 'Tendencia Fuerte':
                    recommendations.append({
                        'symbol': sym,
                        'action': 'SHORT',
                        'strength': data['relative_strength'],
                        'regime': data['regime'],
                        'confidence': min(abs(data['relative_strength']) * 0.5, 0.8)
                    })
                else:
                    recommendations.append({
                        'symbol': sym,
                        'action': 'NEUTRAL',
                        'strength': data['relative_strength'],
                        'regime': data['regime'],
                        'confidence': 0.3
                    })
        
        self.analysis['_recommendations'] = sorted(
            recommendations,
            key=lambda x: x['confidence'],
            reverse=True
        )
    
    def get_summary(self):
        """Retorna resumen del análisis"""
        strongest = self.analysis.get('_strongest')
        weakest = self.analysis.get('_weakest')
        
        return {
            'analysis': {k: v for k, v in self.analysis.items() if not k.startswith('_')},
            'strongest': strongest,
            'weakest': weakest,
            'recommendations': self.analysis.get('_recommendations', []),
            'divergences': self._detect_divergences()
        }
    
    def _detect_divergences(self):
        """Detecta divergencias entre BTC, ETH y SOL"""
        divergences = []
        if len(self.analysis) >= 3:
            # Buscar divergencias de precio vs momentum
            prices = {sym: data.get('price', 0) for sym, data in self.analysis.items() if not sym.startswith('_')}
            strengths = {sym: data.get('relative_strength', 0) for sym, data in self.analysis.items() if not sym.startswith('_')}
            
            # Comparar pares
            for sym1 in prices:
                for sym2 in prices:
                    if sym1 < sym2:
                        price_diff = prices[sym2] - prices[sym1]
                        strength_diff = strengths[sym2] - strengths[sym1]
                        if price_diff * strength_diff < 0:  # Divergencia
                            divergences.append({
                                'symbol1': sym1,
                                'symbol2': sym2,
                                'type': 'bearish' if price_diff > 0 and strength_diff < 0 else 'bullish',
                                'severity': abs(price_diff / prices[sym1]) * abs(strength_diff) * 10
                            })
        return divergences
