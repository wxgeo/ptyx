from __future__ import division, unicode_literals, absolute_import, print_function

import sys
import re

#~ print sys.path
sys.path.append('..')

from latexgenerator import SyntaxTreeGenerator, LatexGenerator, Compiler, parse
from utilities import find_closing_bracket, round, print_sympy_expr
from randfunc import randchoice, srandchoice, randfrac
from ptyx import enumerate_shuffle_tree, display_enumerate_tree

from testlib import assertEq

def test_find_closing_bracket():
    text = '{hello{world} !} etc.'
    assert find_closing_bracket(text, 1) == 15
    text = "{'}'}"
    assert find_closing_bracket(text, 1) == 4
    text = "{'}'}"
    assert find_closing_bracket(text, 1, detect_strings=False) == 2

def test_round():
    assertEq(round(1.775, 2), 1.78)

    assertEq(round(1.454, -2), 0)
    assertEq(round(1.454, -1), 0)
    assertEq(round(1.454), 1)
    assertEq(round(1.454, 1), 1.5)
    assertEq(round(1.454, 2), 1.45)
    assertEq(round(1.454, 3), 1.454)
    assertEq(round(1.454, 4), 1.454)

    assertEq(round(-9.545, -2), 0)
    assertEq(round(-9.545, -1), -10)
    assertEq(round(-9.545), -10)
    assertEq(round(-9.545, 1), -9.5)
    assertEq(round(-9.545, 2), -9.55)
    assertEq(round(-9.545, 3), -9.545)
    assertEq(round(-9.545, 4), -9.545)

    assertEq(round(float('inf'), 4), float('inf'))
    assertEq(round(float('-inf'), 4), float('-inf'))
    assertEq(str(round(float('nan'), 4)), 'nan')

def test_print_sympy_expr():
    assertEq(print_sympy_expr(0.0), "0")
    assertEq(print_sympy_expr(-2.0), "-2")
    assertEq(print_sympy_expr(-0.0), "0")


def test_syntax_tree():
    s = SyntaxTreeGenerator()
    text = 'hello world !'
    s.preparse(text)
    tree = \
"""
+ Node ROOT
  - text: 'hello world !'
""".strip()
    assertEq(s.syntax_tree.display(color=False), tree)

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
    assertEq(s.syntax_tree.display(color=False), tree)


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
    assertEq(s.syntax_tree.display(color=False), tree)


def test_latex_code_generator():
    test = "#{variable=3;b=1;}#{a=2}#IF{a>0}some text here#ELIF{b>0}some more text#ELSE variable value is #variable not #{variable+1} !#END ok"
    c = Compiler()
    latex = c.parse(test)
    assertEq(latex, '2some text here ok')

def test_CALC():
    test = "$#CALC{\dfrac{2}{3}+1}=#RESULT$ et $#CALC[a]{\dfrac{2}{3}-1}=#a$"
    c = Compiler()
    latex = c.parse(test)
    assertEq(latex, r'$\dfrac{2}{3}+1=\frac{5}{3}$ et $\dfrac{2}{3}-1=- \frac{1}{3}$')

def test_TABVAR():
    test = "$#{a=2;}\\alpha=#{alpha=3},\\beta=#{beta=5}\n\n#TABVAR[limites=False,derivee=False]f(x)=#a*(x-#alpha)^2+#beta#END$"
    result = \
'''$\\alpha=3,\\beta=5
\\setlength{\\TVextraheight}{\\baselineskip}
\\[\\begin{tabvar}{|C|CCCCC|}
\\hline
\\,\\,x\\,\\,                            &-\\infty      &        &3&      &+\\infty\\\\
\\hline
\\niveau{1}{2}\\raisebox{0.5em}{$f(x)$}&\\niveau{2}{2}&\\decroit&5&\\croit&\\\\
\\hline
\\end{tabvar}\\]
% x;f(x):(-oo;) >> (3;5) << (+oo;)
% f(x)=2*(x-3)^2+5\n$'''
    c = Compiler()
    latex = c.parse(test)
    assertEq(latex, result)

def test_SEED_SHUFFLE():
    test = '''#SEED{16}Who said "Having nothing, nothing can he lose" ?

\\begin{enumerate}
#SHUFFLE
#ITEM \item W. Shakespeare
#ITEM \item R. Wallace
#ITEM \item C. Doyle
#ITEM \item R. Bradsbury
#END
\\end{enumerate}

"The game is up."'''
    result = \
