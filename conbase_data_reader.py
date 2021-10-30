from datetime import datetime

import cbpro
import numpy as np
import pandas as pd

from Candle import Candle

public_client = cbpro.PublicClient()


def to_date(in_cpu_secs):
    return pd.Timestamp(pd.to_datetime(in_cpu_secs, unit='s'))


# for row in ret:
#     print(to_date(row[0]), row)

# date = pd.Timestamp(year=1970, month=1, day=1, minute=0)
# next_date = pd.Timestamp(year=1970, month=1, day=1, minute=1)
# delta_granularity = next_date - date

def download_history(currency, base_currency, candle_w):
    rets = []

    w_min = candle_w

    granularity = w_min*60

    ret = public_client.get_product_historic_rates(currency+"-"+base_currency, granularity=granularity)
    delta_granularity = to_date(ret[0][0])-to_date(ret[1][0])
    batch_delta = to_date(ret[0][0])-to_date(ret[len(ret)-1][0])

    history = []

    file = open("input_files/"+""+currency+"-"+base_currency+"_"+str(int(granularity/60)), "w")

    while True:
        rets.append(ret)

        for idx, row in enumerate(ret):
            # row = ['unix', 'low', 'high', 'open', 'close', 'volume']
            # Candle(date, price, open_price, high, low, vol, change)
            new_candle = Candle(to_date(row[0]), row[4], row[3], row[2], row[1], row[5])

            if len(history) >= 1:
                while history[-1].date - np.timedelta64(w_min, "m") != new_candle.date:
                    new_date = history[-1].date - np.timedelta64(w_min, "m")
                    missing_candle = Candle(new_date, new_candle.close, new_candle.close, new_candle.close, new_candle.close, 0)
                    assert history[-1].date - np.timedelta64(w_min, "m") == missing_candle.date
                    file.write(str(missing_candle)+"\n")
                    history.append(missing_candle)

            history.append(new_candle)

            file.write(str(new_candle)+"\n")

        end_date = to_date(ret[0][0])
        start_date = to_date(ret[len(ret) - 1][0])

        print("ret id", len(rets))
        print("len(ret)", len(ret))
        print(start_date)
        print(end_date)
        print()

        ret = public_client.get_product_historic_rates(
            currency+"-"+base_currency, granularity=granularity, start=start_date - batch_delta - delta_granularity,
            end=start_date - delta_granularity)

        if len(ret) == 0:
            print("BREAK")
            break

    file.close()

def str_to_datetime(date):
    return datetime.strptime(date, '%Y-%m-%d %H:%M:%S')


def read_history(currency, candle_w, fraction, unit_currency = "USD", update = False):
    if update:
        download_history(currency, unit_currency, candle_w)

    if fraction == 0:
        history = read_history_old(currency + "-" + unit_currency + "_" + str(candle_w))
    else:
        assert False
        history = read_history_old(currency + "-" + unit_currency + "_" + str(candle_w) + "_fraction_" + str(fraction))

    return history


def read_history_old(name, do_print=True):


    history = []
    file = open("input_files/"+name)
    lines = file.readlines()
    lines = [x for x in reversed(lines)]
    file.close()

    if do_print:
        print("reading", file.name, "len(lines)", len(lines))
    prev_p = 0
    for idx, line in enumerate(lines):
        p = 100*idx/len(lines)
        if p//10 > prev_p:
            prev_p = p//10
            p_done = str(p)
            p_done = p_done[:min(4, len(p_done))]
            if do_print:
                print("reading row", p_done + "%", "; line", line, end = "")
        row = line.split(" ")
        date = row[0] + " " + row[1]
        candle = Candle(str_to_datetime(date), float(row[2]), float(row[3]), float(row[4]), float(row[5]),
                        float(row[6]), idx=idx)
        history.append(candle)
    if do_print:
        print("done reading", file.name)
        print()
    return history