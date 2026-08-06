# firm_signals_omega/__init__.py
"""
Firm Signals Ω — Motor de Certificación de Señales
"""

from .config import FIRM_SIGNALS_CONFIG

# Intentar importar proveedores
try:
    from .data_providers import FirmDataProvider
except ImportError:
    try:
        from .providers import FirmDataProvider
    except ImportError:
        # Si no hay proveedores, definimos uno dummy (para evitar errores)
        class FirmDataProvider:
            def get_ohlcv(self, symbol, timeframe='5m', limit=300):
                raise NotImplementedError("No data provider available")

__all__ = ['FIRM_SIGNALS_CONFIG', 'FirmDataProvider']
