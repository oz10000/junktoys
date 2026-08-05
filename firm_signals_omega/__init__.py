# firm_signals_omega/__init__.py
"""
FIRM SIGNALS Ω — Motor de Certificación de Señales de Máxima Calidad

Este módulo proporciona un motor independiente de certificación de señales
que opera con estándares extremadamente exigentes. Solo publica señales
cuando existe una convergencia extraordinaria de factores.
"""

__version__ = "1.0.0"
__author__ = "Junk Toys Research Lab"

from .config import FIRM_SIGNALS_CONFIG
from .data_engine import FirmDataEngine
from .certification_engine import CertificationEngine
from .assistant import ExecutionAssistant
from .signal_generator import SignalGenerator
from .ranking_engine import RankingEngine
from .validator import Validator

__all__ = [
    'FIRM_SIGNALS_CONFIG',
    'FirmDataEngine',
    'CertificationEngine',
    'ExecutionAssistant',
    'SignalGenerator',
    'RankingEngine',
    'Validator'
]
