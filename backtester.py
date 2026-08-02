# backtester.py
import pandas as pd
import numpy as np
from portfolio_manager import PortfolioManager
from config import INITIAL_CAPITAL, COMMISSION
from utils import apply_hour_filter, calculate_hourly_profit

class Backtester:
    def __init__(self, data_dict, params_by_asset, initial_capital=INITIAL_CAPITAL,
                 use_hour_filter=False, trailing_activation_enabled=True):
        self.data = data_dict
        self.params_by_asset = params_by_asset
        self.global_params = params_by_asset.get('__global__', {})
        self.initial_capital = initial_capital
        self.use_hour_filter = use_hour_filter
        self.trailing_activation_enabled = trailing_activation_enabled
        self.pm = PortfolioManager(initial_capital, self.global_params, trailing_activation_enabled)
        self.equity = []
        self.trades = []

    def run(self):
        if self.use_hour_filter:
            for sym in self.data:
                self.data[sym] = apply_hour_filter(self.data[sym])

        common_idx = None
        for df in self.data.values():
            if common_idx is None:
                common_idx = df.index
            else:
                common_idx = common_idx.intersection(df.index)
        if common_idx is None or common_idx.empty:
            return self.initial_capital, pd.DataFrame(), pd.DataFrame()

        common_idx = common_idx.sort_values()

        for ts in common_idx:
            snapshot = {}
            for sym, df in self.data.items():
                if ts in df.index:
                    snapshot[sym] = df.loc[[ts]]
            if not snapshot:
                continue

            ranking, best, pos = self.pm.rotate(snapshot, self.params_by_asset, ts)

            if self.pm.position is not None:
                sym = self.pm.position['symbol']
                if sym in snapshot:
                    current_price = snapshot[sym]['close'].iloc[0]
                    close_order = self.pm.order_manager.manage_position(
                        self.pm.position, current_price, ts, commission=COMMISSION
                    )
                    if close_order:
                        self.pm.capital += close_order['pnl']
                        self.trades.append(close_order)
                        self.pm.position = None

            equity = self.pm.capital
            if self.pm.position is not None:
                sym = self.pm.position['symbol']
                if sym in snapshot:
                    current_price = snapshot[sym]['close'].iloc[0]
                    unrealized = self.pm.position['size'] * (current_price - self.pm.position['entry_price']) * self.pm.position['direction_multiplier']
                    equity += unrealized
            self.equity.append({'timestamp': ts, 'equity': equity, 'capital': self.pm.capital})

        if self.pm.position is not None:
            sym = self.pm.position['symbol']
            if sym in self.data and not self.data[sym].empty:
                last_price = self.data[sym]['close'].iloc[-1]
                close_order = self.pm.order_manager._close(self.pm.position, last_price, 'end_of_backtest', COMMISSION)
                self.pm.capital += close_order['pnl']
                self.trades.append(close_order)
                self.pm.position = None

        self.equity_df = pd.DataFrame(self.equity)
        self.trades_df = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()
        return self.pm.capital, self.trades_df, self.equity_df

    def calculate_metrics(self):
        if self.trades_df.empty or self.equity_df.empty:
            return {}
        equity = self.equity_df.set_index('timestamp')['equity']
        returns = equity.pct_change().dropna()
        total_return = (equity.iloc[-1] - self.initial_capital) / self.initial_capital
        total_hours = (equity.index[-1] - equity.index[0]).total_seconds() / 3600 if len(equity) > 1 else 0

        winning = self.trades_df[self.trades_df['pnl'] > 0]
        losing = self.trades_df[self.trades_df['pnl'] < 0]
        be = self.trades_df[abs(self.trades_df['pnl']) < 0.001]

        win_rate = len(winning) / len(self.trades_df) if len(self.trades_df) > 0 else 0
        gross_profit = winning['pnl'].sum() if not winning.empty else 0
        gross_loss = abs(losing['pnl'].sum()) if not losing.empty else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

        dd_series = equity / equity.cummax() - 1
        max_dd = dd_series.min()
        avg_dd = dd_series.mean()

        sharpe = returns.mean() / returns.std() * np.sqrt(365*24*60/5) if returns.std() > 0 else 0
        downside = returns[returns < 0]
        sortino = returns.mean() / downside.std() * np.sqrt(365*24*60/5) if downside.std() > 0 else 0
        calmar = total_return / abs(max_dd) if max_dd != 0 else 0
        recovery = total_return / abs(max_dd) if max_dd != 0 else 0
        expectancy = self.trades_df['pnl'].mean() if not self.trades_df.empty else 0

        ruin_threshold = self.initial_capital * 0.05
        ruin_risk = len(equity[equity < ruin_threshold]) / len(equity) if len(equity) > 0 else 0

        hourly_profit = calculate_hourly_profit(total_return, total_hours)

        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'expectancy': expectancy,
            'sharpe': sharpe,
            'sortino': sortino,
            'calmar': calmar,
            'recovery': recovery,
            'max_dd': max_dd,
            'avg_dd': avg_dd,
            'risk_of_ruin': ruin_risk,
            'n_trades': len(self.trades_df),
            'n_wins': len(winning),
            'n_losses': len(losing),
            'n_be': len(be),
            'total_hours': total_hours,
            'hourly_profit_pct': hourly_profit,
            'final_capital': equity.iloc[-1],
        }
