# firm_signals_omega/next_trade_engine.py
"""
Next Trade Engine Ω — Estimación dinámica del tiempo hasta la próxima oportunidad.

Este módulo utiliza un modelo de proceso de Poisson no homogéneo para predecir
cuándo es más probable que aparezca la siguiente señal de alta calidad.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class NextTradeEngine:
    """
    Motor de estimación de tiempo basado en el historial de señales y condiciones actuales.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.history = []          # Lista de intervalos entre señales (minutos)
        self.firm_history = []     # Lista de intervalos entre Firm Signals (minutos)
        self.base_rate = 1.0       # señales por minuto (estimación inicial)

    def update_history(self, signal_history: List[Dict], firm_history: List[Dict]):
        """
        Actualiza los historiales de intervalos.
        """
        # Actualizar historial de señales normales (Trade Óptimo o señales válidas)
        if len(signal_history) > 1:
            intervals = []
            for i in range(1, len(signal_history)):
                if signal_history[i].get('is_valid', False) and signal_history[i-1].get('is_valid', False):
                    dt = (signal_history[i]['timestamp'] - signal_history[i-1]['timestamp']).total_seconds() / 60
                    if dt > 0:
                        intervals.append(dt)
            if intervals:
                self.history = intervals[-50:]  # mantener últimas 50

        # Actualizar historial de Firm Signals
        if len(firm_history) > 1:
            intervals = []
            for i in range(1, len(firm_history)):
                dt = (firm_history[i]['timestamp'] - firm_history[i-1]['timestamp']).total_seconds() / 60
                if dt > 0:
                    intervals.append(dt)
            if intervals:
                self.firm_history = intervals[-20:]  # mantener últimas 20

        # Recalcular tasa base
        if self.history:
            self.base_rate = 1.0 / np.mean(self.history)
        else:
            self.base_rate = 1.0 / 120.0  # una señal cada 2 horas (default)

    def get_regime_factor(self, regime: str) -> float:
        """
        Factor multiplicador según régimen de mercado.
        """
        factors = {
            'Expansión': 1.4,
            'Tendencia Fuerte': 1.2,
            'Tendencia': 0.9,
            'Normal': 0.5,
            'Chop': 0.15,
        }
        return factors.get(regime, 0.5)

    def get_adx_factor(self, adx: float) -> float:
        """
        Factor basado en ADX: a mayor ADX, mayor probabilidad de señal.
        """
        if adx < 20:
            return 0.3
        elif adx < 30:
            return 0.7
        elif adx < 40:
            return 1.0
        else:
            return min(1.2, adx / 35.0)

    def get_atr_factor(self, atr_pct: float) -> float:
        """
        Factor basado en volatilidad (ATR%).
        """
        # atr_pct en porcentaje (ej. 0.15 = 0.15%)
        base = 0.1
        if atr_pct <= 0:
            return 0.5
        factor = 1.0 + (atr_pct - base) * 4.0
        return max(0.3, min(2.0, factor))

    def get_vela_factor(self, current_time_minutes: int) -> float:
        """
        Factor basado en la posición dentro de la vela de 5 minutos.
        """
        # current_time_minutes: 0-5
        if current_time_minutes < 1:
            return 1.2  # inicio de vela, mayor probabilidad
        elif current_time_minutes < 3:
            return 1.0
        else:
            return 0.8  # final de vela, menor probabilidad

    def estimate(
        self,
        regime: str,
        adx: float,
        atr_pct: float,
        current_time_minutes: int,
        last_signal_time: Optional[datetime] = None,
        is_firm: bool = False,
    ) -> Dict:
        """
        Estima el tiempo esperado hasta la próxima señal.
        Retorna un diccionario con:
            - expected_time_minutes: float
            - probability_15min: float
            - probability_30min: float
            - probability_60min: float
            - confidence: float
            - status: str (VERDE, AMARILLO, NARANJA, ROJO, AZUL)
        """
        # Tasa base
        lam = self.base_rate

        # Ajustes por condiciones
        lam *= self.get_regime_factor(regime)
        lam *= self.get_adx_factor(adx)
        lam *= self.get_atr_factor(atr_pct)
        lam *= self.get_vela_factor(current_time_minutes)

        # Si es para Firm Signals, la tasa es menor
        if is_firm:
            lam *= 0.4  # las Firm son menos frecuentes

        # Si no hay historial o tasa demasiado baja, usar valores por defecto
        if lam < 1e-6:
            lam = 1.0 / 180.0  # una señal cada 3 horas

        # Tiempo esperado en minutos
        expected_time = 1.0 / lam

        # Ajuste por tiempo desde la última señal (efecto de renovación)
        if last_signal_time:
            elapsed = (datetime.now() - last_signal_time).total_seconds() / 60
            if elapsed > 0:
                # Si ha pasado más del tiempo esperado, la probabilidad aumenta
                if elapsed > expected_time:
                    expected_time = max(10, expected_time * 0.5)
                else:
                    # Si ha pasado menos, ajustar hacia abajo
                    expected_time = max(5, expected_time * (1 - elapsed / (2 * expected_time)))

        expected_time = max(1.0, expected_time)

        # Calcular probabilidades en diferentes horizontes (asumiendo distribución exponencial)
        # P(T <= t) = 1 - exp(-λ * t)
        probs = {
            '15min': 1 - np.exp(-lam * 15),
            '30min': 1 - np.exp(-lam * 30),
            '60min': 1 - np.exp(-lam * 60),
            '180min': 1 - np.exp(-lam * 180),
        }

        # Confianza: basada en la cantidad de datos históricos
        confidence = min(1.0, len(self.history) / 20.0)

        # Determinar estado (semáforo)
        if expected_time < 5:
            status = "VERDE"      # Hay oportunidad ahora o muy pronto
        elif expected_time < 15:
            status = "AMARILLO"   # Probabilidad alta
        elif expected_time < 45:
            status = "NARANJA"    # Prepararse
        elif expected_time < 120:
            status = "ROJO"       # No revisar durante un tiempo
        else:
            status = "AZUL"       # Mercado muerto

        return {
            'expected_time_minutes': expected_time,
            'probability_15min': probs['15min'],
            'probability_30min': probs['30min'],
            'probability_60min': probs['60min'],
            'probability_180min': probs['180min'],
            'confidence': confidence,
            'status': status,
            'rate_per_minute': lam,
        }

    def get_next_recommendation(self, status: str, expected_time: float) -> str:
        """
        Devuelve una recomendación textual para el operador.
        """
        if status == "VERDE":
            return "✅ Revisa ahora. Hay oportunidades inminentes."
        elif status == "AMARILLO":
            return f"⏳ Prepárate. Probable señal en {int(expected_time)} minutos."
        elif status == "NARANJA":
            return f"🟡 Probabilidad creciente. Revisa en {int(max(5, expected_time*0.5))} minutos."
        elif status == "ROJO":
            return f"🔴 Baja probabilidad. No revises durante {int(expected_time)} minutos."
        else:  # AZUL
            return "🔵 Mercado inactivo. Revisa en 2-3 horas."

    def get_countdown(self, expected_time: float) -> str:
        """
        Devuelve una cuenta regresiva en formato legible.
        """
        if expected_time < 1:
            return "< 1 min"
        elif expected_time < 60:
            return f"{int(expected_time)} min"
        elif expected_time < 120:
            return f"{int(expected_time/60)} h {int(expected_time%60)} min"
        else:
            return f"{int(expected_time/60)} h"
