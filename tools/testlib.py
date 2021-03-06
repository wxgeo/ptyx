from __future__ import division, unicode_literals, absolute_import, print_function

from random import random, randint as _randint
from os.path import split, realpath, abspath
import sys

from utilities import term_color

_module_path = split(realpath(sys._getframe().f_code.co_filename))[0]
ROOTDIR = abspath(_module_path + '/..') # /.../nom_du_projet/
#~ WXGEODIR = ROOTDIR + '/wxgeometrie'
EPSILON = 0.0000000001

def randint(a, b = None):
    if b is None:
        b = a
        a = 0
    return _randint(a, b)

def rand():
    return randint(50) - randint(50) + random()

def assertAlmostEqual(x, y):
    if type(x) == type(y) and isinstance(x, (tuple, list)):
        for x_elt, y_elt in zip(x, y):
            assertAlmostEqual(x_elt, y_elt)
    else:
        TEST = abs(y - x) < EPSILON
        if not TEST:
            print("%s != %s" % (x, y))
        assert TEST

def assertNotAlmostEqual(x, y):
    # TODO: define test for tuple
    TEST = abs(y - x) > EPSILON
    if not TEST:
        print("%s == %s" % (x, y))
    assert TEST

def assertEqual(x, y):
    if x != y:
        rx = repr(x)
        ry = repr(y)
        if isinstance(x, str) and isinstance(y, str):
            for i in range(min(len(rx), len(ry))):
                if rx[i] != ry[i]:
                    break
            rx = rx[:i] + term_color(rx[i:], 'yellow')
            ry = ry[:i] + term_color(ry[i:], 'green')

        print('''
--------------
 *** FAIL ***
-> Output:
%s
-> Expected:
%s
--------------
''' %(rx, ry))
    assert (x == y)

assertEq = assertEqual

def assertRaises(error, f, *args, **kw):
    try:
        f(*args, **kw)
    except Exception as e:
        assert type(e) == error
    else:
        raise AssertionError('%s should be raised.' %type(e).__name__)
