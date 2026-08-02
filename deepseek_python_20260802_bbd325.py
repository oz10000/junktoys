# signal_engine.py
from core_engine import compute_adx, compute_ker, compute_atr, compute_regime, compute_pidelta_score

class Signal:
    def __init__(self, symbol, df, params):
        self.symbol = symbol
        self.params = params
        self.df = df
        self.score = 0.0
        self.adx = 0.0
        self.ker = 0.0
        self.atr_pct = 0.0
        self.regime = 'Chop'
        self.is_valid = False
        self.reason = "No evaluado"
        self.direction = None
        self.confidence = 0.0
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.trailing_activation = 0.0
        self.trailing_distance = 0.0
        self.break_even_trigger = 0.0
        self.break_even_buffer = 0.0
        self.max_hold_minutes = 0
        if not df.empty and len(df) > 30:
            self._compute()

    def _compute(self):
        p = self.params
        close = self.df['close'].iloc[-1]
        self.score = compute_pidelta_score(self.df)
        adx_series = compute_adx(self.df)
        self.adx = adx_series.iloc[-1] if not adx_series.empty else 0
        ker_series = compute_ker(self.df, 10)
        self.ker = ker_series.iloc[-1] if not ker_series.empty else 0
        atr_series = compute_atr(self.df)
        self.atr_pct = (atr_series.iloc[-1] / close) if not atr_series.empty else 0
        self.regime = compute_regime(self.df)

        self.is_valid = True
        self.reason = "OK"
        if abs(self.score) < p['min_score']:
            self.is_valid = False
            self.reason = f"score {self.score:.2f} < {p['min_score']}"
        elif self.adx < p['adx_threshold']:
            self.is_valid = False
            self.reason = f"ADX {self.adx:.1f} < {p['adx_threshold']}"
        elif self.ker < p['ker_threshold']:
            self.is_valid = False
            self.reason = f"KER {self.ker:.2f} < {p['ker_threshold']}"
        elif self.regime == 'Chop':
            self.is_valid = False
            self.reason = "Régimen Chop"
        else:
            self.direction = 'Long' if self.score > 0 else 'Short'
            ema15 = self.df['close'].ewm(span=15).mean().iloc[-1]
            if self.direction == 'Long' and close < ema15:
                self.is_valid = False
                self.reason = "Precio < EMA15"
            elif self.direction == 'Short' and close > ema15:
                self.is_valid = False
                self.reason = "Precio > EMA15"

        if self.is_valid:
            self.entry_price = close
            sl_mult = p['sl_mult']
            tp_mult = p['tp_mult']
            if self.regime in ['Tendencia Fuerte', 'Expansión']:
                tp_mult *= 1.1
            if self.direction == 'Long':
                self.sl_price = close * (1 - sl_mult * self.atr_pct)
                self.tp_price = close * (1 + tp_mult * self.atr_pct)
            else:
                self.sl_price = close * (1 + sl_mult * self.atr_pct)
                self.tp_price = close * (1 - tp_mult * self.atr_pct)
            self.trailing_activation = p['trailing_activation']
            self.trailing_distance = p['trailing_distance']
            self.break_even_trigger = p['break_even_trigger']
            self.break_even_buffer = p['break_even_buffer']
            self.max_hold_minutes = p['max_hold_minutes']
            self.confidence = (abs(self.score) * 0.4 + (self.adx / 50) * 0.3 + self.ker * 0.2)
            if self.regime in ['Tendencia Fuerte', 'Expansión']:
                self.confidence += 0.1
            self.confidence = min(1.0, self.confidence)
        else:
            self.direction = None
            self.confidence = 0.0