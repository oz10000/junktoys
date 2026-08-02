# market_diagnosis.py
import numpy as np
import pandas as pd
from core_engine import compute_adx, compute_atr, compute_ker, compute_regime
from amplitude_analyzer import compute_amplitudes

class MarketDiagnosis:
    """Diagnóstico completo del estado del mercado"""
    
    def __init__(self, data_dict):
        self.data = data_dict
        self.diagnosis = {}
        self._compute_diagnosis()
    
    def _compute_diagnosis(self):
        """Calcula todos los indicadores de mercado"""
        if not self.data:
            return
        
        # Obtener BTC como referencia principal
        btc_data = self.data.get('BTC/USDT')
        if btc_data is not None and not btc_data.empty:
            self._compute_btc_diagnosis(btc_data)
        
        # Diagnóstico general
        all_signals = []
        for sym, df in self.data.items():
            if df is not None and not df.empty and len(df) > 50:
                regime = compute_regime(df)
                adx = compute_adx(df).iloc[-1] if not compute_adx(df).empty else 0
                atr = compute_atr(df).iloc[-1] if not compute_atr(df).empty else 0
                ker = compute_ker(df).iloc[-1] if not compute_ker(df).empty else 0
                amplitudes = compute_amplitudes(df)
                all_signals.append({
                    'symbol': sym,
                    'regime': regime,
                    'adx': adx,
                    'atr_pct': atr / df['close'].iloc[-1] if atr > 0 else 0,
                    'ker': ker,
                    'amplitude': amplitudes.get('avg_candle_range', 0),
                    'volume': df['volume'].iloc[-1] if not df.empty else 0,
                    'close': df['close'].iloc[-1] if not df.empty else 0,
                })
        
        if all_signals:
            df_signals = pd.DataFrame(all_signals)
            
            # Régimen predominante
            regimes = df_signals['regime'].value_counts()
            self.diagnosis['regime'] = regimes.index[0] if not regimes.empty else 'Chop'
            self.diagnosis['regime_distribution'] = regimes.to_dict()
            
            # ADX promedio
            self.diagnosis['avg_adx'] = df_signals['adx'].mean()
            self.diagnosis['avg_adx_std'] = df_signals['adx'].std()
            
            # Volatilidad promedio
            self.diagnosis['avg_volatility'] = df_signals['atr_pct'].mean()
            
            # Amplitud promedio
            self.diagnosis['avg_amplitude'] = df_signals['amplitude'].mean()
            
            # Liquidez (volumen)
            self.diagnosis['total_volume'] = df_signals['volume'].sum()
            self.diagnosis['avg_volume'] = df_signals['volume'].mean()
            
            # Correlación (aproximada)
            self.diagnosis['correlation'] = self._compute_correlation(df_signals)
            
            # Riesgo
            self.diagnosis['risk_level'] = self._compute_risk_level(df_signals)
            
            # Tendencia general
            self.diagnosis['trend'] = self._compute_trend(df_signals)
    
    def _compute_btc_diagnosis(self, btc_data):
        """Diagnóstico específico para BTC"""
        if btc_data is None or btc_data.empty:
            return
        
        close = btc_data['close']
        self.diagnosis['btc'] = {
            'price': close.iloc[-1],
            'change_24h': (close.iloc[-1] - close.iloc[-24]) / close.iloc[-24] * 100 if len(close) > 24 else 0,
            'change_7d': (close.iloc[-1] - close.iloc[-7*24]) / close.iloc[-7*24] * 100 if len(close) > 168 else 0,
            'regime': compute_regime(btc_data),
            'adx': compute_adx(btc_data).iloc[-1] if not compute_adx(btc_data).empty else 0,
        }
    
    def _compute_correlation(self, df_signals):
        """Calcula correlación entre activos"""
        try:
            # Usar precios normalizados
            closes = {}
            for _, row in df_signals.iterrows():
                closes[row['symbol']] = row['close']
            if len(closes) > 1:
                df_corr = pd.DataFrame(closes).corr()
                avg_corr = df_corr.values[np.triu_indices_from(df_corr, k=1)].mean()
                return avg_corr
        except:
            pass
        return 0.5
    
    def _compute_risk_level(self, df_signals):
        """Calcula nivel de riesgo del mercado"""
        # Combinación de volatilidad, drawdown y régimen
        vol = df_signals['atr_pct'].mean()
        regimes = df_signals['regime'].value_counts()
        chop_pct = regimes.get('Chop', 0) / len(df_signals) if len(df_signals) > 0 else 0
        
        risk = vol * 2 + chop_pct * 0.5
        if risk < 0.5:
            return 'Bajo'
        elif risk < 1.0:
            return 'Moderado'
        elif risk < 1.5:
            return 'Alto'
        else:
            return 'Muy Alto'
    
    def _compute_trend(self, df_signals):
        """Calcula tendencia general del mercado"""
        # Usar BTC como referencia
        btc_row = df_signals[df_signals['symbol'] == 'BTC/USDT']
        if not btc_row.empty:
            adx = btc_row['adx'].iloc[0]
            ker = btc_row['ker'].iloc[0]
            if adx > 30 and ker > 0.5:
                return 'Fuerte'
            elif adx > 20 and ker > 0.3:
                return 'Moderada'
            else:
                return 'Lateral'
        return 'Neutral'
    
    def get_summary(self):
        """Retorna resumen del diagnóstico"""
        return {
            'regime': self.diagnosis.get('regime', 'Chop'),
            'trend': self.diagnosis.get('trend', 'Neutral'),
            'avg_adx': self.diagnosis.get('avg_adx', 0),
            'avg_volatility': self.diagnosis.get('avg_volatility', 0),
            'risk_level': self.diagnosis.get('risk_level', 'Moderado'),
            'correlation': self.diagnosis.get('correlation', 0),
            'total_volume': self.diagnosis.get('total_volume', 0),
        }
