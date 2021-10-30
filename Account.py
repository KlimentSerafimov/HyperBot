import math

import matplotlib
import matplotlib.pyplot as plt

from Candle import Candle

import gc

class PendingTrade:
    def __init__(self, open_or_close, t, args=None):
        if args is None:
            args = []
        assert open_or_close == "open" or open_or_close == "close"
        if open_or_close == "open":
            assert args[0] == "Long" or args[0] == "Short" or args[0] == "Hold"
        self.open_or_close = open_or_close
        self.args = args
        self.t = t
        self.entry_price = None

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "<" + self.open_or_close + ((" " + str(self.args)) if len(self.args) >= 1 else "") + ">"

    def get_direction(self):
        assert self.open_or_close == "open"
        assert self.args[0] == "Long" or self.args[0] == "Short"
        return self.args[0]


class Account:
    def __init__(self, _portfolio, macro_candle_size = 1):
        self.max_drawdown = 1
        self.portfolio = _portfolio
        assert len(self.portfolio) == 1
        self.currency = [x for x in self.portfolio][0]

        self.history_of_trades = []

        self.local_top = 0

        self._pending_trades = []

        self.total_btc = 1
        self.never_liquidate = False
        self.liquidated = False
        self.in_liquidation = False

        self.in_trade = False
        self.direction = None
        self.entry_price = None
        self.initial_margin = 0
        self.leverage = None
        self.total_contracts = 0
        self.total_contract_value_in_btc = 0
        self.fee_to_open = 0
        self.liquidation_price = None
        self.fee_to_close = 0
        self.sum_funding_fees = 0


        self.taker_fee = 0.075 / 100
        self.funding_fee = 0.01 / 100

        self.num_trades = 0
        self.open_portfolio_at = 1

        self.macro_candle_w = macro_candle_size
        self.local_macro_candle_w = 0

        self.macro_derivative_history = []

        self.print_verbose = 0

    def clear(self):
        del self.macro_derivative_history
        del self.history_of_trades

        # gc.collect()

    def print_open_trade(self, date):
        assert not self.in_trade
        self.open_portfolio_at = self.total_btc
        if self.print_verbose >= 1:
            print("#" + str(self.num_trades), "OPEN", self.direction)
            print("date", date)
            print("initial_margin", self.initial_margin)
            print("leverage", self.leverage)
            print("entry_price", self.entry_price)
            print("liquidation_price", self.liquidation_price)
            print()

    def print_close_trade(self, exit_price, date):
        assert self.in_trade
        gain = self.total_btc / self.open_portfolio_at - 1
        if self.print_verbose >= 1:
            print("#" + str(self.num_trades), "CLOSE ", self.direction)
            print("date", date)
            print("exit_price", exit_price)
            print("absolute_gain", self.total_btc - self.open_portfolio_at)
            print("total (" + self.currency + ")", self.total_btc)
            print("percent_gain ", gain)
            print()

    def perform_open_trade(self, _direction, _leverage, _entry_price, action_date):
        assert not self.in_trade

        assert _direction is not None

        if _direction == "Hold":
            return

        self.direction = _direction
        self.entry_price = _entry_price
        self.initial_margin = self.total_btc
        self.leverage = _leverage
        self.total_contracts = self.initial_margin * self.leverage * self.entry_price
        self.total_contract_value_in_btc = self.total_contracts / self.entry_price
        # Fee to open = (Quantity of contracts/Order Price) x taker fee
        self.fee_to_open = self.taker_fee * self.total_contracts / self.entry_price
        # Bankruptcy Price for Long position = (Average Entry Price x Leverage) / (Leverage+1)
        self.liquidation_price = \
            self.entry_price * 200 if _leverage == 1 and self.direction == "Short" \
                else self.entry_price * _leverage / (
                    _leverage + (1 if self.direction == "Long" else -1))
        #  (Quantity of contracts/Bankruptcy Price derived from Order Price*) x taker fee
        self.fee_to_close = None
        self.sum_funding_fees = self.funding_fee * self.initial_margin  # todo

        self.num_trades += 1
        self.print_open_trade(action_date)
        assert self.direction is not None
        self.in_trade = True

    def total_gain(self):
        if len(self.macro_derivative_history) >= 1:
            return self.macro_derivative_history[-1].close/self.macro_derivative_history[0].open
        else:
            assert self.total_btc == 1
            return 1

    def prefix_gain(self, prefix_percent, do_print = False):
        assert len(self.macro_derivative_history) >= 1
        prefix_abs = int(prefix_percent*(len(self.macro_derivative_history)-1))
        if do_print:
            print(len(self.macro_derivative_history)-prefix_abs)
        return self.macro_derivative_history[prefix_abs].close/self.macro_derivative_history[0].open

    def prefix_max_drawdown(self, prefix_percent):
        assert len(self.macro_derivative_history) >= 1
        prefix_abs = int(prefix_percent * (len(self.macro_derivative_history) - 1))
        # print(prefix_abs, len(self.macro_derivative_history))
        return self.macro_derivative_history[prefix_abs].max_drawdown

    def past_gain(self, window):
        if window == math.inf:
            return self.total_gain()

        scaled_window = window//self.macro_candle_w

        # print(scaled_window, len(self.macro_derivative_history))

        if scaled_window < len(self.macro_derivative_history):
            return self.macro_derivative_history[-1].close / self.macro_derivative_history[-scaled_window].open
        else:
            return self.total_gain()

    def plot(self, title, plot):
        x = []
        y = []

        plot_num_points = 1000
        for idx, row in enumerate(self.macro_derivative_history):
            if True or idx % int(1 + len(self.macro_derivative_history) / plot_num_points) == 0:
                x.append(row.date)
                y.append(row.close)

        plot.plot(x, y, label=title)
        plot.set_yscale("log")
        plot.legend()

    def get_min(self):
        return min([candle.close for candle in self.macro_derivative_history])

    def get_max(self):
        return max([candle.close for candle in self.macro_derivative_history])

    def perform_close_trade(self, exit_price, action_date):
        assert self.in_trade
        self.total_btc += self.closed_p_and_l(exit_price)
        self.print_close_trade(exit_price, action_date)

        # if self.total_btc <= 0:
        #     assert self.in_liquidation
        #     # todo
        #     self.liquidate(exit_price, action_date)
        #     # assert self.check_is_liquidated_and_if_true_then_liquidate(exit_price,
        #     #                                                            action_date)
        # if self.check_is_liquidated_and_if_true_then_liquidate(exit_price, action_date):
        #     # todo
        #     # assert self.total_btc <= 0
        #     pass

        self.sum_funding_fees = 0
        self.fee_to_close = 0
        self.liquidation_price = None
        self.fee_to_open = 0
        self.total_contract_value_in_btc = 0
        self.total_contracts = 0
        self.initial_margin = 0
        self.leverage = None
        self.entry_price = None
        self.direction = None
        self.in_trade = False

    def unrealized_p_and_l(self, last_traded_price):
        if self.in_trade:
            if self.direction == "Long":
                return self.total_contracts * (1 / self.entry_price - 1 / last_traded_price)
            elif self.direction == "Short":
                return self.total_contracts * (
                        -1 / self.entry_price + 1 / last_traded_price)
            else:
                assert False
        else:
            return 0

    def unrealized_p_and_l_to_price(self, p_and_l):
        if self.in_trade:
            if self.direction == "Long":
                return self.total_contracts / (
                        - p_and_l + self.total_contracts / self.entry_price)
            elif self.direction == "Short":
                return self.total_contracts / (
                        p_and_l + self.total_contracts / self.entry_price)
            else:
                assert False
        else:
            assert False

    def closed_p_and_l_to_price(self, closed_p_and_l):
        assert self.in_trade
        return self.unrealized_p_and_l_to_price(closed_p_and_l - (
                - self.fee_to_open - self.fee_to_close - self.sum_funding_fees))

    def closed_p_and_l_percent_to_price(self, closed_p_and_l_percent):
        assert self.in_trade
        return self.closed_p_and_l_to_price(closed_p_and_l_percent * self.initial_margin)

    def closed_p_and_l_percent(self, last_traded_price):
        absolut = self.closed_p_and_l(last_traded_price)
        if absolut == 0:
            ret = 0
        else:
            ret = absolut / self.initial_margin
        return ret

    def closed_p_and_l(self, last_traded_price):
        if self.in_trade:
            if self.direction == "Short":
                return 0
            self.fee_to_close = self.taker_fee * self.total_contracts / last_traded_price
            ret = \
                self.unrealized_p_and_l(last_traded_price) \
                - self.fee_to_open - self.fee_to_close - self.sum_funding_fees
            return ret
        else:
            return 0

    def liquidate(self, last_traded_price, date):

        # print("liquidate")
        # print(self.total_btc)
        # print(self.direction)
        # print("entry:", self.entry_price)
        # print("last_traded:", last_traded_price)
        # print(date)


        assert not self.liquidated
        self.in_liquidation = True
        self.perform_close_trade(last_traded_price, date)
        self.in_liquidation = False
        # todo
        # assert self.total_btc <= 0
        self.liquidated = True
        if self.print_verbose >= 1:
            print("FORCED_LIQUIDATION")

    def check_is_liquidated_and_if_true_then_liquidate(self, last_traded_price, date):
        if self.total_btc < 0:
            # todo to fix liquidation price
            self.liquidate(last_traded_price, date)
            return

        if self.direction == "Long":
            if last_traded_price < self.liquidation_price:
                self.liquidate(last_traded_price, date)
            else:
                pass
        elif self.direction == "Short":
            if last_traded_price > self.liquidation_price:
                self.liquidate(last_traded_price, date)
            else:
                pass
        else:
            assert False

    def open_trade(self, direction, leverage, t):
        new_trade = PendingTrade("open", t, (direction, leverage))
        self.history_of_trades.append(new_trade)
        self._pending_trades.append(new_trade)
        assert len(self._pending_trades) <= 2

    def close_trade(self, t):
        new_trade = PendingTrade("close", t)
        self.history_of_trades.append(new_trade)
        # print("close_trade")
        self._pending_trades.append(new_trade)
        assert len(self._pending_trades) <= 1

    def simulate_open_candle(self, candle):
        if self.liquidated:
            self._pending_trades.clear()
            return
        if not self.never_liquidate:
            if self.in_trade:
                self.check_is_liquidated_and_if_true_then_liquidate(candle.open, candle.date)
                if self.liquidated:
                    self.process_gains(candle, candle.open)
                    self._pending_trades.clear()
                    return

        if not self.liquidated:
            for trade in self._pending_trades:
                assert isinstance(trade, PendingTrade)
                if len(trade.args) == 0:
                    assert trade.open_or_close == "close"
                    self.perform_close_trade(candle.open, candle.date)
                elif len(trade.args) == 2:
                    assert trade.open_or_close == "open"
                    assert not self.in_trade
                    assert trade.args[0] == "Long" or trade.args[0] == "Short" or trade.args[0] == "Hold"
                    if trade.args[0] == "Hold":
                        continue
                    assert isinstance(trade.args[1], float) or isinstance(trade.args[1], int)
                    trade.entry_price = candle.open
                    assert trade.entry_price is not None
                    self.perform_open_trade(trade.args[0], trade.args[1], candle.open, candle.date)
                else:
                    assert False
            self._pending_trades.clear()

    def process_gains(self, candle, action_price):

        # process gains

        if self.liquidated:
            assert not self.in_trade
            derivative_candle = Candle(candle.date, self.total_btc + self.closed_p_and_l(action_price),
                                       self.total_btc + self.closed_p_and_l(action_price),
                                       self.total_btc + self.closed_p_and_l(action_price),
                                       self.total_btc + self.closed_p_and_l(action_price), candle.vol,
                                       idx=len(self.macro_derivative_history))
        else:
            derivative_candle = Candle(candle.date, self.total_btc + self.closed_p_and_l(candle.close),
                                       self.total_btc + self.closed_p_and_l(candle.open),
                                       self.total_btc + self.closed_p_and_l(candle.high),
                                       self.total_btc + self.closed_p_and_l(candle.low), candle.vol,
                                       idx=len(self.macro_derivative_history))

        if self.local_macro_candle_w == 0:
            self.macro_derivative_history.append(derivative_candle)
        else:
            self.macro_derivative_history[-1].close = derivative_candle.close
            self.macro_derivative_history[-1].high = max(self.macro_derivative_history[-1].high, derivative_candle.high)
            self.macro_derivative_history[-1].low = min(self.macro_derivative_history[-1].low, derivative_candle.low)
            self.macro_derivative_history[-1].vol += derivative_candle.vol

        self.local_top = max(self.local_top, self.macro_derivative_history[-1].high)

        self.max_drawdown = min(self.macro_derivative_history[-1].low/self.local_top, self.max_drawdown)

        self.macro_derivative_history[-1].max_drawdown = self.max_drawdown

        self.local_macro_candle_w += 1

        assert self.macro_candle_w >= 1
        if self.local_macro_candle_w == self.macro_candle_w:
            self.local_macro_candle_w = 0

        if False:

            current_total_btc = self.total_btc + self.closed_p_and_l(action_price)

            if current_total_btc > self.all_time_high:
                self.all_time_high = current_total_btc
                self.low_since_all_time_high = current_total_btc
                if self.local_biggest_drop < 0:
                    self.biggest_drops_between_all_time_highs.append(
                        self.local_biggest_drop)
                self.local_biggest_drop = 0

            self.low_since_all_time_high = min(self.low_since_all_time_high,
                                               current_total_btc)

            self.local_biggest_drop = min(self.local_biggest_drop,
                                          self.low_since_all_time_high / self.all_time_high - 1)

            self.biggest_drop = min(self.biggest_drop, self.local_biggest_drop)

    def simulate_close_candle(self, candle):
        if self.liquidated:
            self._pending_trades.clear()
            return

        if not self.never_liquidate:
            if self.in_trade:
                assert self.entry_price is not None
                # check if you are getting liquidated
                self.check_is_liquidated_and_if_true_then_liquidate(candle.low, candle.date)
                if not self.liquidated:
                    self.check_is_liquidated_and_if_true_then_liquidate(candle.high, candle.date)
                else:
                    self.process_gains(candle, candle.low)
                    return
                if not self.liquidated:
                    self.check_is_liquidated_and_if_true_then_liquidate(candle.close, candle.date)
                else:
                    self.process_gains(candle, candle.high)
                    return

        self.process_gains(candle, candle.close)

    def append_pending_trades(self, pending_trades):
        self._pending_trades += pending_trades
        self.history_of_trades += pending_trades

    def get_pending_trades(self):
        return self._pending_trades

    def last_trades_to_str(self, history, num_trades):
        ret = ""
        for trade in reversed(self.history_of_trades[max(-num_trades*2, -len(self.history_of_trades)):]):
            assert isinstance(trade, PendingTrade)
            if trade.open_or_close == "open":
                ret += str(trade.get_direction()) + "@[" + str(history[trade.t].date) + ", " + str(trade.entry_price) + "]; "
        return ret



