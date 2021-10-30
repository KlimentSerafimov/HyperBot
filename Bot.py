from Account import Account
import gc

class Bot:
    def __init__(self, program, name, account):
        assert isinstance(account, Account)
        self.program = program
        self.seed_program = None
        self.account = account
        self.name = name

    def new_t(self, t):
        rez = self.program.eval(t)
        if self.account.in_trade:
            if rez:
                # Long
                if self.account.direction == "Long":
                    pass
                elif self.account.direction == "Short":
                    self.account.close_trade(t)
                    self.account.open_trade("Long", 1, t)
                else:
                    assert False
            elif not rez:
                # Short
                if self.account.direction == "Long":
                    self.account.close_trade(t)
                    self.account.open_trade("Short", 1, t)
                elif self.account.direction == "Short":
                    pass
                else:
                    assert False
        else:
            if rez:
                # Long
                self.account.open_trade("Long", 1, t)
            elif not rez:
                # Short
                self.account.open_trade("Short", 1, t)
                pass
            else:
                assert False

    def clear(self):
        self.account.clear()
        del self.account
        # gc.collect()

