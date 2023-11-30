import os
import re
from os.path import dirname

from ptyx.latex_generator import Compiler

TEST_DIR = dirname(__file__)


def test_SEED_SHUFFLE():
    test = '''#SEED{16}Who said "Having nothing, nothing can he lose" ?

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
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_SEED_SHUFFLE_2():
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
    c = Compiler()
    results = []
    for test in tests:
        results.append(c.parse(code=test))
    assert results[0] == "%\nc\na\nb"
    assert results[1] == "%\n\nc\na\nb"
    assert results[2] == "%\nc\na\nb"


def test_PICK():
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
    c = Compiler()
    c.read_code(test)
    c.preparse()
    # Tweak seed.
    c._state["seed"] = 1
    c.generate_syntax_tree()
    g = c.latex_generator
    assert g.NUM == 0

    # Tweak seed again.
    c._state["seed"] = 5
    assert g.NUM == 0
    latex = c.get_latex()
    latex = re.sub(r"\s+", " ", latex).strip()
    assert latex == "And the winner is: 3"


def test_CASE():
    test = (
        "#CASE{0}first case#CASE{1}second case#CASE{2}third one#END#CASE{1} bonus#END this is something else."
    )
    result = "second case bonus this is something else."
    c = Compiler()
    latex = c.parse(code=test, PTYX_NUM=1)
    assert latex == result


def test_IF_ELIF_ELSE():
    test = (
        "#{a=1;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END"
        "#{a=0;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END#{a=2;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END."
    )
    result = r"10{}2."
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_MACRO():
    test = r"#MACRO{a0}#IF{a==0}$a=0$#ELSE$a\neq 0$#END#END_MACRO#{a=0;}Initially #CALL{a0}#{a=2;}, but now #CALL{a0}."
    result = r"Initially $a=0$, but now $a\neq 0$."
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_TEST():
    test = r"""#{hxA=2;}#{yA=3;}\fbox{#TEST{hxA==yA}{is in}{isn't in}}"""
    result = r"""\fbox{isn't in}"""
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_MUL():
    # Test 1
    test = r"""
#PYTHON
a=-8
b=4
c=5
d=8
#END
$\dfrac{#a#*(#{c*x+d})#-#{a*x+b}#*#c}{(#{c*x+d})^2}$"""
    result = r"""
$\dfrac{-8\times (5 x + 8)-\left(- 8 x + 4\right)\times 5}{(5 x + 8)^2}$"""
    alternative_result = r"""
$\dfrac{-8\times (5 x + 8)-\left(4 - 8 x\right)\times 5}{(5 x + 8)^2}$"""
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result or latex == alternative_result

    # Test 2
    test = "2#*3"
    result = r"2\times 3"
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_MUL_SUB_ADD_expr():
    test = r"""
#PYTHON
a = 6
b = 6
c = 5
d = -4
#END
$#a#*#{b*x+c}$
$#a#*#d$
$#d#*#a$
$#d#*#x$
$#a#-#{b*x+c}$
$#a#+#d$"""
    result = r"""
$6\left(6 x + 5\right)$
$6\times \left(-4\right)$
$-4\times 6$
$-4x$
$6-\left(6 x + 5\right)$
$6-4$"""
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_EVAL_abs():
    test = r"$#{abs(-5)}$"
    result = r"$5$"
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_EVAL_rounding():
    test = r"#[2]{2/3}"
    result = r"0,67"
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result
    test = r"#[2,.]{2/3}"
    result = r"0.67"
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_ADD():
    test = r"""
#PYTHON
a = 2
b = 3
#END
$#a#+\dfrac{#b}{x}$"""
    result = r"""
$2+\dfrac{3}{x}$"""
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


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


def test_rand_pick():
    test = r"""
    #SEED{187}
    #PYTHON
    values = [1,2,3,4]
    #END
    #[rand]values is #[select]values ?
    """
    target = "3is1?"
    c = Compiler()
    latex = c.parse(code=test)
    assert latex.replace(" ", "").strip() == target


def test_INCLUDE():
    os.chdir(TEST_DIR)
    test = "#SEED{99}First, $a=#{a=7}$#INCLUDE{include_example.txt}Last, $a=#a$ still."
    result = """First, $a=7$
This is an example of a file
that can be included using INCLUDE tag.
It may contain some pTyX code...
Note that if $a=1$, then $a+1=2$.
Last, $a=7$ still."""
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_INCLUDE_newline():
    os.chdir(TEST_DIR)
    test = """#SEED{99}
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
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_VERBATIM_tag():
    c = Compiler()
    test = r"""
#VERBATIM
def pi2():
    return "$\pi^2$"
#END
"""
    latex = c.parse(code=test)
    assert latex == (
        r'\texttt{def~pi2():\linebreak\phantom{}~~~~return~"\$\textbackslash{}pi\textasciicircum{}2\$"}' "\n"
    )


def test_PYTHON_tag():
    c = Compiler()
    test = r"""
#PYTHON
a = 2 # test for comment support
#END
#a
"""
    latex = c.parse(code=test)
    assert latex == "\n2\n"


def test_PRINT_tag(capfd):
    c = Compiler()
    test = r"""
#SEED{0}
#PRINT{Hello}
"""
    latex = c.parse(code=test)
    out, err = capfd.readouterr()
    assert out == "Hello\n"


def test_PRINT_hash_symbol(capfd):
    c = Compiler()
    test = r"""
#SEED{0}
#PRINT{Hello ## ##}
"""
    latex = c.parse(code=test)
    out, err = capfd.readouterr()
    assert out == "Hello # #\n"
    assert latex == "\n\n\n"


def test_PRINT_hash_symbol2(capfd):
    c = Compiler()
    test = r"""
#SEED{0}
#{a=7;}
#PRINT{Hello ##a ##}
"""
    latex = c.parse(code=test)
    out, err = capfd.readouterr()
    assert out == "Hello #a #\n"
    assert latex == "\n\n\n\n"


def test_PRINT_EVAL_tag(capfd):
    c = Compiler()
    test = r"""
#SEED{0}
#{a=7;}Hi #a!
#PRINT_EVAL{Hello #a ##}
"""
    latex = c.parse(code=test)
    out, err = capfd.readouterr()
    assert out == "Hello 7 #\n"
    assert latex == "\n\nHi 7!\n\n"


def test_ASK_ASK_ONLY_ANS_ANSWER_tag():
    c = Compiler()
    test = r"""
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
    tex = c.parse(code=test)
    assert (
        tex
        == r"""
Hello!

\dotfill
Question:
1+1=
\dotfill

%

Bye!
"""
    )
    c.reset()
    tex = c.parse(code=test, PTYX_WITH_ANSWERS=True)
    assert (
        tex
        == r"""
Hello!

\dotfill
1+1=
2
\dotfill

That was easy!%

Bye!
"""
    )
