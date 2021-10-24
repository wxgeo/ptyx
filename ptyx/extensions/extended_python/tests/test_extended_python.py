"""
EXTENDED PYTHON

"""


from ptyx.extensions.extended_python import main


def test_extended_python():
    text = r"""

................................
let a, b
let c +
let e, f, g, h -
let a in 3..7
let u, v in -5..-2
let p in 2,3,5,7,11,13,17,19
................................
some text
................................
let a,b,c /
................................

"""
    text2 = """

#PYTHON
a, b, = many(2, srandint)
c, = many(1, randint)
e, f, g, h, = many(4, randint, a=-9, b=-2)
a, = many(1, randint, a=3, b=7)
u, v, = many(2, randint, a=-5, b=-2)
p, = many(1, randchoice, items=[2,3,5,7,11,13,17,19])
#END
some text
#PYTHON
a, b, c, = many(3, srandfrac)
#END

"""
    assert main(text, None) == text2


def test_extended_python_with():
    text = r"""
Some text.
................................
def f():
    let a, b with a*b % 2 == 0
    let c,d in 2..5 with c > d
f()
................................
Some text too.
"""
    text2 = """
Some text.
#PYTHON
def f():
    while True:
        a, b, = many(2, srandint)
        if a*b % 2 == 0:
            break
    while True:
        c, d, = many(2, randint, a=2, b=5)
        if c > d:
            break
f()
#END
Some text too.
"""
    assert main(text, None) == text2
