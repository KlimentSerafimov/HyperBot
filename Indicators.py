import math

import numpy as np
from talib import abstract

from Account import Account
from Bot import Bot
from BotLibrary import BotLibrary
from Environment import Environment
from Grammar import MyConstFloat, MyIndicatorToFloat, MyLessThan, MyNot, MyAnd, MyOr, MyXor, MyIfToBool, MyImplication, MyConstBool
from ProtectedQuotes import ProtectedQuotes, ProtectedHistory
from copy import deepcopy


import matplotlib.pyplot as plt


class Indicator:
    def __init__(self, name, data):
        self.name = name
        self.data = data


def get_all_indicators(name, history, only_indicator = None):
    covered_list = [x[:-1] for x in open("curated_indicators_5.txt").readlines()]

    indicators = {}

    closes = np.array([candle.close for candle in history])
    opens = np.array([candle.open for candle in history])
    highs = np.array([candle.high for candle in history])
    lows = np.array([candle.low for candle in history])

    if True:
        for fun in covered_list:
            if only_indicator is not None and fun != only_indicator:
                continue
            custom_timeperiod = True
            # if not custom_timeperiod:
            default_timeperiod = False
            if default_timeperiod:
                try:
                    indicator = abstract.Function(fun)(closes)
                except:
                    try:
                        indicator = abstract.Function(fun)(highs,
                                                           lows)
                    except:
                        try:
                            indicator = abstract.Function(fun)(highs,
                                                               lows,
                                                               closes)
                        except:

                            indicator = abstract.Function(fun)(opens,
                                                               highs,
                                                               lows,
                                                               closes)
                indicators[name+"_"+fun] = indicator
            if custom_timeperiod:
                for t in [int(1.6**x) for x in range(3, 10)]:
                    try:
                        indicator = abstract.Function(fun, timeperiod=t)(closes)
                    except:
                        try:
                            indicator = abstract.Function(fun, timeperiod=t)(highs,
                                                                             lows)
                        except:
                            try:
                                indicator = abstract.Function(fun, timeperiod=t)(highs,
                                                                                 lows,
                                                                                 closes)
                            except:

                                indicator = abstract.Function(fun, timeperiod=t)(opens,
                                                                                 highs,
                                                                                 lows,
                                                                                 closes)

                    indicators[name+"_"+fun +"_" + str(t)] = indicator

    do_relative_rsis = False
    if do_relative_rsis:
        rsi_inds = [x for x in indicators if "RSI" in x]
        for i in range(len(rsi_inds)):
            for j in range(i+1, len(rsi_inds)):
                new_ind = [(rsi1 - rsi0)/rsi0 for rsi0, rsi1 in zip(indicators[rsi_inds[i]], indicators[rsi_inds[j]])]
                indicators[rsi_inds[i]+"_DIFF_"+rsi_inds[j]] = new_ind

    do_dpdt_indicators = False
    if do_dpdt_indicators:
        max_dt_period = 20
        num_dts = 20
        for delta_t_period in [math.floor((1 + x) * max(1.0, (max_dt_period / num_dts))) for x in range(num_dts)]:
            indicator = []
            for candle_idx in range(len(history)):
                if candle_idx >= delta_t_period:
                    indicator.append(history[candle_idx].close / history[candle_idx - delta_t_period].open)
                else:
                    indicator.append(math.nan)
            indicators[name+"_"+"DPDT_" + str(delta_t_period)] = np.array(indicator)

    do_sma_indicators = False
    if do_sma_indicators:
        # adding sma indicator
        max_sma_period = 100
        num_smas = 50
        for period in [math.floor((x + 1) * max(1.0, (max_sma_period / num_smas))) for x in range(num_smas)]:
            indicators[name+"_SMA_" + str(period)] = \
                np.array([(price-sma)/price for sma, price
                          in zip(list(abstract.Function("SMA", timeperiod=period)(closes)), list(closes))])

        do_relative_smas = True
        if do_relative_smas:
            sma_inds = [x for x in indicators if "SMA" in x]
            for i in range(len(sma_inds)):
                for j in range(i + 1, len(sma_inds)):
                    new_ind = [(rsi1 - rsi0) / rsi0 for rsi0, rsi1 in
                               zip(indicators[sma_inds[i]], indicators[sma_inds[j]])]
                    indicators[sma_inds[i] + "_DIFF_" + sma_inds[j]] = new_ind

    return indicators

