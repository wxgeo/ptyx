import random
import functools
from collections import namedtuple
from math import gcd
from typing import Callable, Iterable, Sequence, TypeVar

from numpy import array
from ptyx.sys_info import SYMPY_AVAILABLE

from ptyx.config import param


if SYMPY_AVAILABLE:
    S: Callable
    from sympy import S, Integer

    INTEGERS_TYPES: tuple[type, ...] = (int, Integer)
else:

    def S(val):
        return val

    INTEGERS_TYPES = (int,)


# Important note: all the following functions are sandboxed.
# By this, I mean that any external call to random won't affect random state for
# the following functions.

_RANDOM_STATE = random.getstate()
_SANDBOXED_MODE = False
_T = TypeVar("_T")


class Point(namedtuple("Point", ["x", "y"])):
    def __add__(self, vec):
        return Point(self.x + vec[0], self.y + vec[1])

    def __neg__(self):
        return Point(-self.x, -self.y)

    def __sub__(self, vec):
        return Point(self.x - vec[0], self.y - vec[1])

    def __rmul__(self, k):
        return Point(k * self.x, k * self.y)


def _print_state():
    """For debuging purpose."""
    print(29 * "*")
    print("randfunc._RANDOM_STATE value:")
    print(hash(_RANDOM_STATE))
    print(29 * "*")


