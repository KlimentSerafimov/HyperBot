import numpy as np
from talib import abstract

from Account import Account
from Bot import Bot
from BotLibrary import BotLibrary
from Environment import Environment
from Grammar import MyIndicatorToFloat, MyConstFloat, MyLessThan, MyNot
from ProtectedQuotes import ProtectedQuotes, ProtectedHistory
from conbase_data_reader import read_history


def main():

    currency = "BTC"
    candle_w = 1440
    fraction = 0
    history = read_history(currency, candle_w, fraction)

    closes = np.array([candle.close for candle in history])

    fun = "RSI"
    rsi_raw = abstract.Function(fun, timeperiod=5)(closes)

    rsi_indicator = MyIndicatorToFloat(fun, rsi_raw)
    my_const = MyConstFloat(64.09932549479646)

    program = MyNot(MyLessThan(rsi_indicator, my_const))

    bot = Bot(program, str(program), Account({currency: 1}, 1))

    bot_library = BotLibrary()
    bot_library.add_bot(bot)

    env = Environment(ProtectedQuotes({currency: ProtectedHistory(history)}), bot_library)
    env.run(do_print=True)

    assert isinstance(bot, Bot)
    print(bot.name, "\n", bot.account.last_trades_to_str(history, 10))

main()

