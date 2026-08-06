# firm_signals_omega/__init__.py
"""
Firm Signals Ω — Módulo de Certificación de Señales
"""

# Intentar importar el proveedor de datos
try:
    from .data_providers import FirmDataProvider
except ImportError:
    from .providers import FirmDataProvider  # fallback

# Exponer config
from .config import FIRM_SIGNALS_CONFIG

__all__ = ['FIRM_SIGNALS_CONFIG', 'FirmDataProvider']