def sandboxed(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        global _RANDOM_STATE, _SANDBOXED_MODE
        if not _SANDBOXED_MODE:
            old_state = random.getstate()
            random.setstate(_RANDOM_STATE)
            _SANDBOXED_MODE = True
            try:
                val = func(*args, **kw)
            finally:
                _RANDOM_STATE = random.getstate()
                random.setstate(old_state)
                _SANDBOXED_MODE = False
        else:
            val = func(*args, **kw)
        return val

    return wrapper


def set_seed(value):
    global _RANDOM_STATE
    random.seed(value)
    _RANDOM_STATE = random.getstate()


@sandboxed
def randint(a: int = None, b: int = None, exclude: Iterable = ()) -> int:
    """Generate a random integer between `a` and `b`.

    Forbidden values may be specified using `exclude` argument.
    """
    if a is None and b is not None:
        a, b = b, a
    if b is None:
        b = 9 if a is None else a
        a = 2
    assert a is not None and b is not None
    while a in exclude:
        a += 1
        if a > b:
            raise ValueError("Can't statisfy constraints !")
    while b in exclude:
        b -= 1
        if a > b:
            raise ValueError("Can't statisfy constraints !")
    while True:
        val = random.randint(a, b)
        if val not in exclude:
            break
    if param["sympy_is_default"]:
        val = S(val)
    return val


@sandboxed
def srandint(a: int = None, b: int = None, exclude: Iterable = ()) -> int:
    """Generate a random integer between `a` and `b` or between `-b` and `-a`.

    `a` and `b` should be positive integers.
    Forbidden values may be specified using `exclude` argument.
    """
    if a is None and b is None:
        a, b = 2, 9
    elif a is None:
        a = 2
    elif b is None:
        a, b = 2, a
    assert a is not None and b is not None
    # pylint: disable=invalid-unary-operand-type
    while a in exclude and -a in exclude:
        a += 1
        if a > b:
            raise ValueError("Can't statisfy constraints !")
    while b in exclude and -b in exclude:
        b -= 1
        if a > b:
            raise ValueError("Can't statisfy constraints !")
    while True:
        val = (-1) ** random.randint(0, 1) * randint(a, b)
        if val not in exclude:
            return val


@sandboxed
def randsign():
    val = (-1) ** random.randint(0, 1)
    if param["sympy_is_default"]:
        val = S(val)
    return val


@sandboxed
def randbool():
    return bool(randint(0, 1))


@sandboxed
def randpoint(a=None, b=None, exclude=()):
    while True:
        x = randint(a, b)
        y = randint(a, b)
        if (x, y) not in exclude:
            return Point(x, y)


@sandboxed
def srandpoint(a=None, b=None, exclude=()):
    while True:
        x = srandint(a, b)
        y = srandint(a, b)
        if (x, y) not in exclude:
            return Point(x, y)


def is_mult_2_5(val: int | Iterable[int]) -> bool:
    """Test if integer `val` matches 2**n * 5**m.

    `val` may also be a list (or other iterable) of integers,
     in that case all values must match 2**n * 5**m.
    """
    if hasattr(val, "__iter__"):
        return all(is_mult_2_5(v) for v in val)
    if val == 0 or not isinstance(val, INTEGERS_TYPES):
        return False
    while val % 5 == 0:  # type: ignore
        val = val // 5  # type: ignore
    while val % 2 == 0:  # type: ignore
        val = val // 2  # type: ignore
    return val in (1, -1)


@sandboxed
def randfrac(a=None, b=None, exclude=(), not_decimal=False, den=None):
    """Return a random positive fraction which is never an integer.

    By default, numerator and denominators are random integers between `a` and `b`.

    Use `den` to specify denominator value; `den` must be an integer or
    a list of integers.
    """
    if b is None:
        b = 9 if a is None else a
        a = 2
    if hasattr(den, "__iter__"):
        # To allow rando.choice() and multiple iterations.
        den = list(den)
    if (den is None and a in (-1, 0, 1) and b in (-1, 0, 1)) or a == b:
        # This would lead to infinite loop.
        raise ValueError("(%s, %s) are not valid parameters." % (a, b))
    if not_decimal and is_mult_2_5(den):
        raise ValueError("chosen denominator is not compatible with `not_decimal` option.")
    while True:
        if den is None:
            d = randint(a, b)
            if d in (0, 1):
                continue
            n = randint(a, b)
        else:
            n = randint(a, b)
            if hasattr(den, "__iter__"):
                d = random.choice(den)
            else:
                d = den
            if gcd(d, n) not in (-1, 1):
                # XXX this may lead to infinite loop if wrong arguments are passed
                continue
        val = S(n) / S(d)
        if not_decimal and is_mult_2_5(val.q):
            continue
        if not val.is_integer and val not in exclude:
            return val


@sandboxed
def srandfrac(a=None, b=None, exclude=(), not_decimal=False, den=None):
    """Return a random signed fraction which is never an integer.

    Use `den` to specify denominator value; `den` must be an integer or a tuple
    of integers.
    """
    while True:
        val = (-1) ** randint(0, 1) * randfrac(a, b, not_decimal=not_decimal, den=den)
        if val not in exclude:
            return val


@sandboxed
def randchoice(items, *others, **kw):
    """Select randomly an item.

    Note that `randchoice(1, 2, 3)` is equivalent to `randchoice([1, 2, 3])`.
    """
    if others:
        # `items` is then only the first element.
        items = [items] + list(others)
    if kw.get("signed"):
        items = list(items) + [-1 * item for item in items]
    if "exclude" in kw:
        items = [val for val in items if val not in kw["exclude"]]
    val = random.choice(items)
    if isinstance(val, (int, float, complex)):
        val = S(val)
    return val


@sandboxed
def randsample(items: Sequence[_T], k: int) -> list[_T]:
    """Return a random list of k unique elements from `items`.

    Raise `ValueError` if `items` does not contain enough elements."""
    return random.sample(items, k)


@sandboxed
def randpop(list_or_set):
    """Randomely remove an item from list or set and return it."""
    i = random.randint(0, len(list_or_set) - 1)
    if isinstance(list_or_set, list):
        return list_or_set.pop(i)
    elif isinstance(list_or_set, set):
        for j, v in enumerate(list_or_set):
            if i == j:
                list_or_set.remove(v)
                return v
    else:
        raise NotImplementedError


@sandboxed
def srandchoice(*items, **kw):
    kw["signed"] = True
    return randchoice(*items, **kw)


@sandboxed
def shuffle(items: list) -> None:
    random.shuffle(items)


@sandboxed
def randmaketrans(string, _random=None):
    """Shuffle string letters and return a random translation table usable for str.translate()."""
    letters = list(string)
    if len(letters) != len(set(letters)):
        raise ValueError(f"Same letter appears twice in {string!r}.")
    random.shuffle(letters, _random)
    shuffled_string = "".join(letters)
    return str.maketrans(string, shuffled_string)


@sandboxed
def randfloat(a, b, d=5, exclude=()):
    k = 10**d
    exclude = {int(round(v * k)) for v in exclude}
    while True:
        n = randint(int(round(a * k)) + 1, int(round(b * k)) - 1)
        if n not in exclude:
            return float(n / k)


@sandboxed
def srandfloat(a, b, d=5, exclude=()):
    return float(randsign()) * randfloat(a, b, d, exclude)


@sandboxed
def randmatrix(size=(3, 3), rank=None, unique=False, func=srandint, **kw):
    """Return a matrix of dimensions `size` (number of lines, number of columns).

    `func` is used to build the random values, and **kw are passed to it.
    Be careful with `rank`, as it may induce infinite recursion if
    condition can't be satisfied.

    Set `unique` to True if each coefficient must be unique.
    Note that you can't specify rank then.
    """
    from sympy import Matrix

    if rank is None:
        m, n = size
        return Matrix(m, n, many(m * n, func=func, unique=unique, **kw))
    elif unique:
        raise NotImplementedError("You can't specify rank if you set unique=True.")
    elif rank > min(size):
        raise ValueError("Matrix rank can't exceed lines nor columns number.")
    else:
        while True:
            # noinspection PyUnusedLocal
            matrix = [[func(**kw) for j in range(size[1])] for i in range(rank)]
            if Matrix(matrix).rank() == rank:
                break
        while len(matrix) < size[0]:
            matrix.append(list(sum(srandint() * array(line) for line in matrix)))
    return Matrix(matrix)


def many(n=2, func=srandint, unique=True, **kw):
    """Return several numbers at once.

    By default, every number is unique.
    Note this can lead to infinite recursion if n is too large and
    `unique` is set to True (default value)."""
    values = []
    kw.setdefault("exclude", [])
    # Make a copy of `exclude`, to not modify the given list.
    kw["exclude"] = list(kw["exclude"])
    for i in range(n):
        val = func(**kw)
        if unique:
            kw["exclude"].append(val)
        values.append(val)
    return values


def distinct(*vals):
    """Test that all values are distinct.

    Values must be either immutable or convertible to tuples::

    >>> distinct(1, 2, 3)
    True
    >>> distinct(1, 1, 3)
    False
    >>> distinct(5, 4, 5.0)
    False
    >>> distinct((1, 2), {1, 3})
    True
    >>> distinct((1, 2), {1, 2})
    False
    """
    try:
        return len(set(vals)) == len(vals)
    except TypeError:
        hashable_vals = set()
        for val in vals:
            try:
                hashable_vals.add(val)
            except TypeError:
                try:
                    hashable_vals.add(tuple(val))
                except TypeError:
                    raise ValueError(f"Unsupported type {type(val)} for {val!r}")
        return len(set(hashable_vals)) == len(vals)
