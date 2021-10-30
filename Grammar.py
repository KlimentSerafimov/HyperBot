
"""

program: price history -> buy/sell signal

primitives:
    {indicator(params<indicator>)}, <, const float
    and, or, not, if

    indicator(params<indicator>): history -> float

    <: float, float -> bool
    const_float: void -> float
    const_bool: void -> bool
    and: bool, bool -> bool
    or: bool, bool -> bool
    not: bool -> bool
    if_to_float: bool, float, float -> float
    if_to_bool: bool, float, float -> float

"""


class MyType:
    def __init__(self):
        pass

    def eval(self, state):
        assert False

    def __str__(self):
        assert False

    def __repr__(self):
        return str(self)

    def __lt__(self, other):
        return self.size() < other.size()

    def size(self):
        assert False

class MyBool(MyType):
    def __init__(self):
        super().__init__()
        self.out_type = bool

    def eval(self, state):
        assert False


class MyConstBool(MyBool):
    def __init__(self, op):
        super().__init__()
        assert isinstance(op, bool)
        self.op = op

    def eval(self, state):
        return self.op

    def size(self):
        return 1

    def __str__(self):
        return str(self.op)


class MyBinaryBool(MyBool):
    def __init__(self, op_name, op0, op1):
        super().__init__()
        assert op0.out_type == bool
        assert op1.out_type == bool
        self.op_name = op_name
        self.op0 = op0
        self.op1 = op1

    def eval(self, state):
        assert False

    def __str__(self):
        return self.op_name + "(" + str(self.op0) + "," + str(self.op1) + ")"

    def size(self):
        return self.op0.size() + self.op1.size( ) +1


class MyAnd(MyBinaryBool):
    def __init__(self, op0, op1):
        super().__init__("and", op0, op1)

    def eval(self, state):
        return self.op0.eval(state) and self.op1.eval(state)


class MyOr(MyBinaryBool):
    def __init__(self, op0, op1):
        super().__init__("or", op0, op1)

    def eval(self, state):
        return self.op0.eval(state) or self.op1.eval(state)


class MyXor(MyBinaryBool):
    def __init__(self, op0, op1):
        super().__init__("xor", op0, op1)

    def eval(self, state):
        return self.op0.eval(state) != self.op1.eval(state)


class MyImplication(MyBinaryBool):
    def __init__(self, op0, op1):
        super().__init__("=>", op0, op1)

    def eval(self, state):
        return self.op1.eval(state) if self.op0.eval(state) else True


class MyNot(MyBool):
    def __init__(self, op):
        super().__init__()
        assert op.out_type == bool
        self.op = op

    def eval(self, state):
        return not self.op.eval(state)

    def __str__(self):
        return "not( " +str(self.op ) +")"

    def size(self):
        return self.op.size() + 1


class MyFloat(MyType):
    def __init__(self):
        super().__init__()
        self.out_type = float

    def eval(self, state):
        assert False


class MyConstFloat(MyFloat):
    def __init__(self, op):
        super().__init__()
        assert isinstance(op, float)
        self.op = op

    def eval(self, state):
        return self.op

    def __str__(self):
        return str(self.op)

    def size(self):
        return 1


class MyBinaryComparison(MyBool):
    def __init__(self, op0, op1):
        super().__init__()
        assert op0.out_type == float
        assert op1.out_type == float
        self.op0 = op0
        self.op1 = op1

    def eval(self, state):
        assert False

    def size(self):
        return self.op0.size() + self.op1.size() + 1


class MyLessThan(MyBinaryComparison):
    def __init__(self, op0, op1):
        super().__init__(op0, op1)

    def eval(self, state):
        return self.op0.eval(state) < self.op1.eval(state)

    def __str__(self):
        return str(self.op0) + " < " + str(self.op1)


class MyIf(MyType):
    def __init__(self, cond, if_true_body, if_false_body):
        super().__init__()
        assert isinstance(cond, MyBool)
        assert if_true_body.out_type == if_false_body.out_type
        assert hasattr(if_true_body, "eval")
        assert hasattr(if_false_body, "eval")

        self.cond = cond
        self.if_true_body = if_true_body
        self.if_false_body = if_false_body

    def eval(self, state):
        if self.cond.eval(state):
            return self.if_true_body.eval(state)
        else:
            return self.if_false_body.eval(state)

    def __str__(self):
        return "if(" + str(self.cond) + ") { " + str(self.if_true_body) + "} else {" + str(self.if_false_body) + "}"

    def size(self):
        return self.cond.size() + self.if_true_body.size() + self.if_false_body.size() + 1


class MyIfToFloat(MyIf, MyFloat):
    def __init__(self, cond, if_true_body, if_false_body):
        assert isinstance(if_true_body, MyFloat)
        assert isinstance(if_false_body, MyFloat)
        MyIf.__init__(self, cond, if_true_body, if_false_body)
        MyFloat.__init__(self)


class MyIfToBool(MyIf, MyBool):
    def __init__(self, cond, if_true_body, if_false_body):
        assert isinstance(if_true_body, MyBool)
        assert isinstance(if_false_body, MyBool)
        MyIf.__init__(self, cond, if_true_body, if_false_body)
        MyBool.__init__(self)


class MyIndicatorToFloat(MyFloat):
    def __init__(self, name, indicator):
        super().__init__()
        self.name = name
        self.indicator = indicator

    def eval(self, state):
        # print(state, self.indicator[state])
        return self.indicator[state]

    def __str__(self):
        return self.name

    def size(self):
        return 1


class MyIndicatorToBool(MyBool):
    def __init__(self, name, indicator):
        super().__init__()
        self.name = name
        self.indicator = indicator

    def eval(self, state):
        return self.indicator[state]

    def __str__(self):
        return self.name

    def size(self):
        return 1
