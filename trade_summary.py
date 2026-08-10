# trade_summary.py
# Versión corregida y ampliada para Junk Toys v6.2.1
# Maneja sr_data como escalar o lista, evitando TypeError

import numpy as np
import pandas as pd
from typing import Union, List, Tuple, Optional

class TradeSummary:
    """
    Genera un resumen ejecutable de una operación basada en la señal,
    métricas, datos de mercado, ratio de Sharpe (u otros) y parámetros.
    """

    def __init__(
        self,
        signal: dict,
        metrics: dict,
        market_data: pd.DataFrame,
        sr_data: Union[float, List[float], Tuple[float, ...], None],
        amplitudes: dict,
        params: dict
    ):
        """
        Args:
            signal: Diccionario con señal (ej. {'action':'buy', 'price':...})
            metrics: Diccionario con métricas de rendimiento (drawdown, winrate, etc.)
            market_data: DataFrame con precios/velas (necesario para calcular tendencia, etc.)
            sr_data: Puede ser:
                - float: valor único de Sharpe ratio
                - list/tuple: (sharpe, sortino, calmar, ...) al menos 3 elementos
                - None: sin datos
            amplitudes: Diccionario con amplitudes (ej. para ATR)
            params: Parámetros de configuración (ej. timeframe, stop loss, etc.)
        """
        self.signal = signal
        self.metrics = metrics
        self.market_data = market_data
        self.sr_data = self._normalize_sr_data(sr_data)  # <-- normalización
        self.amplitudes = amplitudes
        self.params = params

        # Atributos que se llenarán en _compute_summary
        self.action = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.probability = 0.0
        self.risk_reward = 0.0
        self.regime = "Lateral"
        self.trend_strength = 0.0
        self.adx_avg = 0.0
        self.risk_level = "Medio"

        self._compute_summary()

    def _normalize_sr_data(self, sr_data):
        """
        Convierte sr_data a una tupla de al menos 3 elementos.
        Si es float, se convierte a (float, 0.0, 0.0).
        Si es None, se usa (0.0, 0.0, 0.0).
        Si es lista/tupla con menos de 3, se rellena con ceros.
        """
        if sr_data is None:
            return (0.0, 0.0, 0.0)
        if isinstance(sr_data, (int, float)):
            return (float(sr_data), 0.0, 0.0)
        if isinstance(sr_data, (list, tuple)):
            # Asegurar al menos 3 elementos
            if len(sr_data) == 0:
                return (0.0, 0.0, 0.0)
            elif len(sr_data) == 1:
                return (float(sr_data[0]), 0.0, 0.0)
            elif len(sr_data) == 2:
                return (float(sr_data[0]), float(sr_data[1]), 0.0)
            else:
                return tuple(float(x) for x in sr_data[:3])
        # Cualquier otro tipo, tratar como 0
        return (0.0, 0.0, 0.0)

    def _compute_summary(self):
        """Calcula todos los campos del resumen."""
        # Acción y precios
        self.action = self.signal.get('action', 'HOLD')
        self.entry_price = self.signal.get('price', 0.0)

        # Stop Loss y Take Profit desde amplitud (ATR, etc.)
        atr = self.amplitudes.get('atr', 0.0)
        if self.action == 'BUY':
            self.stop_loss = self.entry_price - 2 * atr
            self.take_profit = self.entry_price + 3 * atr
        elif self.action == 'SELL':
            self.stop_loss = self.entry_price + 2 * atr
            self.take_profit = self.entry_price - 3 * atr
        else:
            self.stop_loss = self.entry_price
            self.take_profit = self.entry_price

        # Riesgo/recompensa
        if self.stop_loss and self.stop_loss != self.entry_price:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.take_profit - self.entry_price) if self.take_profit else 0
            self.risk_reward = reward / risk if risk > 0 else 0
        else:
            self.risk_reward = 0

        # Probabilidad estimada (usando sr_data normalizado)
        self.probability = self._estimate_probability()

        # Régimen de mercado (usando market_data)
        self._compute_regime()

    def _estimate_probability(self) -> float:
        """
        Estima la probabilidad de éxito de la operación.
        Usa el Sharpe (primer elemento de sr_data) como base.
        """
        # Obtener el Sharpe (índice 0) de la tupla normalizada
        sharpe = self.sr_data[0] if len(self.sr_data) > 0 else 0.0
        # También podemos usar el tercer elemento (índice 2) como ajuste, pero ahora es seguro
        # Ajuste por Calmar (índice 2) si existe
        calmar = self.sr_data[2] if len(self.sr_data) > 2 else 0.0

        # Base de probabilidad: 50% + (sharpe * 10%) + (calmar * 5%)
        prob = 0.50 + (sharpe * 0.10) + (calmar * 0.05)
        # Acotar entre 0 y 1
        prob = max(0.0, min(1.0, prob))
        return prob

    def _compute_regime(self):
        """Determina régimen de mercado basado en datos OHLC."""
        if self.market_data is None or len(self.market_data) < 20:
            self.regime = "Desconocido"
            self.trend_strength = 0
            self.adx_avg = 0
            self.risk_level = "Alto"
            return

        # Calcular ADX y tendencia simple (ejemplo simplificado)
        try:
            close = self.market_data['Close']
            high = self.market_data['High']
            low = self.market_data['Low']

            # Cálculo ADX (aproximado)
            atr = self._atr(high, low, close, 14)
            plus_dm = np.where(high.diff() > low.diff(), np.maximum(high.diff(), 0), 0)
            minus_dm = np.where(low.diff() > high.diff(), np.maximum(low.diff(), 0), 0)
            plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(14).mean().iloc[-1] if len(dx) > 0 else 0
            self.adx_avg = adx if not np.isnan(adx) else 0

            # Fuerza de tendencia
            if self.adx_avg > 25:
                self.trend_strength = "Fuerte" if self.adx_avg > 40 else "Moderada"
                self.regime = "Tendencia"
            else:
                self.trend_strength = "Débil"
                self.regime = "Lateral"

            # Riesgo basado en volatilidad
            vol = close.pct_change().std() * np.sqrt(252)
            if vol < 0.2:
                self.risk_level = "Bajo"
            elif vol < 0.4:
                self.risk_level = "Medio"
            else:
                self.risk_level = "Alto"

        except Exception as e:
            # Si falla, valores por defecto
            self.regime = "Indeterminado"
            self.trend_strength = 0
            self.adx_avg = 0
            self.risk_level = "Alto"

    def _atr(self, high, low, close, period=14):
        """Calcula el Average True Range."""
        tr1 = high - low
        tr2 = np.abs(high - close.shift())
        tr3 = np.abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def to_dict(self) -> dict:
        """Devuelve un diccionario con todos los campos."""
        return {
            'action': self.action,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'probability': self.probability,
            'risk_reward': self.risk_reward,
            'regime': self.regime,
            'trend_strength': self.trend_strength,
            'adx_avg': self.adx_avg,
            'risk_level': self.risk_level,
        }

    def __repr__(self):
        return f"<TradeSummary action={self.action} prob={self.probability:.2f}>"
