# ============================================================
# portfolio_manager.py — VERSIÓN CON APALANCAMIENTO DINÁMICO
# ============================================================

# ... (todo el código existente se mantiene)

# ----- NUEVA FUNCIÓN AUXILIAR -----

def _get_dynamic_leverage(symbol, atr_pct, volatility, profile='moderate'):
    max_leverage = 1.0 / (atr_pct * LEVERAGE_SAFETY_MULT) if atr_pct > 0 else 10.0
    max_leverage = min(max_leverage, 10.0)
    if volatility > 0.03:
        max_leverage *= 0.8
    elif volatility < 0.01:
        max_leverage *= 1.2
    profile_factor = LEVERAGE_PROFILE.get(profile, 0.7)
    recommended = max_leverage * profile_factor
    recommended = max(1.0, min(10.0, recommended))
    return {'max_safe': round(max_leverage, 1), 'recommended': round(recommended, 1)}

# ----- MODIFICACIÓN EN calculate_leverage() -----

class PortfolioManager:
    # ... (resto de la clase)

    def calculate_leverage(self, symbol, atr_pct=None, volatility=None, profile=None):
        if USE_DYNAMIC_LEVERAGE and atr_pct is not None:
            if profile is None:
                profile = DEFAULT_LEVERAGE_PROFILE
            result = _get_dynamic_leverage(symbol, atr_pct, volatility, profile)
            self._current_leverage_info = result
            return result['recommended']
        else:
            return LEVERAGE