def get_programs(indicators):

    num_buckets = 50

    min_max = {}
    # print("INDICATORS")
    for fun, indicator in indicators.items():
        filtered = [x for x in indicator if not np.isnan(x)]
        if len(filtered) == 0:
            continue
        indicator_min = min(filtered)
        indicator_max = max(filtered)
        min_max[fun] = indicator_min, indicator_max
        # print(fun, indicator_min, indicator_max, "len", len(indicator))

    # print()

    # new_progs = [MyConstBool(True), MyConstBool(False)]
    new_progs = []

    for fun, indicator in indicators.items():
        if fun not in min_max:
            continue
        delta_f = (min_max[fun][1] - min_max[fun][0])/num_buckets

        for bucket_id in range(num_buckets+1):
            const = MyConstFloat(min_max[fun][0]+delta_f*bucket_id)
            if "SMA" in fun:
                const = MyConstFloat(0.0)
            expr = MyIndicatorToFloat(fun, indicator)
            lt = MyLessThan(expr, const)

            new_progs.append(lt)
            new_progs.append(MyNot(lt))
            if "SMA" in fun:
                break

    return new_progs


def eval_indicators(history, currency, init_programs, training_prefix_p=7 / 8, do_print=False, derivative_bot=None,
                    generations=3, splitter_bot = None):


    derivative_program = None
    derivative_history = None

    splitter_program = None
    splitter_history = None

    if derivative_bot is not None:
        derivative_program = derivative_bot.program
        derivative_history = derivative_bot.account.macro_derivative_history

    if splitter_bot is not None:
        splitter_program = splitter_bot.program
        splitter_history = splitter_bot.account.macro_derivative_history


    cutoff = 0.8
    consider_top_bots = 200
    population_size = 30

    consider_top_bots = min(population_size, consider_top_bots)

    new_progs = init_programs

    # print("PROGRAMS")

    # for prog in new_progs:
    #     print(str(prog))

    bot_library = BotLibrary()

    max_num_candles_in_memory = 10000000

    macro_candle_size = max(1, (len(history) * len(new_progs)) // max_num_candles_in_memory)

    if do_print:
        print("macro_candle_size", macro_candle_size)
        print(macro_candle_size)

    for prog in new_progs:
        if str(prog) not in bot_library.bots:
            bot_library.add_bot(Bot(prog, str(prog), Account({currency: 1}, macro_candle_size)))

    # print("INIT BOTS")
    # for bot in bot_library:
    #     print(bot.name)

    env = Environment(ProtectedQuotes({currency: ProtectedHistory(history)}), bot_library, derivative_program, splitter_program)
    env.run(do_print = do_print)

    best_program = None
    best_test_score = -math.inf

    correlations = []

    ret_bot = None

    for gen_id in range(generations):

        if do_print:
            print("GENERATION", gen_id)

        if do_print:
            plot = plt.subplot()
        else:
            plot = None
        bot_frontier, train_test_scores = bot_library.get_differentiated_frontier(
            history, cutoff, population_size, training_prefix_p, plot, consider_top_bots, do_print)
        if do_print:
            plot.plot([candle.date for candle in history], [candle.close / history[0].open for candle in history], label ="base_price")

            if derivative_history is not None:
                plot.plot([candle.date for candle in derivative_history], [candle.close / derivative_history[0].open for candle in derivative_history],
                          label="derivative_price")

            if splitter_history is not None:
                plot.plot([candle.date for candle in splitter_history],
                          [candle.close / splitter_history[0].open for candle in splitter_history],
                          label="splitter_price")

            plt.legend()
            plt.show()

        corr = np.corrcoef([score for _, score, _ in train_test_scores], [test_gain for _, _, test_gain in train_test_scores])
        if do_print:
            print("gen_id", gen_id, "corr=", corr[0][1], "|population|=", len(bot_frontier))
            for bot, (mi_score, score, test) in [x for x in zip(bot_frontier, train_test_scores)][:min(3, len(bot_frontier))]:
                assert isinstance(bot, Bot)
                print(mi_score, score, test, bot.name, bot.account.last_trades_to_str(history, 8))

        for bot, (mi_score, score, test) in [x for x in zip(bot_frontier, train_test_scores)][
                                            :min(1, len(bot_frontier))]:
            assert isinstance(bot, Bot)
            print(mi_score, score, test, bot.name, bot.account.last_trades_to_str(history, 8))

        ret_bot = deepcopy(bot_frontier[0])

        if len(bot_frontier) >= population_size/2:
            correlations.append(corr[0][1])
        else:
            correlations.append(math.nan)

        bot_library.clear()
        del bot_library
        # gc.collect()

        if gen_id == generations-1:
            break

        bot_library = BotLibrary()

        new_programs = []
        for bot in bot_frontier:
            new_programs.append(bot.seed_program)

        for op0_idx in range(len(bot_frontier)):
            for op1_idx in range(op0_idx+1, len(bot_frontier)):
                _op0 = bot_frontier[op0_idx].seed_program
                _op1 = bot_frontier[op1_idx].seed_program
                for idx, (op0, op1) in enumerate([(_op0, _op1), (_op0, MyNot(_op1)), (MyNot(_op0), _op1)]):
                    and_program = MyAnd(op0, op1)
                    or_prog = MyOr(op0, op1)
                    new_programs.append(and_program)
                    new_programs.append(or_prog)
                    # my_imp = MyImplication(op0, op1)
                    # new_programs.append(my_imp)

                    # splitter_true = MyIfToBool(
                    #     op0,
                    #     op1,
                    #     MyNot(op1)
                    # )
                    # new_programs.append(splitter_true)

                    if idx != 2:
                        xor_prog = MyXor(op0, op1)
                        new_programs.append(xor_prog)

                    # if isinstance(op0, MyIfToBool):
                    #     cond = op0.cond
                    #     cond_and_prog = MyAnd(cond, op1)
                    #     cond_or_prog = MyOr(cond, op1)
                    #     new_programs.append(MyIfToBool(cond_and_prog, op0.if_true_body, op0.if_false_body))
                    #     new_programs.append(MyIfToBool(cond_or_prog, op0.if_true_body, op0.if_false_body))
                    #
                    #     if idx != 2:
                    #         cond_xor_prog = MyXor(cond, op1)
                    #         new_programs.append(MyIfToBool(cond_xor_prog, op0.if_true_body, op0.if_false_body))

        if False:
            sample_in_range = len(bot_frontier)*len(bot_frontier)*len(bot_frontier)//len(new_programs)
            for cond_bot_id in range(len(bot_frontier)):
                for true_bot_id in range(len(bot_frontier)):
                    if cond_bot_id != true_bot_id:
                        for false_bot_id in range(len(bot_frontier)):
                            if cond_bot_id != false_bot_id and true_bot_id != false_bot_id:
                                if random.randint(0, sample_in_range) == 0:
                                    cond_bot = bot_frontier[cond_bot_id]
                                    true_bot = bot_frontier[true_bot_id]
                                    false_bot = bot_frontier[false_bot_id]
                                    assert isinstance(cond_bot, Bot)
                                    assert isinstance(true_bot, Bot)
                                    assert isinstance(false_bot, Bot)
                                    # print(len(second_bot_library), len(bot_library)**3)
                                    if_program = MyIfToBool(cond_bot.seed_program, true_bot.seed_program, false_bot.seed_program)
                                    new_programs.append(if_program)
                                    # print(str(if_program))

        macro_candle_size = max(1, (len(history) * len(new_programs))//max_num_candles_in_memory)
        if do_print:
            print("macro_candle_size", macro_candle_size)
        for prog in new_programs:
            bot_library.add_bot(Bot(prog, str(prog), Account({currency: 1}, macro_candle_size)))

        env = Environment(ProtectedQuotes({currency: ProtectedHistory(history)}), bot_library, derivative_program, splitter_program)
        env.run(do_print = do_print)

    if do_print:
        print("SUBSAMPLE CORRELATIONS")
        for corr in correlations:
            print(corr)
        print("DONE CORR")

    if do_print:
        plot = plt.subplot()
        if len(correlations) == 1:
            plot.scatter([0], correlations)
        else:
            plot.plot(correlations)
        plt.show()

    return ret_bot, correlations
