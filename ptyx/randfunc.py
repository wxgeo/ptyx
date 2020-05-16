import random
import functools
from collections import namedtuple

from math import gcd

from ptyx.config import param, sympy

if sympy is not None:
    from sympy import S

# Important note: all the following functions are sandboxed.
# By this, I mean that any external call to random won't affect random state for
# the following functions.

_RANDOM_STATE = random.getstate()
_SANDBOXED_MODE = False


class Point(namedtuple('Point', ['x', 'y'])):
    def __add__(self, vec):
        return Point(self.x + vec[0], self.y + vec[1])

    def __neg__(self):
        return Point(-self.x, -self.y)

    def __sub__(self, vec):
        return Point(self.x - vec[0], self.y - vec[1])

    def __rmul__(self, k):
        return Point(k*self.x, k*self.y)

def _print_state():
    "For debuging purpose."
    print(29*'*')
    print('randfunc._RANDOM_STATE value:')
    print(hash(_RANDOM_STATE))
    print(29*'*')

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
def randint(a=None, b=None, exclude=(), maximum=100000):
    if b is None:
        b = (9 if a is None else a)
        a = 2
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
    if param['sympy_is_default']:
        val = S(val)
    return val



@sandboxed
def srandint(a=None, b=None, exclude=(), maximum=100000):
    if b is None:
        b = (9 if a is None else a)
        a = 2
    while a in exclude and -a in exclude:
        a += 1
        if a > b:
            raise ValueError("Can't statisfy constraints !")
    while b in exclude and -b in exclude:
        b -= 1
        if a > b:
            raise ValueError("Can't statisfy constraints !")
    while True:
        val = (-1)**random.randint(0, 1)*randint(a, b)
        if val not in exclude:
            return val
    else:
        raise RuntimeError("Can't satisfy constraints !")



@sandboxed
def randsign():
    val = (-1)**random.randint(0, 1)
    if param['sympy_is_default']:
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

def is_mult_2_5(val):
    "Test if integer val matches 2^n*5^m."
    if sympy:
        ints = (sympy.Integer, int)
    else:
        ints = (int,)
    if hasattr(val, '__iter__'):
        return all(is_mult_2_5(v) for v in val)
    if val == 0 or not isinstance(val, ints):
        return False
    while val%5 == 0:
        val = val//5
    while val%2 == 0:
        val = val//2
    return val in (1, -1)

@sandboxed
def randfrac(a=None, b=None, exclude=(), not_decimal=False, den=None):
    '''Return a random positive fraction which is never an integer.

    Use `den` to specify denominator value; `den` must be an integer or a tuple
    of integers.
    '''
    if b is None:
        b = (9 if a is None else a)
        a = 2
    if hasattr(den, '__iter__'):
        # To allow rando.choice() and multiple iterations.
        den = list(den)
    if (den is None and a in (-1, 0, 1) and b in (-1, 0, 1)) or a == b:
        # This would lead to infinite loop.
        raise ValueError('(%s, %s) are not valid parameters.' % (a, b))
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
            if hasattr(den, '__iter__'):
                d = random.choice(den)
            else:
                d = den
            if gcd(d, n) not in (-1, 1):
                # XXX this may lead to infinite loop if wrong arguments are passed
                continue
        val = S(n)/S(d)
        if not_decimal and is_mult_2_5(val.q):
            continue
        if not val.is_integer and val not in exclude:
            return val

@sandboxed
def srandfrac(a=None, b=None, exclude=(), not_decimal=False, den=None):
    '''Return a random signed fraction which is never an integer.

    Use `den` to specify denominator value; `den` must be an integer or a tuple
    of integers.
    '''
    while True:
        val = (-1)**randint(0, 1)*randfrac(a, b, not_decimal=not_decimal, den=den)
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
    if kw.get('signed'):
        items = list(items) + [-1*item for item in items]
    if 'exclude' in kw:
        items = [val for val in items if val not in kw['exclude']]
    val = random.choice(items)
    if isinstance(val, (int, float, complex)):
        val = S(val)
    return val

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
    kw['signed'] = True
    return randchoice(*items, **kw)

@sandboxed
def shuffle(l, _random=None):
    random.shuffle(l, _random)

@sandboxed
def randfloat(a, b, d=5, exclude=[]):
    k = 10**d
    exclude = {int(round(v*k)) for v in exclude}
    while True:
        n = randint(int(round(a*k)) + 1, int(round(b*k)) - 1)
        if n not in exclude:
            return float(n/k)


@sandboxed
def srandfloat(a, b, d=5, exclude=[]):
    return float(randsign())*randfloat(a, b, d, exclude)



def many(n=2, func=srandint, unique=True, **kw):
    """Return several numbers at once.

    By default, every number is unique.
    Note this can lead to infinite recursion if n is too large."""
    l = []
    kw.setdefault('exclude', [])
    for i in range(n):
        val = func(**kw)
        kw['exclude'].append(val)
        l.append(val)
    return l


def distinct(*vals):
    return len(set(vals)) == len(vals)

