from pandas import Timestamp


class Candle:
    def __init__(self, date, close, _open, high, low, vol, change=None, idx=None):
        # assert isinstance(date, Timestamp)
        self.date = date
        self.close = float(close)
        self.open = float(_open)
        self.high = float(high)
        self.low = float(low)
        self.max_drawdown = self.low/self.high
        if isinstance(vol, str):
            if vol[-1] == "-":
                vol = "0K"
            assert vol[-1] == "K" or vol[-1] == "M"
            self.vol = float(vol[:-1]) * (1000 if vol[-1] == "K" else 1000000)
        elif isinstance(vol, float) or isinstance(vol, int):
            self.vol = vol
        else:
            assert False
        if change is not None:
            assert change[-1] == '%'
            self.change = float(change[:-1])
        else:
            self.change = None

        self.wait_for_delta = {}
        self.idx = idx

    def get_copy(self):
        return Candle(self.date, self.close, self.open, self.high, self.low, self.vol, self.change, self.idx)

    def style_print(self):
        return \
            str(self.date) + " | " + str(self.open) + " " + str(self.close) + " | " + \
            str(self.low) + " " + str(self.high) + " | " + str(self.vol) + (
                " " + str(self.change) + "%" if self.change is not None else "")

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self.date) + " " + str(self.close) + " " + str(self.open) + " " + str(self.high) + " " + str(self.low) + " " + str(self.vol) + (" " + str(self.change) + "%" if self.change is not None else "")

    def get_trend(self):
        return "up" if self.close > self.open else "down"

    def update(self, other):
        self.close = other.close
        self.high = max(self.high, other.high)
        self.low = max(self.low, other.low)
        self.max_drawdown = self.low/self.high
        self.vol += other.vol
