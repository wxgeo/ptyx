import os
import re
from os.path import dirname

import pytest

from ptyx.latex_generator import Compiler

TEST_DIR = dirname(__file__)


@pytest.fixture
def compiler():
    return Compiler()


def parse(code: str, **kw) -> str:
    return Compiler().parse(code=code, **kw)


def test_SEED_SHUFFLE():
    code = '''#SEED{16}Who said "Having nothing, nothing can he lose" ?

\\begin{enumerate}
#SHUFFLE
#ITEM \\item W. Shakespeare
#ITEM \\item R. Wallace
#ITEM \\item C. Doyle
#ITEM \\item R. Bradsbury
#END
\\end{enumerate}

"The game is up."'''
    result = '''Who said "Having nothing, nothing can he lose" ?

\\begin{enumerate} \\item W. Shakespeare \\item R. Bradsbury \\item R. Wallace \\item C. Doyle
\\end{enumerate}

"The game is up."'''
    assert parse(code) == result


def test_SEED_SHUFFLE_2(compiler):
    tests = [
        """#SEED{153}%
#SHUFFLE
#ITEM
a
#ITEM
b
#ITEM
c
#END""",
        """#SEED{153}%
#SHUFFLE

#ITEM
a
#ITEM
b
#ITEM
c
#END""",
        """#SEED{153}%
#SHUFFLE
 #ITEM
a
#ITEM
b
#ITEM
c
#END""",
    ]
    results = []
    for test in tests:
        results.append(compiler.parse(code=test))
    assert results[0] == "%\nc\na\nb"
    assert results[1] == "%\n\nc\na\nb"
    assert results[2] == "%\nc\na\nb"


def test_PICK(compiler):
    test = """
    And the winner is:
    #PICK
    #ITEM
    1
    #ITEM
    2
    #ITEM
    3
    #ITEM
    4
    #END_PICK"""
    compiler.read_code(test)
    compiler.preparse()
    # Tweak seed.
    compiler._state["seed"] = 1
    compiler.generate_syntax_tree()
    g = compiler.latex_generator
    assert g.NUM == 0

    # Tweak seed again.
    compiler._state["seed"] = 5
    assert g.NUM == 0
    latex = compiler.get_latex()
    latex = re.sub(r"\s+", " ", latex).strip()
    assert latex == "And the winner is: 3"


def test_CASE(compiler):
    code = "#CASE{0}1st case#CASE{1}2nd case#CASE{2}3rd one#END#CASE{1} bonus#END this is something else."
    assert parse(code, PTYX_NUM=1) == "2nd case bonus this is something else."


def test_IF_ELIF_ELSE():
    code = (
        "#{a=1;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END"
        "#{a=0;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END#{a=2;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END."
    )
    assert parse(code) == r"10{}2."


def test_MACRO(compiler):
    code = r"#MACRO{a0}#IF{a==0}$a=0$#ELSE$a\neq 0$#END#END_MACRO#{a=0;}Initially #CALL{a0}#{a=2;}, but now #CALL{a0}."
    assert parse(code) == r"Initially $a=0$, but now $a\neq 0$."


def test_TEST():
    code = r"""#{hxA=2;}#{yA=3;}\fbox{#TEST{hxA==yA}{is in}{isn't in}}"""
    assert parse(code) == r"\fbox{isn't in}"


def test_MUL():
    code = r"""
#PYTHON
a, b, c, d = -8, 4, 5, 8
#END
$\dfrac{#a#*(#{c*x+d})#-#{a*x+b}#*#c}{(#{c*x+d})^2}$"""
    result = r"""
$\dfrac{-8\times (5 x + 8)-\left(- 8 x + 4\right)\times 5}{(5 x + 8)^2}$"""
    alternative_result = r"""
$\dfrac{-8\times (5 x + 8)-\left(4 - 8 x\right)\times 5}{(5 x + 8)^2}$"""
    assert (latex := parse(code)) == result or latex == alternative_result

    assert parse("2#*3") == r"2\times 3"


def test_SUB_ADD_expr():
    code = r"""
#PYTHON
a, b, c, d = 6, 6, 5, -4
#END
$#a#-#{b*x+c}$
$#a#+#d$"""
    result = r"""
$6-\left(6 x + 5\right)$
$6-4$"""
    assert parse(code) == result


def test_MUL_expr():
    code = r"""
#PYTHON
a = 6
b = 6
c = 5
d = -4
e = 0
f = -1
g = 1
#END
$#a#*#{b*x+c}$
$#a#*#d$
$#d#*#a$
$#d#*#x$
#e#*#x#+#c
#g #* #{x + a}
#d #+ #g #* #x
#d #+ #f #* #x
"""
    result = r"""
$6\left(6 x + 5\right)$
$6\times \left(-4\right)$
$-4\times 6$
$-4x$
0+5
  \left(x + 6\right)
-4  +  x
-4  -  x
"""
    assert parse(code) == result


def test_EVAL_abs():
    assert parse(r"$#{abs(-5)}$") == r"$5$"


