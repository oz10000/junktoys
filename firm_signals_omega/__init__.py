# firm_signals_omega/__init__.py
"""
Firm Signals Ω — Capa de visualización y análisis contextual
Basado en las señales existentes del motor principal.
"""

from .config import FIRM_SIGNALS_CONFIG
from .helpers import (
    estimate_next_opportunity,
    calculate_support_resistance,
    suggest_leverage,
    format_signal_reason
)
from .streamlit_panel import render_firm_signals_panel
from .next_trade_engine import NextTradeEngine

__all__ = [
    'FIRM_SIGNALS_CONFIG',
    'estimate_next_opportunity',
    'calculate_support_resistance',
    'suggest_leverage',
    'format_signal_reason',
    'render_firm_signals_panel',
    'NextTradeEngine'
]
