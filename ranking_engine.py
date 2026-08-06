# ranking_engine.py
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config import DEFAULT_PARAMS, INITIAL_CAPITAL
import logging

logger = logging.getLogger(__name__)

class RankingEngine:
    """Motor de ranking que utiliza métricas históricas reales para la puntuación."""

    def __init__(self, data_engine, backtester=None):
        self.data_engine = data_engine
        self.backtester = backtester
        self.historical_metrics_cache = {}
        self.ranking_history = []
        self.top_history = []

    def get_historical_metrics(self, symbol: str) -> Dict:
        """
        Obtiene métricas históricas reales para un símbolo.
        Si no están cacheadas, las calcula usando backtesting.
        """
        if symbol in self.historical_metrics_cache:
            return self.historical_metrics_cache[symbol]

        # Intentar obtener métricas reales mediante backtesting rápido
        try:
            from backtester import Backtester
            from data_engine import DataEngine
            # Usar el data_engine existente o crear uno nuevo para evitar conflictos
            de = self.data_engine if self.data_engine else DataEngine()
            df = de.fetch_historical(symbol, days=90)
            if df is not None and not df.empty:
                bt = Backtester({symbol: df}, {'__global__': DEFAULT_PARAMS}, INITIAL_CAPITAL)
                _, _, _ = bt.run()
                metrics = bt.calculate_metrics()
                if metrics.get('n_trades', 0) > 5:
                    self.historical_metrics_cache[symbol] = {
                        'win_rate': metrics.get('win_rate', 0.5),
                        'profit_factor': metrics.get('profit_factor', 1.0),
                        'expectancy': metrics.get('expectancy', 0.0),
                        'max_dd': abs(metrics.get('max_dd', 0.1)),
                        'n_trades': metrics.get('n_trades', 0),
                    }
                    return self.historical_metrics_cache[symbol]
        except Exception as e:
            logger.warning(f"Error calculando métricas reales para {symbol}: {e}")

        # Fallback: valores estáticos razonables (no aleatorios)
        fallback = {
            'win_rate': 0.55,
            'profit_factor': 1.2,
            'expectancy': 0.005,
            'max_dd': 0.08,
            'n_trades': 30,
        }
        self.historical_metrics_cache[symbol] = fallback
        logger.info(f"ℹ️ Usando métricas de fallback para {symbol}")
        return fallback

    def rank_symbols(self, signals: List, data_dict: Dict) -> List:
        """
        Rankea los símbolos usando el scoring avanzado.
        """
        ranking = []
        for signal in signals:
            if not signal.is_valid:
                continue

            df = data_dict.get(signal.symbol)
            if df is None or df.empty:
                continue

            market_data = {
                'spread': 0.001,
                'volume': df['volume'].iloc[-1] if not df.empty else 0
            }

            # Soportes y resistencias
            try:
                from support_resistance import find_pivots, compute_sr_strength
                supports, resistances = find_pivots(df)
                sr_data = compute_sr_strength(signal.entry_price, supports, resistances)
            except ImportError:
                sr_data = (None, None, 0.0)

            # Métricas históricas
            metrics = self.get_historical_metrics(signal.symbol)

            # Score avanzado (usando scoring_engine si está disponible)
            try:
                from scoring_engine import compute_advanced_score
                score, details = compute_advanced_score(signal, metrics, market_data, sr_data)
            except ImportError:
                # Fallback: usar score simple
                score = signal.score
                details = {}

            from amplitude_analyzer import compute_amplitudes, define_zones
            amplitudes = compute_amplitudes(df)
            zones = define_zones(amplitudes.get('avg_candle_range', 0.5), signal.entry_price)

            predicted_amplitude = amplitudes.get('avg_candle_range', 0.5) * (1 + score * 0.3)

            # Confianza
            confidence = abs(score) * 0.6 + metrics.get('win_rate', 0.5) * 0.4
            confidence = min(1.0, confidence)

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
                'supports': supports[:3] if supports else [],
                'resistances': resistances[:3] if resistances else [],
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

    def estimate_next_opportunity(self):
        """
        Estima el tiempo hasta la próxima oportunidad de alto score.
        """
        if len(self.ranking_history) < 5:
            return None

        high_score_times = []
        for entry in self.ranking_history:
            if entry['top'] and entry['top'][0].get('score', 0) > 0.7:
                high_score_times.append(entry['timestamp'])

        if len(high_score_times) < 3:
            return None

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
