import math
import random

import matplotlib.pyplot as plt

from Account import Account
from Bot import Bot
from BotLibrary import BotLibrary
from Environment import Environment
from Indicators import get_all_indicators, Indicator, eval_indicators, get_programs
from ProtectedQuotes import ProtectedQuotes, ProtectedHistory
from conbase_data_reader import read_history


def get_and_eval_bot_from_program(program, name, history, currency):
    bot = Bot(program, name, Account({currency: 1}, 1))
    bot_library = BotLibrary()
    bot_library.add_bot(bot)

    env = Environment(ProtectedQuotes({currency: ProtectedHistory(history)}), bot_library)
    env.run(do_print=True)

    # bot.account.plot("what", plt.subplot())
    # plt.show()

    assert not bot.account.liquidated
    assert len(bot.account.macro_derivative_history) == len(history)

    return bot


def eval_program(program, currency, history, init_p, end_p):
    bot = Bot(program, str(program), Account({currency: 1}, 1))
    bot_library = BotLibrary()
    bot_library.add_bot(bot)

    env = Environment(ProtectedQuotes({currency: ProtectedHistory(history)}), bot_library)
    env.run(do_print=False)

    return bot.account.prefix_gain(end_p) / bot.account.prefix_gain(init_p)


class IndicatorSet:
    def __init__(self, as_arr, second_arr=[]):
        self.as_arr = as_arr + second_arr

    def __iter__(self):
        return self.as_arr.__iter__()

    def get_random_subset(self, num_elements):
        random.shuffle(self.as_arr)
        return IndicatorSet(self.as_arr[:num_elements])

    def __len__(self):
        return len(self.as_arr)

    def __lt__(self, other):
        return len(self) < len(other)


def metalearning():
    currency = "BTC"
    candle_w = 360
    fraction = 0
    history = read_history(currency, candle_w, fraction)
    # history = history[len(history)*3//4:]
    train_p = 0.8
    train_history = history[:math.floor(len(history) * train_p)]
    all_indicators = get_all_indicators(currency, history)

    all_indicators = IndicatorSet([Indicator(name, all_indicators[name]) for name in all_indicators])

    bucket_size = math.ceil(len(all_indicators) / 2)

    num_samples = 6

    get_top = 4

    generations = 10

    best_indicator_subset = None
    best_correlation = -math.inf

    init_population = []

    for sample_id in range(num_samples):
        init_population.append(all_indicators.get_random_subset(bucket_size))

    for gen_id in range(generations):

        print("META GENERATION", gen_id)
        print("len(all_indicators)", len(all_indicators))

        sorted_subsets = []
        for idx, subset in enumerate(init_population):
            print("SAMPLE", idx, "/", len(init_population))
            _, correlation = eval_indicators(train_history, currency, get_programs({ind.name: ind.data for ind in subset}),
                                          do_print=False)
            # sorted_subsets.append((best_test_score, best_program.program, indicator_subset))
            # print(best_test_score, "; test_test:", eval_program(best_program.program, currency, history, train_p, 1), best_program.program)
            if not math.isnan(correlation):
                sorted_subsets.append((correlation, subset))

        sorted_subsets = [x for x in reversed(sorted(sorted_subsets))]

        local_correlation = sorted_subsets[0][0]
        if local_correlation > best_correlation:
            best_correlation = local_correlation
            best_indicator_subset = sorted_subsets[0][1]

        init_population = []

        print("META RET")
        for correlation, indicators in sorted_subsets:
            print("correlation", correlation, [indicator.name for indicator in indicators])

        for idx, (correlation, subset) in enumerate(sorted_subsets[:min(get_top, len(sorted_subsets))]):
            for _ in range(3):
                subsubet = subset.get_random_subset(len(subset) - 1)
                init_population.append(subsubet)
            small_parts = []
            for idx2 in range(min(get_top, len(sorted_subsets))):
                if idx2 != idx:
                    for _ in range(3):
                        small_parts.append(
                            sorted_subsets[idx2][1].get_random_subset(math.ceil(len(sorted_subsets[idx2][1]) / 4)))
            random.shuffle(small_parts)
            for small_part in small_parts[:3]:
                supersubset = IndicatorSet(subset.as_arr, small_part.as_arr)
                init_population.append(supersubset)


def get_best_bot(currency, history, train_p, generations, append_programs=None, ret_bot = None, num_derivatives = 1, do_print = False):
    if append_programs is None:
        append_programs = []
    init_indicator_set = get_all_indicators(currency, history)

    # init_indicators_set = IndicatorSet([Indicator(name, init_indicators[name]) for name in init_indicators])

    all_indicators = init_indicator_set

    tp = train_p

    for idx, train_p in enumerate([tp for _ in range(num_derivatives)]):
        if do_print:
            print("DERIV_LVL", idx)


        ret_bot, _ = eval_indicators(history, currency, append_programs + get_programs(all_indicators), train_p, do_print,
                                  # ret_bot if idx != 0 else None, generations, None if idx != 0 else ret_bot)
                                  ret_bot, generations, None)

        ret_bot = get_and_eval_bot_from_program(ret_bot.program, ret_bot.name, history, currency)

        if idx == num_derivatives - 1:
            break

        currency = "D_" + currency

        derv_indicators = get_all_indicators(currency, ret_bot.account.macro_derivative_history)

        all_indicators = {**all_indicators, **derv_indicators}

    return ret_bot, currency


def baselarning():
    currency = "BTC"
    candle_w = 1440
    fraction = 0
    history = read_history(currency, candle_w, fraction)
    # history = history[-1000:]
    train_p = 1
    train_history = history[:math.floor(len(history) * train_p)]
    init_indicator_set = get_all_indicators(currency, history)

    # init_indicators_set = IndicatorSet([Indicator(name, init_indicators[name]) for name in init_indicators])

    all_indicators = init_indicator_set

    ret_bot = None

    tp = 9.5 / 10

    for idx, train_p in enumerate([tp, tp, tp]):
        print("DERIV_LVL", idx)

        ret_bot, _ = eval_indicators(train_history, currency, get_programs(all_indicators), train_p, True, ret_bot)

        currency = "D_" + currency

        derv_indicators = get_all_indicators(currency, ret_bot.account.macro_derivative_history)

        all_indicators = {**all_indicators, **derv_indicators}


# baselarning()
