# portfolio_manager.py
import pandas as pd
from signal_engine import Signal
from order_manager import OrderManager
from risk_engine import get_optimal_leverage

class PortfolioManager:
    def __init__(self, initial_capital, global_params, trailing_activation_enabled=True):
        self.capital = initial_capital
        self.position = None
        self.global_params = global_params
        self.trailing_activation_enabled = trailing_activation_enabled
        self.order_manager = OrderManager(trailing_activation_enabled)
        self.history = []

    def scan(self, data_dict, params_by_asset):
        signals = []
        for sym, df in data_dict.items():
            params = params_by_asset.get(sym, self.global_params)
            signal = Signal(sym, df, params)
            if signal.is_valid:
                signals.append(signal)
        if not signals:
            return []
        longs = [s for s in signals if s.direction == 'Long']
        shorts = [s for s in signals if s.direction == 'Short']
        best_long = max(longs, key=lambda x: x.confidence) if longs else None
        best_short = max(shorts, key=lambda x: x.confidence) if shorts else None
        candidates = []
        if best_long:
            candidates.append(best_long)
        if best_short:
            candidates.append(best_short)
        if candidates:
            best = max(candidates, key=lambda x: x.confidence)
            return [best]
        return []

    def rotate(self, data_dict, params_by_asset, timestamp):
        ranking = self.scan(data_dict, params_by_asset)
        best = ranking[0] if ranking else None
        if best is None:
            return ranking, None, None

        if self.position is None:
            leverage = get_optimal_leverage(best.symbol, best.atr_pct, best.confidence)
            pos = self.order_manager.open_position(best, self.capital, leverage)
            pos['entry_time'] = timestamp
            self.position = pos
            return ranking, best, pos

        current_sym = self.position['symbol']
        gap = params_by_asset.get(current_sym, self.global_params).get('rotation_confidence_gap', 0.15)
        if best.symbol != current_sym and best.confidence > self.position['confidence'] + gap:
            close_order = self.order_manager._close(
                self.position,
                data_dict[current_sym]['close'].iloc[-1],
                'rotation',
                commission=0.0004
            )
            self.capital += close_order['pnl']
            self.history.append(close_order)
            self.position = None
            leverage = get_optimal_leverage(best.symbol, best.atr_pct, best.confidence)
            pos = self.order_manager.open_position(best, self.capital, leverage)
            pos['entry_time'] = timestamp
            self.position = pos
            return ranking, best, pos

        return ranking, best, self.position
