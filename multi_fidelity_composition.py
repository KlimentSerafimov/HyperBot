import numpy as np
from talib import abstract

from Account import Account
from Bot import Bot
from BotLibrary import BotLibrary
from Grammar import MyIndicatorToFloat, MyIndicatorToBool, MyConstFloat, MyLessThan, MyNot, MyXor
from Indicators import get_all_indicators, get_programs, eval_indicators
from ProtectedQuotes import ProtectedHistory, ProtectedQuotes
from conbase_data_reader import read_history
from metalearning import get_best_bot, get_and_eval_bot_from_program


def make_macro(history, candle_bundle):
    ret = []

    current_candle = None
    num_candles = 0

    for i in range(len(history)):
        if num_candles == 0:
            current_candle = history[i].get_copy()
            num_candles += 1
        elif num_candles < candle_bundle:
            current_candle.update(history[i])
            num_candles += 1
        else:
            ret.append(current_candle)
            current_candle = history[i].get_copy()
            num_candles = 1

    if current_candle is not None:
        ret.append(current_candle)

    # print("len(original_history)", len(history))
    # print("len(macro_history)", len(ret))

    return ret

def multi_fidelity_composition(currency, history, train_p):

    micro_history = history

    base_hist_candle_size = 4

    history = make_macro(micro_history, base_hist_candle_size)

    macro_candle_size = 4

    macro_history = make_macro(history, macro_candle_size)
    # macro_history = history




    if False:
        closes = np.array([candle.close for candle in history])
        btc_rsi_40 = MyIndicatorToFloat("rsi_40",
                            indicator = abstract.Function("RSI", timeperiod=40)(closes))
        btc_rsi_36 =MyIndicatorToFloat("rsi_36",
                            indicator = abstract.Function("RSI", timeperiod=36)(closes))

        not_rsi_40_lt_50 = MyNot(MyLessThan(btc_rsi_40, MyConstFloat(50.04020761608167)))
        rsi_36_lt_35 = MyLessThan(btc_rsi_36, MyConstFloat(35.46419269281007))

        final_xor = MyXor(not_rsi_40_lt_50, rsi_36_lt_35)

        new_currency = "base"

        new_best_bot = get_and_eval_bot_from_program(final_xor, new_currency, history, currency)


        best_bot, new_currency = get_best_bot(
            currency, macro_history, train_p, generations = 2, num_derivatives=2, do_print=True, ret_bot=new_best_bot,
                                              append_programs=get_programs(get_all_indicators("D_" + new_currency,
                                                                                              new_best_bot.account.macro_derivative_history))
                                              )

        print("best_bot.program", best_bot.program)

        assert isinstance(best_bot, Bot)


        return


    if False:

        generations = 2
        covered_list = [x[:-1] for x in open("covered_indicators.txt").readlines()]
        for fun in covered_list:

            init_indicator_set = get_all_indicators(currency, history, fun)
            ret_bot, correlations = eval_indicators(history, currency, get_programs(init_indicator_set), train_p, False,
                                      # ret_bot if idx != 0 else None, generations, None if idx != 0 else ret_bot)
                                      None, generations, None)

            print(fun)
            print(ret_bot.program)
            print(correlations)
            print()

        return

    best_bot, new_currency = get_best_bot(currency, macro_history, train_p, generations=2, num_derivatives=1,
                                          do_print=True)


    indicator = []

    org_t = 0

    for t in range(0, len(macro_history)):
        counter = 0
        while counter < macro_candle_size and org_t < len(history):
            if t == 0:
                if counter < macro_candle_size-1:
                    indicator.append(False)
                else:
                    indicator.append(best_bot.program.eval(t))
            else:
                if counter < macro_candle_size-1:
                    indicator.append(best_bot.program.eval(t-1))
                else:
                    indicator.append(best_bot.program.eval(t))
            org_t += 1
            counter += 1

    best_macro_program = MyIndicatorToBool(new_currency, indicator)

    new_best_bot = get_and_eval_bot_from_program(best_macro_program, "best_macro_program", history, currency)

    assert len(new_best_bot.account.macro_derivative_history) == len(history)


    best_bot, new_currency = get_best_bot(
        currency, history, train_p, generations = 2,
        append_programs=get_programs(get_all_indicators("macro_"+new_currency, new_best_bot.account.macro_derivative_history)),
        ret_bot=new_best_bot, num_derivatives = 1, do_print=True)

    indicator = []

    org_t = 0

    for t in range(0, len(history)):
        counter = 0
        while counter < base_hist_candle_size and org_t < len(micro_history):
            if t == 0:
                if counter < base_hist_candle_size-1:
                    indicator.append(False)
                else:
                    indicator.append(best_bot.program.eval(t))
            else:
                if counter < base_hist_candle_size-1:
                    indicator.append(best_bot.program.eval(t-1))
                else:
                    indicator.append(best_bot.program.eval(t))
            org_t += 1
            counter += 1

    best_macro_program = MyIndicatorToBool(new_currency, indicator)

    new_best_bot = get_and_eval_bot_from_program(best_macro_program, "best_program", micro_history, currency)

    assert len(new_best_bot.account.macro_derivative_history) == len(micro_history)

    best_bot, new_currency = get_best_bot(
        currency, micro_history, train_p, generations=2,
        append_programs=get_programs(
            get_all_indicators("macro_" + new_currency, new_best_bot.account.macro_derivative_history)),
        ret_bot=new_best_bot, num_derivatives=1, do_print=True)


def main():
    currency = "ETH"
    unit_currency = "USD"
    candle_w = 360
    fraction = 0
    history = read_history(currency, candle_w, fraction, unit_currency = unit_currency, update = False)
    # history = history[int(30*len(history))//32:]
    # history = make_macro(history, 4)
    # print("p = 9")
    # multi_fidelity_composition(currency, history, 9/10)
    print("p = 9")
    multi_fidelity_composition(currency, history, 9.5/10)
    # print("p = 9.75")
    # multi_fidelity_composition(currency, history, 9.75/10)

main()