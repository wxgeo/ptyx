import random
from fractions import gcd

from config import param, sympy

if sympy is not None:
    from sympy import S

def randint(a=None, b=None, exclude=(), maximum=100000):
    if b is None:
        b = (9 if a is None else a)
        a = 2
    count = 0
    while count < maximum:
        val = random.randint(a, b)
        if val not in exclude:
            break
        count += 1
    else:
        raise RuntimeError("Can't satisfy constraints !")
    if param['sympy_is_default']:
        val = S(val)
    return val

def srandint(a=None, b=None, exclude=(), maximum=100000):
    count = 0
    while count < maximum:
        val = (-1)**random.randint(0, 1)*randint(a, b)
        if val not in exclude:
            return val
        count += 1
    else:
        raise RuntimeError("Can't satisfy constraints !")

def randsign():
    val = (-1)**random.randint(0, 1)
    if param['sympy_is_default']:
        val = S(val)
    return val

def randbool():
    return bool(randint(0, 1))

def randpoint(a=None, b=None, exclude=()):
    while True:
        x = randint(a, b)
        y = randint(a, b)
        if (x, y) not in exclude:
            return (x, y)

def srandpoint(a=None, b=None, exclude=()):
    while True:
        x = srandint(a, b)
        y = srandint(a, b)
        if (x, y) not in exclude:
            return (x, y)

def is_mult_2_5(val):
    "Test if integer val matches 2^n*5^m."
    if sympy:
        ints = (sympy.Integer, int, long)
    else:
        ints = (int, long)
    if hasattr(val, '__iter__'):
        return all(is_mult_2_5(v) for v in val)
    if val == 0 or not isinstance(val, ints):
        return False
    while val%5 == 0:
        val = val//5
    while val%2 == 0:
        val = val//2
    return val in (1, -1)


def randfrac(a=None, b=None, exclude=(), not_decimal=False, den=None):
    '''Return a random fraction which is never an integer.

    Use `d` to specify denominator value; `d` must be an integer or a tuple
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
        raise ValueError, ('(%s, %s) are not valid parameters.' % (a, b))
    if not_decimal and is_mult_2_5(den):
        raise ValueError, "chosen denominator is not compatible with `not_decimal` option."
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

def srandfrac(a=None, b=None, exclude=(), not_decimal=False, den=None):
    while True:
        val = (-1)**randint(0, 1)*randfrac(a, b, not_decimal=not_decimal, den=den)
        if val not in exclude:
            return val


def randchoice(*items, **kw):
    """Select randomly an item.
    """
    if len(items) == 1 and hasattr(items[0], '__iter__'):
        items = items[0]
    if kw.get('signed'):
        items = list(items) + [-1*item for item in items]
    if 'exclude' in kw:
        items = [val for val in items if val not in kw['exclude']]
    val = random.choice(items)
    if isinstance(val, (int, long, float, complex)):
        val = S(val)
    return val

def srandchoice(*items, **kw):
    kw['signed'] = True
    return randchoice(*items, **kw)

