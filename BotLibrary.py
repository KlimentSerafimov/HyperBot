import math

import gc

import matplotlib.pyplot as plt

from Bot import Bot

def get_count_table(othr_hist, focus_hist, max_t):
    if_focus_then_next = [[0, 0], [0, 0]]

    focus_idx = 0
    othr_idx = 0

    init_t = 0

    prev_othr_dir = None
    prev_focus_dir = None

    bits_othr = []
    bits_focus = []

    while True:

        both_at_end = True
        if focus_idx >= len(focus_hist):
            focus_t = max_t
        else:
            focus_t = focus_hist[focus_idx].t
            both_at_end = False

        if othr_idx >= len(othr_hist):
            othr_t = max_t
        else:
            othr_t = othr_hist[othr_idx].t
            both_at_end = False

        at_t = min(focus_t, othr_t)
        # print(focus_t, othr_t, prev_focus_dir, prev_othr_dir, at_t, init_t)
        if prev_focus_dir is not None and prev_othr_dir is not None:
            focus_dir_id = 1 if prev_focus_dir == "Long" else 0
            othr_dir_id = 1 if prev_othr_dir == "Long" else 0
            for _ in range(at_t - init_t):
                bits_othr.append(othr_dir_id)
                bits_focus.append(focus_dir_id)
            if_focus_then_next[focus_dir_id][othr_dir_id] += at_t - init_t
        init_t = at_t

        if init_t == max_t:
            if not both_at_end:
                print(init_t, max_t)
                print(focus_idx)
                print(othr_idx)
                print([x for x in enumerate(focus_hist)])
                print([x for x in enumerate(othr_hist)])
            assert both_at_end
            break
        if both_at_end:
            assert False

        if focus_t < othr_t:
            prev_focus_dir = focus_hist[focus_idx].get_direction()
            focus_idx += 1
            if focus_idx < len(focus_hist):
                assert focus_hist[focus_idx].open_or_close == "close"
                focus_idx += 1
                if focus_idx < len(focus_hist):
                    assert focus_hist[focus_idx].open_or_close == "open"
        elif focus_t > othr_t:
            prev_othr_dir = othr_hist[othr_idx].get_direction()
            othr_idx += 1
            if othr_idx < len(othr_hist):
                assert othr_hist[othr_idx].open_or_close == "close"
                othr_idx += 1
                if othr_idx < len(othr_hist):
                    assert othr_hist[othr_idx].open_or_close == "open"
        else:
            prev_othr_dir = othr_hist[othr_idx].get_direction()
            prev_focus_dir = focus_hist[focus_idx].get_direction()
            assert focus_t == othr_t
            focus_idx += 1
            if focus_idx < len(focus_hist):
                assert focus_hist[focus_idx].open_or_close == "close"
                focus_idx += 1
                if focus_idx < len(focus_hist):
                    assert focus_hist[focus_idx].open_or_close == "open"
            othr_idx += 1
            if othr_idx < len(othr_hist):
                assert othr_hist[othr_idx].open_or_close == "close"
                othr_idx += 1
                if othr_idx < len(othr_hist):
                    assert othr_hist[othr_idx].open_or_close == "open"

    return if_focus_then_next, bits_focus, bits_othr

from sklearn import metrics

def get_mutual_information(othr_hist, focus_hist, max_t):

    if_focus_then_next, bits_focus, bits_other = get_count_table(
        othr_hist=othr_hist,
        focus_hist=focus_hist,
        max_t=max_t
    )

    return metrics.normalized_mutual_info_score(bits_focus, bits_other)

    parts = []
    for row_id in range(2):
        for col_id in range(2):
            parts.append(if_focus_then_next[row_id][col_id])

    total_sum = sum(parts)

    if total_sum == 0:
        return None

    pxy = []
    for x in range(2):
        pxy.append([])
        for y in range(2):
            pxy[x].append(if_focus_then_next[x][y] / total_sum)

    px = []
    for x in range(2):
        px.append(sum(if_focus_then_next[x]) / total_sum)

    py = []
    for y in range(2):
        py.append((if_focus_then_next[0][y] + if_focus_then_next[1][y]) / total_sum)

    ixy = 0
    for x in range(2):
        for y in range(2):
            ixy -= math.inf if pxy[x][y] == 0 else pxy[x][y] * math.log2(pxy[x][y] / (px[x] * py[y]))

    entropy = ixy

    return entropy


