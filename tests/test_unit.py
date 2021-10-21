import re

from ptyx.latexgenerator import SyntaxTreeGenerator, Compiler#, parse
from ptyx.utilities import find_closing_bracket, round
from ptyx.printers import sympy2latex
from ptyx.randfunc import randchoice, srandchoice, randfrac


def test_find_closing_bracket():
    text = '{hello{world} !} etc.'
    assert find_closing_bracket(text, 1) == 15
    text = "{'}'}"
    assert find_closing_bracket(text, 1) == 4
    text = "{'}'}"
    assert find_closing_bracket(text, 1, detect_strings=False) == 2

def test_round():
    assert round(1.775, 2) == 1.78

    assert round(1.454, -2) == 0
    assert round(1.454, -1) == 0
    assert round(1.454) == 1
    assert round(1.454, 1) == 1.5
    assert round(1.454, 2) == 1.45
    assert round(1.454, 3) == 1.454
    assert round(1.454, 4) == 1.454

    assert round(-9.545, -2) == 0
    assert round(-9.545, -1) == -10
    assert round(-9.545) == -10
    assert round(-9.545, 1) == -9.5
    assert round(-9.545, 2) == -9.55
    assert round(-9.545, 3) == -9.545
    assert round(-9.545, 4) == -9.545

    assert round(float('inf'), 4) == float('inf')
    assert round(float('-inf'), 4) == float('-inf')
    assert str(round(float('nan'), 4)) == 'nan'

def test_sympy2latex():
    assert sympy2latex(0.0) == "0"
    assert sympy2latex(-2.0) == "-2"
    assert sympy2latex(-0.0) == "0"


def test_syntax_tree():
    s = SyntaxTreeGenerator()
    text = 'hello world !'
    s.preparse(text)
    tree = \
"""
+ Node ROOT
  - text: 'hello world !'
""".strip()
    assert s.syntax_tree.display(color=False) == tree

    text = "#IF{a>0}some text here#ELIF{b>0}some more text#ELSE variable value is #variable not #{variable+1} !#END"
    s.preparse(text)
    tree = \
"""
+ Node ROOT
  + Node CONDITIONAL_BLOCK
    + Node IF
      + Node 0
        - text: 'a>0'
      - text: 'some text here'
    + Node ELIF
      + Node 0
        - text: 'b>0'
      - text: 'some more text'
    + Node ELSE
      - text: ' variable value is '
      + Node EVAL
        + Node 0
          - text: 'variable'
      - text: ' not '
      + Node EVAL
        + Node 0
          - text: 'variable+1'
      - text: ' !'
""".strip()
    assert s.syntax_tree.display(color=False) == tree


    text = "#PYTHON#some comment\nvariable = 2\n#END#ASSERT{variable == 2}"
    s.preparse(text)
    tree = \
"""
+ Node ROOT
  + Node PYTHON
    - text: '#some comment\\nvariable  [...]'
  + Node ASSERT
    + Node 0
      - text: 'variable == 2'
""".strip()
    assert s.syntax_tree.display(color=False) == tree


def test_latex_code_generator():
    test = "#{variable=3;b=1;}#{a=2}#IF{a>0}some text here#ELIF{b>0}some more text#ELSE variable value is #variable not #{variable+1} !#END ok"
    c = Compiler()
    latex = c.parse(test)
    assert latex == '2some text here ok'


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
    result = \
'''Who said "Having nothing, nothing can he lose" ?

\\begin{enumerate} \\item W. Shakespeare \\item R. Bradsbury \\item R. Wallace \\item C. Doyle
\\end{enumerate}

"The game is up."'''
    c = Compiler()
    latex = c.parse(test)
    assert latex == result
# ADD A TEST :
# "#IF{True}message 1#IF{False}message 2#ELSE message 3" -> test that 'message 3' is printed.

