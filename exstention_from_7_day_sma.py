import math

import matplotlib.pyplot as plt
import numpy as np
from talib import abstract

from Account import Account
from Bot import Bot
from BotLibrary import BotLibrary
from Environment import Environment
from Indicators import get_all_indicators, eval_indicators,  get_programs
from ProtectedQuotes import ProtectedQuotes, ProtectedHistory
from conbase_data_reader import read_history


def plot_timeseries(dates, timeseries, plot, title):
    x = []
    y = []

    for idx, (date, val) in enumerate(zip(dates, timeseries)):
        x.append(date)
        y.append(val)


    plot.plot(x, y, label=title)
    plot.legend()


def get_segments():
    currency = "BTC"
    candle_w = 60
    fraction = 0
    history = read_history(currency, candle_w, fraction)
    # history = history[-2000:]
    train_p = 0
    history = history[math.floor(len(history) * train_p):]

    dates = [candle.date for candle in history]

    closes = np.array([candle.close for candle in history])
    sma_7_day = np.array([(price-sma)/price for sma, price
                          in zip(list(abstract.Function("SMA", timeperiod=130)(closes)), list(closes))])

    plot = plt.subplot()
    # plot_timeseries(dates, sma_7_day, plot, "7_day_sma")
    # plot_timeseries(dates, closes, plot, "7_day_sma")
    # plot.set_yscale("log")
    # plt.show()

    num_days_above = 0

    days_above_arr = []
    days_above_end = []

    for x, price in zip(sma_7_day, closes):
        print(x, price)
        if x > 0:
            num_days_above += 1
        else:
            if len(days_above_end) >= 1:
                days_above_end[-1] = num_days_above
            num_days_above = 0

        days_above_end.append(0)
        days_above_arr.append(num_days_above)

    days_above_end[-1] = num_days_above

    plot = plt.subplot()
    plot_timeseries(dates, days_above_arr, plot, "num_days_above_7_day_sma")
    # plot_timeseries(dates, days_above_end, plot, "end")
    plt.show()

    num_times_num_days_above_x = []

    max_num_days_range = [x for x in range(0, max(days_above_end)+1)]
    for x in max_num_days_range:
        count = 0
        for num_days_above in days_above_end:
            if num_days_above >= x:
                count+=1
        num_times_num_days_above_x.append(count)

    plot_past = 24
    plot = plt.subplot()
    plot_timeseries(max_num_days_range[plot_past:], [x/100 for x in num_times_num_days_above_x[plot_past:]], plot, "count")
    # plt.show()

    num_days_plus = 3
    prob_plus_1_day = []
    for x in range(len(num_times_num_days_above_x)):
        if x + num_days_plus < len(num_times_num_days_above_x) and num_times_num_days_above_x[x] >= 1:
            prob_plus_1_day.append(num_times_num_days_above_x[x + num_days_plus] / num_times_num_days_above_x[x] )
            print(num_times_num_days_above_x[x + num_days_plus] / num_times_num_days_above_x[x] )

    plot = plt.subplot()
    plot.vlines([days_above_end[-1]],
                0,
                1, linestyles="dashed", colors="black")

    plot_timeseries([x for x in range(len(prob_plus_1_day))], prob_plus_1_day, plot, "prob_plus_" + str(num_days_plus) +"_day")
    plt.show()

    data = []

    cutoff = 400
    after = 3*25
    for idx, x in enumerate(days_above_end):
        if x > cutoff:
            print(idx-x, idx)
            data.append((
                history[idx-x:idx+after],
                sma_7_day[idx-x:idx+after]  )
            )

    plot = plt.subplot()
    for idx, (extension, _) in enumerate(data):
        plot_timeseries([candle.date for candle in extension], [candle.close for candle in extension], plot, "ext_" + str(idx))

    plot.set_yscale("log")
    plt.show()

    plot = plt.subplot()
    for idx, (price_segment, sma_segment) in enumerate(data):
        plot = plt.subplot()
        plot_timeseries([x for x in range(len(price_segment))], sma_segment, plot,
                        "ext_" + str(idx))
        plot_timeseries([x for x in range(len(price_segment))], [candle.close/price_segment[0].open-1 for candle in price_segment], plot,
                        "ext_" + str(idx))
        plt.show()
    plt.show()

    return [x for x, _ in data]


def main():
    data = get_segments()



    currency = "BTC"
    candle_w = 60
    fraction = 0
    history = read_history(currency, candle_w, fraction)
    # history = history[-2000:]
    train_p = 0
    history = history[math.floor(len(history) * train_p):]

    macro_candle_size = 1
    for segment in data:

        granular_segment = []

        for x in history:
            if segment[0].date <= x.date < segment[-1].date:
                granular_segment.append(x)

        segment = granular_segment

        init_indicator_set = get_all_indicators(currency, segment)

        ret_bot, _ = eval_indicators(segment, currency, get_programs(init_indicator_set), 0.99, True, None)

get_segments()

