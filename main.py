import math
import random
import gc

import matplotlib.pyplot as plt
import numpy as np
import talib
from talib import abstract

from Account import Account
from Bot import Bot
from BotLibrary import BotLibrary
from Environment import Environment
from Grammar import MyLessThan, MyConstFloat, MyIndicatorToFloat, MyNot, MyIf, MyAnd, MyOr, MyIfToBool
from Indicators import get_all_indicators
from ProtectedQuotes import ProtectedHistory, ProtectedQuotes
from conbase_data_reader import read_history


def explore_indicators():
    currency = "BTC"
    candle_w = 1440
    fraction = 0
    history = read_history(currency,candle_w, fraction)

    ignore_list = [x[:-1] for x in open("ignore_indicators.txt").readlines()]
    covered_list = [x[:-1] for x in open("covered_indicators.txt").readlines()]
    # for row in ignore_list:
    #     print(row)

    closes = np.array([candle.close for candle in history])
    opens = np.array([candle.open for candle in history])
    highs = np.array([candle.high for candle in history])
    lows = np.array([candle.low for candle in history])

    local_len = len(talib.get_functions())
    for idx, fun in enumerate(talib.get_functions()):
        if fun in ignore_list or fun in covered_list or fun[:3] == "CDL":
            continue
        print(idx, "/", local_len, fun)

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

                    indicator = abstract.Function(fun)(np.array([candle.open for candle in history]),
                                                       highs,
                                                       lows,
                                                       closes)

        plot = plt.subplot()
        plot.plot(indicator)
        plt.show()
