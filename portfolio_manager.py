# ============================================================
# portfolio_manager.py — VERSIÓN ORIGINAL
# ============================================================
# Este archivo solo existe en el repositorio junktoys.
# Ultra‑Viola‑et‑massive‑toy no tiene este módulo.
# ============================================================

from config import LEVERAGE, RISK_PER_TRADE

class PortfolioManager:
    """
    Gestión de cartera y capital.
    Proporciona el apalancamiento y el riesgo por operación.
    """

    def __init__(self, initial_capital: float = 10000.0):
        self.capital = initial_capital
        self.equity = initial_capital
        self.trades = []
        self.current_positions = []

    def calculate_leverage(self, symbol: str = None) -> int:
        """
        Retorna el apalancamiento fijo definido en la configuración.
        """
        return LEVERAGE

    def calculate_risk_per_trade(self) -> float:
        """
        Retorna el riesgo fijo por operación (porcentaje del capital).
        """
        return RISK_PER_TRADE

    def update_capital(self, pnl: float) -> None:
        """
        Actualiza el capital tras cerrar una operación.
        """
        self.capital += pnl
        self.equity = self.capital

    def add_trade(self, trade: dict) -> None:
        """
        Registra un trade cerrado en el historial.
        """
        self.trades.append(trade)

    def get_equity(self) -> float:
        """
        Retorna el equity actual (capital + ganancias no realizadas).
        """
        return self.equity

    def get_capital(self) -> float:
        """
        Retorna el capital disponible.
        """
        return self.capital

    def reset(self) -> None:
        """
        Reinicia el gestor (para backtesting).
        """
        self.capital = 10000.0
        self.equity = 10000.0
        self.trades = []
        self.current_positions = []
