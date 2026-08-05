# firm_signals_omega/certification_engine.py
"""
Motor de Certificación — Firm Signals Ω

Aplica múltiples niveles de filtrado para certificar señales de máxima calidad.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from .config import (
    QUALITY_THRESHOLDS, MICROSTRUCTURE_THRESHOLDS, 
    HOUR_FILTER, WEEKDAY_FILTER, MACRO_EVENTS,
    ALLOWED_REGIMES, REJECTED_REGIMES
)

logger = logging.getLogger(__name__)

class CertificationEngine:
    """
    Motor de certificación de señales con múltiples niveles de filtrado
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.passed_levels = []
        self.certification_log = []
        self.status = "ESPERAR"
        self.progress = 0.0
        self._current_signal = None
        
        # Definir niveles de certificación
        self.certification_levels = [
            ('calidad', self._certify_quality),
            ('confirmacion', self._certify_confirmation),
            ('microestructura', self._certify_microstructure),
            ('temporal', self._certify_temporal),
            ('contexto', self._certify_context),
        ]
    
    def certify(self, candidate: Dict, market_data: Dict, macro_data: Dict = None) -> Dict:
        """
        Certifica una señal candidata a través de todos los niveles
        """
        self.passed_levels = []
        self.progress = 0.0
        self.status = "PREPARANDO"
        self._current_signal = candidate
        
        results = {}
        
        for level_name, level_func in self.certification_levels:
            self.status = f"CERTIFICANDO: {level_name}"
            result = level_func(candidate, market_data, macro_data)
            results[level_name] = result
            
            if not result.get('passed', False):
                self.status = "CANCELADA"
                self.progress = self._calculate_progress()
                return self._build_response(candidate, results)
            
            self.passed_levels.append(level_name)
            self.progress = self._calculate_progress()
        
        self.status = "PUBLICADA"
        self.progress = 1.0
        
        # Registrar certificación
        self.certification_log.append({
            'timestamp': datetime.now(),
            'symbol': candidate.get('symbol'),
            'direction': candidate.get('direction'),
            'passed_levels': self.passed_levels,
        })
        
        return self._build_response(candidate, results)
    
    def _certify_quality(self, candidate: Dict, market: Dict, macro: Dict) -> Dict:
        """Nivel 1: Calidad de la señal"""
        symbol = candidate.get('symbol', '')
        thresholds = QUALITY_THRESHOLDS.get(symbol, QUALITY_THRESHOLDS.get('BTC/USDT', {}))
        
        checks = {
            'score': candidate.get('score', 0) >= thresholds.get('min_score', 0.65),
            'adx': candidate.get('adx', 0) >= thresholds.get('min_adx', 25),
            'adx_slope': candidate.get('adx_slope', 0) > 0,
            'ker': candidate.get('ker', 0) >= thresholds.get('min_ker', 0.45),
            'regime': candidate.get('regime', '') in ALLOWED_REGIMES,
        }
        
        passed = all(checks.values())
        return {
            'passed': passed,
            'details': checks,
            'message': '✅ Calidad aprobada' if passed else '❌ Calidad insuficiente'
        }
    
    def _certify_confirmation(self, candidate: Dict, market: Dict, macro: Dict) -> Dict:
        """Nivel 2: Confirmaciones multi-timeframe"""
        symbol = candidate.get('symbol', '')
        thresholds = QUALITY_THRESHOLDS.get(symbol, QUALITY_THRESHOLDS.get('BTC/USDT', {}))
        
        checks = {
            'volume_ratio': candidate.get('volume_ratio', 1) >= thresholds.get('min_volume_ratio', 1.2),
            'volume_accel': candidate.get('volume_accel', 0) > 0,
            'cvd': self._check_cvd(candidate),
            'timeframes': candidate.get('timeframes_aligned', 0) >= thresholds.get('min_timeframes_aligned', 3),
        }
        
        passed = all(checks.values())
        return {
            'passed': passed,
            'details': checks,
            'message': '✅ Confirmaciones aprobadas' if passed else '❌ Confirmaciones insuficientes'
        }
    
    def _certify_microstructure(self, candidate: Dict, market: Dict, macro: Dict) -> Dict:
        """Nivel 3: Microestructura"""
        imbalance = market.get('order_book_imbalance', 0)
        
        checks = {
            'imbalance': abs(imbalance) >= MICROSTRUCTURE_THRESHOLDS.get('min_imbalance', 0.3),
            'funding': abs(candidate.get('funding_rate', 0)) < MICROSTRUCTURE_THRESHOLDS.get('max_funding_rate', 0.01),
            'oi_growing': market.get('oi_growing', False),
        }
        
        # Dirección del imbalance debe coincidir con la señal
        if candidate.get('direction') == 'LONG' and imbalance > 0:
            checks['imbalance_direction'] = True
        elif candidate.get('direction') == 'SHORT' and imbalance < 0:
            checks['imbalance_direction'] = True
        else:
            checks['imbalance_direction'] = False
        
        passed = all(checks.values())
        return {
            'passed': passed,
            'details': checks,
            'message': '✅ Microestructura aprobada' if passed else '❌ Microestructura insuficiente'
        }
    
    def _certify_temporal(self, candidate: Dict, market: Dict, macro: Dict) -> Dict:
        """Nivel 4: Filtros temporales"""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()
        
        checks = {
            'hour_ok': HOUR_FILTER['start'] <= hour <= HOUR_FILTER['end'],
            'weekday_ok': weekday in WEEKDAY_FILTER,
            'no_macro_event': not self._is_macro_event(),
        }
        
        passed = all(checks.values())
        return {
            'passed': passed,
            'details': checks,
            'message': '✅ Temporal aprobado' if passed else '❌ Temporal insuficiente'
        }
    
    def _certify_context(self, candidate: Dict, market: Dict, macro: Dict) -> Dict:
        """Nivel 5: Contexto macro y correlaciones"""
        checks = {
            'macro_favorable': self._check_macro(macro, candidate),
            'correlation_ok': self._check_correlation(market, candidate),
        }
        
        passed = all(checks.values())
        return {
            'passed': passed,
            'details': checks,
            'message': '✅ Contexto aprobado' if passed else '❌ Contexto desfavorable'
        }
    
    def _check_cvd(self, candidate: Dict) -> bool:
        """Verifica CVD en dirección de la señal"""
        cvd = candidate.get('cvd', 0)
        direction = candidate.get('direction', '')
        if direction == 'LONG':
            return cvd > 0
        elif direction == 'SHORT':
            return cvd < 0
        return True
    
    def _is_macro_event(self) -> bool:
        """Verifica si hay evento macro en las próximas 2 horas"""
        # En producción, se consultaría un calendario económico
        # Simulación: asumir que no hay eventos
        return False
    
    def _check_macro(self, macro: Dict, candidate: Dict) -> bool:
        """Verifica condiciones macro favorables"""
        if macro is None:
            return True  # Si no hay datos macro, no penalizar
        
        # Verificar que S&P 500 no está en caída libre
        spx_change = macro.get('SPX_change', 0)
        if spx_change < -0.03:  # Caída >3%
            return False
        
        return True
    
    def _check_correlation(self, market: Dict, candidate: Dict) -> bool:
        """Verifica correlaciones favorables"""
        # Implementación simplificada
        return True
    
    def _calculate_progress(self) -> float:
        """Calcula el progreso de certificación"""
        if not self.certification_levels:
            return 0.0
        return len(self.passed_levels) / len(self.certification_levels)
    
    def _build_response(self, candidate: Dict, results: Dict) -> Dict:
        """Construye la respuesta final de certificación"""
        is_published = self.status == "PUBLICADA"
        
        return {
            'status': self.status,
            'progress': self.progress,
            'passed_levels': self.passed_levels,
            'results': results,
            'signal': candidate if is_published else None,
            'timestamp': datetime.now().isoformat(),
            'message': self._get_status_message(),
        }
    
    def _get_status_message(self) -> str:
        """Obtiene mensaje de estado"""
        if self.status == "PUBLICADA":
            return "🎯 SEÑAL CERTIFICADA — Lista para ejecutar"
        elif self.status == "CANCELADA":
            return "⛔ SEÑAL RECHAZADA — No cumple criterios"
        elif self.status == "PREPARANDO":
            return "⏳ PREPARANDO — Evaluando condiciones"
        else:
            return f"📡 {self.status}"
    
    def get_estimation(self) -> Dict:
        """Estima tiempo y probabilidad de próxima señal"""
        # Basado en histórico de certificaciones
        if not self.certification_log:
            return {
                'remaining_minutes': 45,
                'probability_15min': 0.15,
                'probability_30min': 0.35,
                'probability_1h': 0.55,
                'probability_3h': 0.75,
                'probability_6h': 0.85,
                'probability_12h': 0.92,
                'probability_24h': 0.95,
                'confidence': 0.70,
            }
        
        # Calcular intervalos promedio entre certificaciones
        timestamps = [log['timestamp'] for log in self.certification_log]
        if len(timestamps) > 1:
            intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() / 60 
                        for i in range(len(timestamps)-1)]
            avg_interval = np.mean(intervals)
            std_interval = np.std(intervals)
        else:
            avg_interval = 180  # 3 horas por defecto
            std_interval = 60
        
        last_time = timestamps[-1] if timestamps else datetime.now() - timedelta(hours=2)
        elapsed = (datetime.now() - last_time).total_seconds() / 60
        remaining = max(0, avg_interval - elapsed)
        
        return {
            'remaining_minutes': remaining,
            'probability_15min': min(0.95, 0.05 + 0.5 * (1 - remaining / max(avg_interval, 1))),
            'probability_30min': min(0.95, 0.10 + 0.6 * (1 - remaining / max(avg_interval, 1))),
            'probability_1h': min(0.95, 0.20 + 0.7 * (1 - remaining / max(avg_interval, 1))),
            'probability_3h': min(0.95, 0.40 + 0.8 * (1 - remaining / max(avg_interval, 1))),
            'probability_6h': min(0.95, 0.60 + 0.9 * (1 - remaining / max(avg_interval, 1))),
            'probability_12h': min(0.95, 0.75 + 0.95 * (1 - remaining / max(avg_interval, 1))),
            'probability_24h': 0.95,
            'confidence': 1 - (std_interval / avg_interval) if avg_interval > 0 else 0.7,
        }
