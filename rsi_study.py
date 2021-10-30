import matplotlib.pyplot as plt

from Grammar import MyLessThan, MyNot, MyConstFloat, MyIndicatorToFloat
from conbase_data_reader import read_history
from metalearning import get_best_bot
from multi_fidelity_composition import make_macro

def get_best_rsi(currency, history, p_train):


    best_bot = get_best_bot(
        currency, history, p_train, generations = 1,
        append_programs=None,
        ret_bot=None, num_derivatives = 1)

    prog = best_bot.program

    is_neg = False

    if isinstance(prog, MyNot):
        prog = prog.op
        is_neg = True

    if isinstance(prog, MyLessThan):
        assert isinstance(prog.op0, MyIndicatorToFloat)
        assert isinstance(prog.op1, MyConstFloat)
        assert prog.op0.name == currency+"_RSI"

        return prog.op1.op * (-1 if is_neg else 1), best_bot.account.total_gain()/best_bot.account.prefix_gain(p_train, True)

def main():

    currency = "BTC"
    candle_w = 60
    fraction = 0
    history = read_history(currency, candle_w, fraction)
    # history = history[3*len(history)//4:]
    macro_candle_size = 1
    candle_w*=macro_candle_size

    macro_history = make_macro(history, macro_candle_size)

    mins_in_day = 1440
    w_days = 120
    inc_days = w_days
    w = w_days*mins_in_day//candle_w
    inc = inc_days*mins_in_day//candle_w

    ret_date = []
    ret_rsi_pos = []
    ret_rsi_neg = []
    ret_gain = []
    cumulative = []

    total_gain = 1

    for init_t in range(0, len(macro_history)-w, inc):
        start_t = 0
        end_t = min(len(macro_history)-1, init_t+w)
        print("[", start_t, ":", end_t, "]", "/", len(macro_history))
        tmp = get_best_rsi(currency, macro_history[start_t:end_t], 1-inc/end_t)
        ret_date.append(macro_history[end_t].date)
        ret_rsi_pos.append(tmp[0] if tmp[0] > 0 else None)
        ret_rsi_neg.append(-tmp[0] if tmp[0] < 0 else None)
        ret_gain.append(tmp[1])
        total_gain*=tmp[1]
        cumulative.append(total_gain)

    plot = plt.subplot()
    # plot.scatter(ret_date, ret_rsi_pos, label="best_rsi_pos")
    # plot.scatter(ret_date, ret_rsi_neg, label="best_rsi_neg")
    # plot.legend()
    # plot.legend()
    # plt.show()
    # plot = plot.twinx()
    plot.plot(ret_date, ret_gain, color = "r", label="ret_gain_of_best_rsi")
    plot.legend()
    plot = plot.twinx()
    plot.plot(ret_date, cumulative, color = "b", label = "total_gain")
    plot.legend()
    plt.show()

main()