'''Who said "Having nothing, nothing can he lose" ?

\\begin{enumerate} \\item C. Doyle \\item W. Shakespeare \\item R. Bradsbury \\item R. Wallace
\\end{enumerate}

"The game is up."'''
    c = Compiler()
    latex = c.parse(test)
    assertEq(latex, result)
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
    assertEq(results[0], '%\nb\na\nc')
    assertEq(results[1], '%\n\nb\na\nc')
    assertEq(results[2], '%\nb\na\nc')



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
    assertEq(g.NUM, 0)
    
    c.state['seed'] = 5
    assertEq(g.NUM, 0)
    latex = c.generate_latex()
    latex = re.sub('\s+', ' ', latex).strip()
    assertEq(latex, 'And the winner is: 3')

def test_CASE():
    test = "#CASE{0}first case#CASE{1}second case#CASE{2}third one#END#CASE{1} bonus#END this is something else."
    result = "second case bonus this is something else."
    c = Compiler()
    latex = c.parse(test, NUM=1)
    assertEq(latex, result)

def test_IF_ELIF_ELSE():
    test = r"#{a=1;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END#{a=0;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END#{a=2;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END."
    result = r"10{}2."
    c = Compiler()
    latex = c.parse(test)
    assertEq(latex, result)

def test_MACRO():
    test = r"#NEW_MACRO{a0}#IF{a==0}$a=0$#ELSE$a\neq 0$#END#END#{a=0;}Initially #MACRO{a0}#{a=2;}, but now #MACRO{a0}."
    result = r"Initially $a=0$, but now $a\neq 0$."
    c = Compiler()
    latex = c.parse(test)
    assertEq(latex, result)

def test_randchoice():
    for i in range(1000):
        assertEq(randchoice(0, 1, exclude=[0]), 1)
        assertEq(srandchoice(0, 1, exclude=[0, 1]), -1)
        assert randchoice([0, 1, 2], exclude=[0]) in [1, 2]
        assert srandchoice([0, 1, 2], exclude=[0, 1]) in [-1, -2, 2]


def test_randfrac():
    for i in range(1000):
        assertEq(randfrac(2, 7, den=6).q, 6)


def test_latex_newcommand():
    # \newcommand parameters #1, #2... are not tags.
    test = r'''\newcommand{\rep}[1]{\ding{114}\,\,#1\hfill}'''
    result = test
    c = Compiler()
    latex = c.parse(test)
    assertEq(latex, result)

def test_TEST():
    test = r'''#{hxA=2;}#{yA=3;}\fbox{#TEST{hxA==yA}{is in}{isn't in}}'''
    result = r'''\fbox{isn't in}'''
    c = Compiler()
    latex = c.parse(test)
    assertEq(latex, result)

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
    assertEq(latex, result)

    # Test 2
    test = "2#*3"
    result = r"2\times 3"
    c = Compiler()
    latex = c.parse(test)
    assertEq(latex, result)

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
    assertEq(latex, result)

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
    assertEq(latex, result)


def test_enumerate_tree():
    test = r'''
Some text outside enumerate environnement...
\begin{enumerate}
\item This is first question...
\begin{enumerate}
\item ...and this is first subquestion.
\item An other one.
\item Last one.
\end{enumerate}
\item Ok, second question now.
\item Third one.
\begin{enumerate}
\item  subquestion 1
\item subquestion 2
\item subquestion 3
\end{enumerate}
\end{enumerate}

That's all, folks.
'''


    tree = display_enumerate_tree(enumerate_shuffle_tree(test), color=False, raw=True)
    assertEq(tree,
r'''  - text: '\nSome text outside enumerate environnement...\n'
  + Node enumerate []
    - text: '\n'
    + Node item []
      - text: ' This is first question...\n'
      + Node enumerate []
        - text: '\n'
        + Node item []
          - text: ' ...and this is first subquestion.\n'
        + Node item []
          - text: ' An other one.\n'
        + Node item []
          - text: ' Last one.\n'
      - text: '\n'
    + Node item []
      - text: ' Ok, second question now.\n'
    + Node item []
      - text: ' Third one.\n'
      + Node enumerate []
        - text: '\n'
        + Node item []
          - text: '  subquestion 1\n'
        + Node item []
          - text: ' subquestion 2\n'
        + Node item []
          - text: ' subquestion 3\n'
      - text: '\n'
  - text: "\n\nThat's all, folks.\n"''')


if __name__ == '__main__':
    test_PICK()