def test_SEED_SHUFFLE_2():
    tests = []
    tests.append('''#SEED{153}%
#SHUFFLE
#ITEM
a
#ITEM
b
#ITEM
c
#END''')
    tests.append('''#SEED{153}%
#SHUFFLE

#ITEM
a
#ITEM
b
#ITEM
c
#END''')
    tests.append('''#SEED{153}%
#SHUFFLE
 #ITEM
a
#ITEM
b
#ITEM
c
#END''')
    c = Compiler()
    results = []
    for test in tests:
        results.append(c.parse(test))
    assert results[0] == '%\nc\na\nb'
    assert results[1] == '%\n\nc\na\nb'
    assert results[2] == '%\nc\na\nb'



def test_PICK():
    test = '''
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
    #END_PICK'''
    c = Compiler()
    c.state['seed'] = 1
    c.generate_syntax_tree(test)
    g = c.latex_generator
    assert g.NUM == 0

    c.state['seed'] = 5
    assert g.NUM == 0
    latex = c.generate_latex()
    latex = re.sub(r'\s+', ' ', latex).strip()
    assert latex == 'And the winner is: 3'

def test_CASE():
    test = "#CASE{0}first case#CASE{1}second case#CASE{2}third one#END#CASE{1} bonus#END this is something else."
    result = "second case bonus this is something else."
    c = Compiler()
    latex = c.parse(test, NUM=1)
    assert latex == result

def test_IF_ELIF_ELSE():
    test = r"#{a=1;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END#{a=0;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END#{a=2;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END."
    result = r"10{}2."
    c = Compiler()
    latex = c.parse(test)
    assert latex == result

def test_MACRO():
    test = r"#MACRO{a0}#IF{a==0}$a=0$#ELSE$a\neq 0$#END#END_MACRO#{a=0;}Initially #CALL{a0}#{a=2;}, but now #CALL{a0}."
    result = r"Initially $a=0$, but now $a\neq 0$."
    c = Compiler()
    latex = c.parse(test)
    assert latex == result

def test_randchoice():
    for i in range(1000):
        assert randchoice(0, 1, exclude=[0]) == 1
        assert srandchoice(0, 1, exclude=[0, 1]) == -1
        assert randchoice([0, 1, 2], exclude=[0]) in [1, 2]
        assert srandchoice([0, 1, 2], exclude=[0, 1]) in [-1, -2, 2]


def test_randfrac():
    for i in range(1000):
        assert randfrac(2, 7, den=6).q == 6


def test_latex_newcommand():
    # \newcommand parameters #1, #2... are not tags.
    test = r'''\newcommand{\rep}[1]{\ding{114}\,\,#1\hfill}'''
    result = test
    c = Compiler()
    latex = c.parse(test)
    assert latex == result

def test_TEST():
    test = r'''#{hxA=2;}#{yA=3;}\fbox{#TEST{hxA==yA}{is in}{isn't in}}'''
    result = r'''\fbox{isn't in}'''
    c = Compiler()
    latex = c.parse(test)
    assert latex == result

def test_MUL():
    # Test 1
    test = r'''
#PYTHON
a=-8
b=4
c=5
d=8
#END
$\dfrac{#a#*(#{c*x+d})#-#{a*x+b}#*#c}{(#{c*x+d})^2}$'''
    result = r'''
$\dfrac{-8\times (5 x + 8)-\left(- 8 x + 4\right)\times 5}{(5 x + 8)^2}$'''
    c = Compiler()
    latex = c.parse(test)
    assert latex == result

    # Test 2
    test = "2#*3"
    result = r"2\times 3"
    c = Compiler()
    latex = c.parse(test)
    assert latex == result

def test_MUL_SUB_Add_expr():
    test = r'''
#PYTHON
a = 6
b = 6
c = 5
#END
$#a#*#{b*x+c}$
$#a#-#{b*x+c}$'''
    result = r'''
$6\times \left(6 x + 5\right)$
$6-\left(6 x + 5\right)$'''
    c = Compiler()
    latex = c.parse(test)
    assert latex == result

def test_ADD():
    test = r'''
#PYTHON
a = 2
b = 3
#END
$#a#+\dfrac{#b}{x}$'''
    result = r'''
$2+\dfrac{3}{x}$'''
    c = Compiler()
    latex = c.parse(test)
    assert latex == result


if __name__ == '__main__':
    test_PICK()
