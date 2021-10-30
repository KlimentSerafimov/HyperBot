import numpy as np
from talib import RSI


class ProtectedHistory:
    def __init__(self, _history):
        self._history = _history
        self._t = 0
        self._rsi = {}

    def calc_rsi(self, period):
        assert period not in self._rsi
        self._rsi[period] = \
            RSI(np.array([candle.close for candle in self._history]), timeperiod=period)

    def get_rsi(self, period):
        assert period in self._rsi
        return self._rsi[period][self._t]

    def next_timestep(self):
        self._t += 1

    def protected_len(self):
        return len(self._history)

    def begin_date(self):
        return self._history[0].date

    def end_date(self):
        return self._history[-1].end_date

    def __getitem__(self, idx):
        if idx < 0:
            idx = self._t+idx+1
            assert idx >= 0
        assert idx >= 0
        assert isinstance(idx, int)
        assert idx <= self._t
        assert idx < len(self._history)
        return self._history[idx]

    def __iter__(self):
        for idx in range(self._t+1):
            yield self._history[idx]

    def empty(self):
        if self._t < len(self._history):
            return False
        return True

    def get_t(self):
        return self._t

    def get_current_candle(self):
        assert not self.empty()
        return self._history[self._t]

    def last(self, period):
        for idx in range(self._t+1-period, self._t+1):
            yield self._history[idx]

    def subsection(self, init_id, end_id):
        subhistory = self._history[init_id: end_id]
        ret = ProtectedHistory(subhistory)
        for rsi_period in self._rsi:
            ret.calc_rsi(rsi_period)
        return ret

class ProtectedQuotes:
    def __init__(self, _quotes):
        self._quotes = _quotes
        self._t = 0

    def get_t(self):
        return self._t

    def get_currencies(self):
        return [name for name in self._quotes]

    def next_timestep(self):
        self._t += 1
        for currency in self._quotes:
            self._quotes[currency].next_timestep()

    def __getitem__(self, item):
        assert item in self._quotes
        return self._quotes[item]

    def __iter__(self):
        return self._quotes.__iter__()

    def empty(self):
        for currency in self._quotes:
            if self._quotes[currency].empty():
                return True
        return False

    def calc_rsis(self, period):
        for currency in self._quotes:
            self._quotes[currency].calc_rsi(period)

    def subsection(self, init_idx, end_idx):
        new_quotes = {
            curr_name : self._quotes[curr_name].subsection(init_idx, end_idx) for curr_name in self._quotes
        }
        return ProtectedQuotes(new_quotes)
