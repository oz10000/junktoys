# trade_summary.py
import numpy as np
import pandas as pd
from config import RISK_PER_TRADE, MAX_LEVERAGE_GLOBAL
from risk_engine import get_optimal_leverage, get_position_size

class TradeSummary:
    """Resumen completo de un trade listo para ejecución manual"""

    def __init__(self, signal, metrics, market_data, sr_data, amplitudes, params):
        self.signal = signal
        self.metrics = metrics
        self.market_data = market_data
        self.sr_data = sr_data
        self.amplitudes = amplitudes
        self.params = params
        self._compute_summary()

    def _compute_summary(self):
        # ===== INFORMACIÓN BÁSICA =====
        self.symbol = self.signal.symbol
        self.direction = self.signal.direction
        self.score = self.signal.score
        self.confidence = self.signal.confidence
        self.regime = self.signal.regime
        self.entry_price = self.signal.entry_price

        # ===== POSITION SIZING =====
        # Obtener atr_pct asegurando que sea numérico
        atr_pct = getattr(self.signal, 'atr_pct', 0.01)
        if isinstance(atr_pct, dict):
            atr_pct = atr_pct.get('avg_candle_range', 0.01)
        try:
            atr_pct = float(atr_pct)
        except (TypeError, ValueError):
            atr_pct = 0.01

        self.leverage = get_optimal_leverage(
            self.symbol,
            atr_pct,
            self.confidence,
            self.metrics
        )
        self.position_size = get_position_size(
            self.metrics.get('capital', 10000),
            self.leverage,
            self.entry_price
        )
        self.position_value = self.position_size * self.entry_price

        # ===== STOP LOSS =====
        self.sl_mult = self.params.get('sl_mult', 1.0)
        self.sl_pct = self.sl_mult * atr_pct * 100
        self.sl_price = self.signal.sl_price
        self.sl_amount = abs(self.entry_price - self.sl_price) * self.position_size

        # ===== TAKE PROFIT =====
        self.tp_mult = self.params.get('tp_mult', 2.5)
        self.tp_pct = self.tp_mult * atr_pct * 100
        self.tp_price = self.signal.tp_price
        self.tp_amount = abs(self.tp_price - self.entry_price) * self.position_size

        # ===== RIESGO =====
        self.risk_amount = self.sl_amount
        self.risk_pct = (self.risk_amount / self.metrics.get('capital', 10000)) * 100
        self.risk_reward_ratio = self.tp_amount / self.sl_amount if self.sl_amount > 0 else 0

        # ===== TRAILING CON ACTIVACIÓN =====
        self.trailing_activation_pct = self.params.get('trailing_activation', 0.012) * 100
        self.trailing_activation_price = self.entry_price * (1 + self.trailing_activation_pct / 100) if self.direction == 'Long' else self.entry_price * (1 - self.trailing_activation_pct / 100)
        self.trailing_distance_pct = self.params.get('trailing_distance', 0.008) * 100
        self.trailing_sl_pct = self.trailing_distance_pct
        self.trailing_sl_price = self.entry_price * (1 - self.trailing_distance_pct / 100) if self.direction == 'Long' else self.entry_price * (1 + self.trailing_distance_pct / 100)

        # ===== TRAILING SIN ACTIVACIÓN =====
        self.trailing_no_activation_pct = self.trailing_distance_pct * 0.7
        self.trailing_no_activation_price = self.entry_price * (1 - self.trailing_no_activation_pct / 100) if self.direction == 'Long' else self.entry_price * (1 + self.trailing_no_activation_pct / 100)

        # ===== BREAK EVEN =====
        self.be_trigger_pct = self.params.get('break_even_trigger', 0.008) * 100
        self.be_trigger_price = self.entry_price * (1 + self.be_trigger_pct / 100) if self.direction == 'Long' else self.entry_price * (1 - self.be_trigger_pct / 100)
        self.be_buffer_pct = self.params.get('break_even_buffer', 0.002) * 100

        # ===== PROBABILIDAD =====
        self.probability = self._estimate_probability()
        self.expected_return = self.probability * self.tp_amount - (1 - self.probability) * self.sl_amount

        # ===== DRAWDOWN ESPERADO =====
        self.expected_drawdown = self.sl_amount * (1 - self.probability) * 0.5

        # ===== EDGE =====
        self.edge = self.probability * self.risk_reward_ratio - (1 - self.probability)
        self.edge_type = self._get_edge_type()

        # ===== TIPO DE ENTRADA =====
        self.entry_type = self._get_entry_type()

        # ===== TIEMPO ESTIMADO =====
        self.estimated_duration = self._estimate_duration()

    def _estimate_probability(self):
        base = self.metrics.get('win_rate', 0.5)
        score_adjust = (self.score - 0.3) * 0.3
        conf_adjust = (self.confidence - 0.5) * 0.15
        regime_adjust = {
            'Expansión': 0.10,
            'Tendencia Fuerte': 0.08,
            'Tendencia': 0.04,
            'Normal': 0.00,
            'Chop': -0.05,
        }.get(self.regime, 0.00)
        sr_adjust = (self.sr_data[2] if self.sr_data else 0) * 0.10 if self.sr_data else 0
        prob = base + score_adjust + conf_adjust + regime_adjust + sr_adjust
        return np.clip(prob, 0.1, 0.95)

    def _get_edge_type(self):
        if self.score >= 0.70:
            return 'Máximo'
        elif self.score >= 0.50:
            return 'Medio'
        else:
            return 'Mínimo'

    def _get_entry_type(self):
        if self.edge_type == 'Máximo':
            return 'Market (entrada inmediata)'
        elif self.edge_type == 'Medio':
            return 'Limit (esperar zona A/B)'
        else:
            return 'Evitar (esperar mejor oportunidad)'

    def _estimate_duration(self):
        base_duration = self.params.get('max_hold_minutes', 120)
        regime_factor = 1.0
        if self.regime in ['Expansión', 'Tendencia Fuerte']:
            regime_factor = 0.7
        elif self.regime == 'Chop':
            regime_factor = 1.5
        return base_duration * regime_factor

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'score': self.score,
            'confidence': self.confidence,
            'probability': self.probability,
            'regime': self.regime,
            'edge': self.edge,
            'edge_type': self.edge_type,
            'entry_price': self.entry_price,
            'entry_type': self.entry_type,
            'leverage': self.leverage,
            'position_size': self.position_size,
            'position_value': self.position_value,
            'sl_price': self.sl_price,
            'sl_pct': self.sl_pct,
            'sl_amount': self.sl_amount,
            'tp_price': self.tp_price,
            'tp_pct': self.tp_pct,
            'tp_amount': self.tp_amount,
            'risk_amount': self.risk_amount,
            'risk_pct': self.risk_pct,
            'risk_reward_ratio': self.risk_reward_ratio,
            'expected_drawdown': self.expected_drawdown,
            'expected_return': self.expected_return,
            'trailing_activation_pct': self.trailing_activation_pct,
            'trailing_activation_price': self.trailing_activation_price,
            'trailing_distance_pct': self.trailing_distance_pct,
            'trailing_sl_price': self.trailing_sl_price,
            'trailing_no_activation_pct': self.trailing_no_activation_pct,
            'trailing_no_activation_price': self.trailing_no_activation_price,
            'be_trigger_pct': self.be_trigger_pct,
            'be_trigger_price': self.be_trigger_price,
            'be_buffer_pct': self.be_buffer_pct,
            'estimated_duration_minutes': self.estimated_duration,
        }

    def to_dataframe(self):
        data = self.to_dict()
        return pd.DataFrame([{
            'Parámetro': k.replace('_', ' ').title(),
            'Valor': v
        } for k, v in data.items()])

    def get_trailing_comparison(self):
        return {
            'Estrategia A (con activación)': {
                'Win Rate estimado': f"{self.probability * 1.05:.1%}",
                'Activación': f"{self.trailing_activation_pct:.2f}%",
                'Distancia': f"{self.trailing_distance_pct:.2f}%",
                'Precio SL': f"${self.trailing_sl_price:.2f}",
            },
            'Estrategia B (sin activación)': {
                'Win Rate estimado': f"{self.probability * 0.95:.1%}",
                'Activación': 'N/A',
                'Distancia': f"{self.trailing_no_activation_pct:.2f}%",
                'Precio SL': f"${self.trailing_no_activation_price:.2f}",
            }
        }