def test_EVAL_variable_name():
    # Underscore in variable name
    assert parse("#{this_is_a_strange_name_1=3}:#this_is_a_strange_name_1") == "3:3"
    assert parse("#_a") == "_a"
    assert parse("#a_") == "a_{}"
    # A variable name can't start with a digit
    assert parse("#5_a") == "#5_a"


def test_EVAL_rounding():
    assert parse(r"#[2]{2/3}") == r"0,67"
    assert parse(r"#[2,.]{2/3}") == r"0.67"


def test_ADD():
    code = r"""#PYTHON
a, b = 2, 3
#END
$#a#+\dfrac{#b}{x}$"""
    assert parse(code) == "\n" r"$2+\dfrac{3}{x}$"


def test_EVAL_mul_flag():
    test = r"""
    #PYTHON
    a = 1
    b = 1
    c = -1
    d = 0
    e = 5
    #END
    $#[*]a x #+ #[*]b #y #+ #[*]c #z #+ #[*]d #t#+#x= 0$"""
    target = "$x+y-z+x=0$"
    c = Compiler()
    latex = c.parse(code=test)
    assert latex.replace(" ", "").strip() == target
    test = r"""
    #PYTHON
    xu = S(0)
    xv = S(-1)
    xw = S(1)
    #END
    #[*]xu #a#+#[*]xv #b#+#[*]xw #c=0"""
    target = "-b+c=0"
    c = Compiler()
    latex = c.parse(code=test)
    assert latex.replace(" ", "").strip() == target


def test_rand_select_pick():
    code = r"""
    #SEED{187}
    #PYTHON
    values = [1,2,3,4]
    #END
    #[rand]values is #[select]values?
    """
    assert parse(code).strip() == "3 is 1?"


def test_INCLUDE():
    os.chdir(TEST_DIR)
    code = "#SEED{99}First, $a=#{a=7}$#INCLUDE{include_example.txt}Last, $a=#a$ still."
    result = """First, $a=7$
This is an example of a file
that can be included using INCLUDE tag.
It may contain some pTyX code...
Note that if $a=1$, then $a+1=2$.
Last, $a=7$ still."""
    assert parse(code) == result


def test_INCLUDE_newline():
    os.chdir(TEST_DIR)
    code = """#SEED{99}
First, $a=#{a=7}$
#INCLUDE{include_example.txt}
Last, $a=#a$ still."""
    result = """
First, $a=7$

This is an example of a file
that can be included using INCLUDE tag.
It may contain some pTyX code...
Note that if $a=1$, then $a+1=2$.

Last, $a=7$ still."""
    assert parse(code) == result


def test_VERBATIM_tag():
    code = r"""
#VERBATIM
def pi2():
    return "$\pi^2$"
#END
"""
    assert parse(code) == (
        r'\texttt{def~pi2():\linebreak\phantom{}~~~~return~"\$\textbackslash{}pi\textasciicircum{}2\$"}' "\n"
    )


def test_PYTHON_tag():
    code = r"""
#PYTHON
a = 2 # test for comment support
#END
#a
"""
    assert parse(code) == "\n2\n"


def test_PRINT_tag(capfd):
    code = r"""
#SEED{0}
#PRINT{Hello}
"""
    latex = parse(code)
    out, err = capfd.readouterr()
    assert out == "Hello\n"
    assert latex.strip() == ""


def test_PRINT_hash_symbol(capfd):
    code = r"""
#SEED{0}
#PRINT{Hello ## ##}
"""
    latex = parse(code)
    out, err = capfd.readouterr()
    assert out == "Hello # #\n"
    assert latex == "\n\n\n"


def test_PRINT_hash_symbol2(capfd):
    code = r"""
#SEED{0}
#{a=7;}
#PRINT{Hello ##a ##}
"""
    latex = parse(code)
    out, err = capfd.readouterr()
    assert out == "Hello #a #\n"
    assert latex == "\n\n\n\n"


def test_PRINT_EVAL_tag(capfd):
    code = r"""
#SEED{0}
#{a=7;}Hi #a!
#PRINT_EVAL{Hello #a ##}
"""
    latex = parse(code)
    out, err = capfd.readouterr()
    assert out == "Hello 7 #\n"
    assert latex == "\n\nHi 7!\n\n"


def test_ASK_ASK_ONLY_ANS_ANSWER_tag(compiler):
    code = r"""
#SEED{5}Hello!

\dotfill
#ASK_ONLY
Question:
#END
#ASK
1+1=
#END
#ANS
2
#END
\dotfill

#ANSWER{That was easy!}%

Bye!
"""
    result = r"""
Hello!

\dotfill
Question:
1+1=
\dotfill

%

Bye!
"""
    assert compiler.parse(code=code) == result
    result = r"""
Hello!

\dotfill
1+1=
2
\dotfill

That was easy!%

Bye!
"""
    compiler.reset()
    assert compiler.parse(code=code, PTYX_WITH_ANSWERS=True) == result
