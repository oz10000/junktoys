# order_manager.py
class OrderManager:
    def __init__(self, trailing_activation_enabled=True):
        self.trailing_activation_enabled = trailing_activation_enabled

    def open_position(self, signal, capital, leverage):
        pos = {
            'symbol': signal.symbol,
            'direction': signal.direction,
            'entry_price': signal.entry_price,
            'sl_price': signal.sl_price,
            'tp_price': signal.tp_price,
            'trailing_activation': signal.trailing_activation if self.trailing_activation_enabled else 0.0,
            'trailing_distance': signal.trailing_distance,
            'break_even_trigger': signal.break_even_trigger,
            'break_even_buffer': signal.break_even_buffer,
            'max_hold_minutes': signal.max_hold_minutes,
            'confidence': signal.confidence,
            'leverage': leverage,
            'size': capital * leverage / signal.entry_price,
            'direction_multiplier': 1 if signal.direction == 'Long' else -1,
            'entry_time': None,
            'trailing_active': False,
            'trailing_sl': None,
            'break_even_activated': False,
            'sl_initial': signal.sl_price,
            'tp_initial': signal.tp_price,
        }
        return pos

    def manage_position(self, position, current_price, timestamp, commission=0.0004):
        if position.get('entry_time') is not None:
            elapsed = (timestamp - position['entry_time']).total_seconds() / 60
            if elapsed >= position['max_hold_minutes']:
                return self._close(position, current_price, 'timeout', commission)

        if position['direction'] == 'Long':
            if current_price <= position['sl_price']:
                return self._close(position, current_price, 'stop_loss', commission)
            if current_price >= position['tp_price']:
                return self._close(position, current_price, 'take_profit', commission)
        else:
            if current_price >= position['sl_price']:
                return self._close(position, current_price, 'stop_loss', commission)
            if current_price <= position['tp_price']:
                return self._close(position, current_price, 'take_profit', commission)

        # Break Even
        if not position['break_even_activated']:
            trigger = position['break_even_trigger']
            if position['direction'] == 'Long' and current_price >= position['entry_price'] * (1 + trigger):
                position['break_even_activated'] = True
                position['sl_price'] = position['entry_price'] * (1 + position['break_even_buffer'])
            elif position['direction'] == 'Short' and current_price <= position['entry_price'] * (1 - trigger):
                position['break_even_activated'] = True
                position['sl_price'] = position['entry_price'] * (1 - position['break_even_buffer'])

        # Trailing
        if self.trailing_activation_enabled:
            if not position['trailing_active']:
                act = position['trailing_activation']
                if position['direction'] == 'Long' and current_price >= position['entry_price'] * (1 + act):
                    position['trailing_active'] = True
                    position['trailing_sl'] = current_price * (1 - position['trailing_distance'])
                elif position['direction'] == 'Short' and current_price <= position['entry_price'] * (1 - act):
                    position['trailing_active'] = True
                    position['trailing_sl'] = current_price * (1 + position['trailing_distance'])
            else:
                dist = position['trailing_distance']
                if position['direction'] == 'Long':
                    new_sl = current_price * (1 - dist)
                    if new_sl > position['trailing_sl']:
                        position['trailing_sl'] = new_sl
                        position['sl_price'] = new_sl
                else:
                    new_sl = current_price * (1 + dist)
                    if new_sl < position['trailing_sl']:
                        position['trailing_sl'] = new_sl
                        position['sl_price'] = new_sl
        else:
            if position['trailing_sl'] is None:
                if position['direction'] == 'Long':
                    position['trailing_sl'] = position['entry_price'] * (1 - position['trailing_distance'])
                else:
                    position['trailing_sl'] = position['entry_price'] * (1 + position['trailing_distance'])
            else:
                dist = position['trailing_distance']
                if position['direction'] == 'Long':
                    new_sl = current_price * (1 - dist)
                    if new_sl > position['trailing_sl']:
                        position['trailing_sl'] = new_sl
                        position['sl_price'] = new_sl
                else:
                    new_sl = current_price * (1 + dist)
                    if new_sl < position['trailing_sl']:
                        position['trailing_sl'] = new_sl
                        position['sl_price'] = new_sl

        return None

    def _close(self, position, current_price, reason, commission):
        pnl = position['size'] * (current_price - position['entry_price']) * position['direction_multiplier']
        pnl -= position['size'] * position['entry_price'] * commission
        pnl -= position['size'] * current_price * commission
        return {
            'symbol': position['symbol'],
            'direction': position['direction'],
            'entry_price': position['entry_price'],
            'exit_price': current_price,
            'pnl': pnl,
            'return_pct': pnl / (position['size'] * position['entry_price'] / position['leverage']) * 100,
            'reason': reason,
            'leverage': position['leverage']
        }
