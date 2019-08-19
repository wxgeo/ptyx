"""
EXTENDED PYTHON

"""


import sys
from os.path import join, dirname, realpath

from testlib import assertEq


def test_question():
    text = r"""

................................
let a, b
let c +
let e, f, g, h -
let a in 3..7
let u, v in -5..-2
................................

"""
    text2 = """

#PYTHON
a, b, = many(2, srandint)
c, = many(1, randint)
e, f, g, h, = many(4, randint, a=-9, b=-2)
a, = many(1, randint, a=3, b=7)
u, v, = many(2, randint, a=-5, b=-2)
#END

"""
    print(sys.executable)
    this_file = realpath(sys._getframe().f_code.co_filename)
    filename = join(dirname(dirname(this_file)), 'extended_python.py')

    d = {}
    exec(compile(open(filename).read(), filename, 'exec'), d)
    assertEq(d['main'](text, None), text2)