class BotLibrary:
    def __init__(self):
        self.bots = {}

    def __iter__(self):
        for bot_name in self.bots:
            yield self.bots[bot_name]

    def add_bot(self, bot):
        # if bot.name in self.bots:
        #     return
        assert bot.name not in self.bots
        self.bots[bot.name] = bot
        assert isinstance(self.bots[bot.name], Bot)

    def new_t(self, t):
        for bot_name in self.bots:
            self.bots[bot_name].new_t(t)

    def get_differentiated_frontier(self, history, cutoff, max_ret_size, training_refix_p, plot, consider_top_bots, do_print=True):

        max_t = len(history)-1
        prefix_p = training_refix_p
        prefix_t = math.floor(prefix_p*max_t)
        bot_to_score = {}
        sorted_bots = []
        for bot_name, bot in self.bots.items():
            if bot.account.liquidated:
                continue
            assert isinstance(bot, Bot)
            prefix_gain = bot.account.prefix_gain(prefix_p)
            max_drawdown = bot.account.prefix_max_drawdown(prefix_p)
            score = prefix_gain*max_drawdown
            test_gain = bot.account.total_gain()/prefix_gain
            sorted_bots.append((score, test_gain, bot_name))
            bot_to_score[bot_name] = [math.nan, score, test_gain]
            #
            # self.bots[bot_name].account.plot(bot_name, plot)


        sorted_bots = [x for x in reversed(sorted(sorted_bots))]


        # best_bot = self.bots[sorted_bots[0][2]]
        # for score, test, bot in sorted_bots:
        #
        #     bot = self.bots[bot]
        #     entropy = get_mutual_information(
        #         othr_hist=[trade for trade in bot.account.history_of_trades if trade.t <= prefix_t],
        #         focus_hist=[trade for trade in best_bot.account.history_of_trades if trade.t <= prefix_t],
        #         max_t=prefix_t + 1
        #     )
        # #     print(entropy, score, test, bot.name)
        #     print([(1, x.t) if x.args[0] == "Long" else (0, x.t) for x in bot.account.history_of_trades if x.open_or_close == "open"])
        # #
        # assert False

        plot_min = math.inf
        plot_max = -math.inf
        plot_num_bots = 3
        train_test_scores = []

        new_ordering = []

        num_plotted = 0
        ret_bots = []

        for idx, (score, test_gain, bot_name) in enumerate(sorted_bots):
            bot = self.bots[bot_name]
            add = True

            if do_print:
                print(idx, "/", len(sorted_bots), score, test_gain, bot.name, "len(ret_bots)", len(ret_bots), end = "")

            max_mi = -math.inf
            for other_bot in ret_bots:
                assert isinstance(other_bot, Bot)
                entropy = get_mutual_information(
                    othr_hist=[trade for trade in other_bot.account.history_of_trades if trade.t <= prefix_t],
                    focus_hist=[trade for trade in bot.account.history_of_trades if trade.t <= prefix_t],
                    max_t=prefix_t+1)
                max_mi = max(max_mi, entropy)
                if max_mi > cutoff:
                    add = False
                    break
                # if entropy > cutoff:
                #     add = False
                #     break

            if do_print:
                print(" min_mutual_information", max_mi)
            if add:
                if do_print:
                    print("add")
                new_score = score*(1-max_mi)*(1-max_mi)#*(1-max_mi)
                new_ordering.append((new_score, score, test_gain, bot.name))
                bot_to_score[bot.name][0] = new_score
                ret_bots.append(bot)
                # train_test_scores.append((score, test_gain))
                # if len(ret_bots) >= max_ret_size:
                #     break
            if len(ret_bots) >= consider_top_bots:
                break

        new_ordering = [x for x in reversed(sorted(new_ordering))]

        ret_bots = []
        for idx in range(len(new_ordering)):
            score, score_2, test_gain, bot_name = new_ordering[idx]
            ret_bots.append(self.bots[bot_name])
            train_test_scores.append((score, score_2,  test_gain))

            if len(ret_bots) >= max_ret_size:
                break

        if do_print:
            if do_print:
                print("RET")
                print("len(ret_bots)", len(ret_bots))
            for bot in ret_bots:
                if do_print:
                    print(bot_to_score[bot.name], bot.name, bot.account.last_trades_to_str(history, 8))
                num_plotted += 1
                if num_plotted <= plot_num_bots:
                    if do_print:
                        bot.account.plot("best_#" + str(num_plotted), plot)
                        plot_min = min(plot_min, bot.account.get_min())
                        plot_max = max(plot_max, bot.account.get_max())
                        if num_plotted == plot_num_bots:
                            plot.vlines([bot.account.macro_derivative_history[prefix_t // bot.account.macro_candle_w].date],
                                        plot_min,
                                        plot_max, linestyles="dashed", colors="black")
                # print([(1, x.t) if x.args[0] == "Long" else (0, x.t) for x in bot.account.history_of_trades if x.open_or_close == "open"])
            if do_print:
                print("DONE RET")

        return ret_bots, train_test_scores

    def __len__(self):
        return len(self.bots)

    def clear(self):
        for bot in self.bots:
            self.bots[bot].clear()
        del self.bots
        # gc.collect()


