import time

from Candle import Candle
from Grammar import MyConstBool, MyIfToBool, MyNot
from helpers import trunk


class Trade:
    def __init__(self):
        self.open_or_close = None
        self.currency = None
        self.amount = None


class Exchange:
    def __init__(self, protected_quotes):
        self.t = 0

        self.protected_quotes = protected_quotes

        self.accounts = {}

    def add_bot(self, bot_name, account):
        assert bot_name not in self.accounts
        self.accounts[bot_name] = account

    def bot_action(self, bot_name, trade):
        self.accounts[bot_name].simulate_close(trade, self.protected_quotes)

    def get_quotes(self):
        return self.protected_quotes

    def next_timestep(self):
        self.t += 1
        for acc_name in self.accounts:
            self.accounts[acc_name].simulate_open(self.protected_quotes)

    def simulate_open_candle(self, candle):
        for bot_name in self.accounts:
            self.accounts[bot_name].simulate_open_candle(candle)

    def simulate_close_candle(self, candle):
        for bot_name in self.accounts:
            self.accounts[bot_name].simulate_close_candle(candle)


print_verbose = 0


class Environment:
    def __init__(self, protected_quotes, bot_library, derivative_program = None, splitter_program = None):

        self.protected_quotes = protected_quotes
        self.save_runs = False
        self.derivative_program = derivative_program
        self.splitter_program = splitter_program

        if self.save_runs:
            print("provide_name")
            assert False
            self.experiment_name = ""
            if not os.path.exists(self.experiment_name):
                mkdir(self.experiment_name)
            else:
                idx = 1
                while os.path.exists(self.experiment_name + "_try" + str(idx)):
                    idx += 1
                self.experiment_name = self.experiment_name + "_try" + str(idx)
                mkdir(self.experiment_name)

        self.currencies = self.protected_quotes.get_currencies()
        assert len(self.currencies) == 1
        self.base_currency = self.currencies[0]
        self.protected_history = self.protected_quotes[self.base_currency]

        self.exchange = Exchange(self.protected_quotes)

        self.bot_library = bot_library

        for bot in self.bot_library:
            bot.seed_program = bot.program

        if derivative_program is not None:
            assert splitter_program is None

            for bot in self.bot_library:
                bot.program = \
                    MyIfToBool(
                        bot.program,
                        derivative_program,
                        MyNot(derivative_program)
                    )
        if splitter_program is not None:
            for bot in self.bot_library:
                bot.program = \
                    MyIfToBool(
                        splitter_program,
                        MyConstBool(False),
                        bot.program
                    )

        for bot_name in self.bot_library.bots:
            self.exchange.add_bot(bot_name, self.bot_library.bots[bot_name].account)

    def run(self, do_print = True):
        start_time = time.time()
        quotes = self.exchange.get_quotes()
        prev_s_per_candle = []

        init_t = 0
        end_t = self.protected_history.protected_len()
        training_prev_s_per_candle = max(1, end_t//20)
        num_prints = 10

        if do_print:
            print("START RUN")
            print("len(self.protected_quotes)", self.protected_history.protected_len())
            print("len(self.bot_library.bots)", len(self.bot_library.bots))

        while not quotes.empty():
            candle = self.protected_history.get_current_candle()

            time_elapsed = (time.time() - start_time)
            s_per_candle = (time.time() - start_time) / (quotes.get_t() - init_t + 1)
            if training_prev_s_per_candle < len(prev_s_per_candle):
                delta_s_per_candle_per_candle = (s_per_candle - prev_s_per_candle[-training_prev_s_per_candle - 1]) / training_prev_s_per_candle
            elif len(prev_s_per_candle) >= 1:
                delta_s_per_candle_per_candle = (s_per_candle - prev_s_per_candle[0]) / len(prev_s_per_candle)
            else:
                delta_s_per_candle_per_candle = None
            prev_s_per_candle.append(s_per_candle)
            num_candles_remaining = (end_t - self.protected_history.get_t())
            remaining = s_per_candle * num_candles_remaining + (
                num_candles_remaining * num_candles_remaining * delta_s_per_candle_per_candle / 2 if delta_s_per_candle_per_candle is not None else 0)
            if quotes.get_t() % ((end_t - init_t) // num_prints) == 0:
                if do_print:
                    print(
                        self.protected_history.get_t() + 1, "/", self.protected_history.protected_len(), " | ",
                        candle.date, " |",
                        # " s/cnd", trunk(s_per_candle, 2),
                        # " d_s/cnd/cnd", trunk(delta_s_per_candle_per_candle, 5),
                        " estimate_of_total", trunk(remaining + time_elapsed, 2),
                        " time_elapsed", trunk(time_elapsed, 2),
                        " remaining", trunk(remaining, 2)
                    )

            self.exchange.simulate_open_candle(candle)  # take trade decided from the previous timestep.
            self.bot_library.new_t(self.protected_history.get_t())  # give close and calcualte trade to take on the next timestep
            self.exchange.simulate_close_candle(candle)  # process closing price, don't take a trade.
            quotes.next_timestep()


        if self.save_runs:
            self.bot_library.save_runs(self.experiment_name)

        if do_print:
            print("END RUN")
            print()