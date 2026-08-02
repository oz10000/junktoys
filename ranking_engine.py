# ranking_engine.py
import numpy as np
from datetime import datetime, timedelta
from scoring_engine import compute_advanced_score, compute_confidence
from amplitude_analyzer import define_zones, compute_amplitudes
from support_resistance import find_pivots, compute_sr_strength

class RankingEngine:
    def __init__(self, data_engine, backtester=None):
        self.data_engine = data_engine
        self.backtester = backtester
        self.historical_metrics_cache = {}
        self.ranking_history = []
        self.top_history = []
    
    def get_historical_metrics(self, symbol):
        """Obtiene métricas históricas del activo (con caché)"""
        if symbol not in self.historical_metrics_cache:
            # Simular métricas de backtest rápido
            # En producción, se cargan desde base de datos
            self.historical_metrics_cache[symbol] = {
                'win_rate': 0.55 + np.random.rand() * 0.3,
                'profit_factor': 1.0 + np.random.rand() * 0.8,
                'expectancy': 0.005 + np.random.rand() * 0.02,
                'max_dd': 0.05 + np.random.rand() * 0.10,
                'n_trades': 20 + int(np.random.rand() * 80),
            }
        return self.historical_metrics_cache[symbol]
    
    def rank_symbols(self, signals, data_dict):
        """
        Rankea los símbolos usando el scoring avanzado
        Retorna: lista ordenada con top 3 destacados
        """
        ranking = []
        
        for signal in signals:
            if not signal.is_valid:
                continue
            
            # Datos de mercado
            df = data_dict.get(signal.symbol)
            if df is None or df.empty:
                continue
            
            market_data = {
                'spread': 0.001,
                'volume': df['volume'].iloc[-1] if not df.empty else 0
            }
            
            # Soportes y resistencias
            supports, resistances = find_pivots(df)
            sr_data = compute_sr_strength(signal.entry_price, supports, resistances)
            
            # Métricas históricas
            metrics = self.get_historical_metrics(signal.symbol)
            
            # Score avanzado
            score, details = compute_advanced_score(signal, metrics, market_data, sr_data)
            confidence = compute_confidence(score, signal, metrics)
            
            # Amplitudes y zonas
            amplitudes = compute_amplitudes(df)
            zones = define_zones(amplitudes.get('avg_candle_range', 0.5), signal.entry_price)
            
            # Predicción de amplitud
            predicted_amplitude = amplitudes.get('avg_candle_range', 0.5) * (1 + confidence * 0.3)
            
            ranking.append({
                'symbol': signal.symbol,
                'signal': signal,
                'score': score,
                'confidence': confidence,
                'direction': signal.direction,
                'entry_price': signal.entry_price,
                'sl': signal.sl_price,
                'tp': signal.tp_price,
                'details': details,
                'amplitudes': amplitudes,
                'zones': zones,
                'predicted_amplitude': predicted_amplitude,
                'supports': supports[:3],
                'resistances': resistances[:3],
                'sr_strength': sr_data[2] if sr_data else 0,
                'metrics': metrics,
                'regime': signal.regime,
            })
        
        # Ordenar por score descendente
        ranking.sort(key=lambda x: x['score'], reverse=True)
        
        # Guardar historial
        self.ranking_history.append({
            'timestamp': datetime.now(),
            'top': ranking[:3] if ranking else [],
            'all': ranking
        })
        
        return ranking
    
    def get_top_n(self, ranking, n=3):
        """Retorna los top N del ranking"""
        return ranking[:n] if ranking else []
    
    def estimate_next_opportunity(self):
        """
        Estima el tiempo hasta la próxima oportunidad de alto score
        basado en el historial de rankings
        """
        if len(self.ranking_history) < 5:
            return None
        
        # Extraer timestamps de señales con score > 0.7
        high_score_times = []
        for entry in self.ranking_history:
            if entry['top'] and entry['top'][0].get('score', 0) > 0.7:
                high_score_times.append(entry['timestamp'])
        
        if len(high_score_times) < 3:
            return None
        
        # Calcular intervalos
        intervals = [
            (high_score_times[i+1] - high_score_times[i]).total_seconds() / 60
            for i in range(len(high_score_times) - 1)
        ]
        
        if not intervals:
            return None
        
        avg_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        last_time = high_score_times[-1]
        now = datetime.now()
        elapsed = (now - last_time).total_seconds() / 60
        remaining = max(0, avg_interval - elapsed)
        
        # Confianza basada en la consistencia
        confidence = 1 - (std_interval / avg_interval) if avg_interval > 0 else 0
        confidence = max(0, min(1, confidence))
        
        return {
            'avg_minutes': avg_interval,
            'remaining_minutes': remaining,
            'std_minutes': std_interval,
            'confidence': confidence,
            'next_estimated': last_time + timedelta(minutes=avg_interval),
        }
    
    def get_statistics(self):
        """Estadísticas del ranking histórico"""
        if not self.ranking_history:
            return {}
        
        scores = [r['top'][0]['score'] if r['top'] else 0 for r in self.ranking_history]
        valid_scores = [s for s in scores if s > 0]
        
        return {
            'avg_score': np.mean(valid_scores) if valid_scores else 0,
            'max_score': max(valid_scores) if valid_scores else 0,
            'min_score': min(valid_scores) if valid_scores else 0,
            'std_score': np.std(valid_scores) if valid_scores else 0,
            'n_samples': len(valid_scores),
            'n_high_score': sum(1 for s in valid_scores if s > 0.7),
        }
