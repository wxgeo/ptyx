"""
EXTENDED PYTHON

"""
import pytest
from ptyx.latex_generator import Compiler

import ptyx.extensions.extended_python
from ptyx.extensions.extended_python import main


@pytest.fixture
def compiler():
    return Compiler()


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
#END_PYTHON
some text
#PYTHON
a, b, c, = many(3, srandfrac)
#END_PYTHON

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
    affect1 = "(_tmp_ptyx_var := many(2, srandint), a := _tmp_ptyx_var[0], b := _tmp_ptyx_var[1])"
    affect2 = "(_tmp_ptyx_var := many(2, randint, a=2, b=5), c := _tmp_ptyx_var[0], d := _tmp_ptyx_var[1])"
    text2 = f"""
Some text.
#PYTHON
def f():
    while (({affect1} or True) and not (a*b % 2 == 0)): pass
    while (({affect2} or True) and not (c > d)): pass
f()
#END_PYTHON
Some text too.
"""
    assert main(text, None) == text2


def test_let_with_compilation(compiler):
    code = """
#LOAD{extended_python}#SEED{55}
........
for i in range(100):
    let a, b in -10..10 with a < b
    assert a < b
........ 
OK
"""
    assert compiler.parse(code=code).strip() == "OK"


def test_change_delimiter(monkeypatch):
    assert isinstance(ptyx.extensions.extended_python.PYTHON_DELIMITER, str)

    monkeypatch.setattr(ptyx.extensions.extended_python, "PYTHON_DELIMITER", r"^\*\*\*$")
    code = "\n***\nprint('hello')\n***\n***"
    new_code = code.replace("***", "#PYTHON", 1).replace("***", "#END_PYTHON", 1)
    assert main(code, None) == new_code


def test_preserve_verbatim():
    code = r"""Complete python code:
#VERBATIM
def factorial(n):
    if n == 0:
        ............
    else:
        ............
#END

Hint: (n+1)!=(n+1)*n!.
"""
    assert main(code, None) == code  # code unchanged


def test_no_linebreak_before_first_delimiter():
    code = """...................
x = 5
................."""
    new_code = """#PYTHON
x = 5
#END_PYTHON"""
    assert main(code, None) == new_code


def test_missing_linebreak():
    for code in (
        "...................x = 5\n.................",
        "...................\nx = 5.................",
        "a...................\nx = 5\n.................",
    ):
        assert main(code, None) == code  # code unchanged
