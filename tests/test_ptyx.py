# -*- coding: utf-8 -*-
from __future__ import division # 1/2 == .5

import sys

#~ print sys.path
sys.path.append('..')

from ptyx import SyntaxTreeGenerator, LatexGenerator, find_closing_bracket, randchoice, srandchoice
from testlib import assertEq

def test_find_closing_bracket():
    text = '{hello{world} !} etc.'
    assert find_closing_bracket(text, 1) == 15


def test_syntax_tree():
    s = SyntaxTreeGenerator()
    text = 'hello world !'
    s.parse(text)
    tree = \
"""+ Node ROOT
  - text: 'hello world !'"""
    assertEq(s.syntax_tree.display(color=False), tree)

    text = "#IF{a>0}some text here#ELIF{b>0}some more text#ELSE variable value is #variable not #{variable+1} !#END"
    s.parse(text)
    tree = \
"""+ Node ROOT
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
      - text: ' !'"""
    assertEq(s.syntax_tree.display(color=False), tree)


    text = "#PYTHON#some comment\nvariable = 2\n#END#ASSERT{variable == 2}"
    s.parse(text)
    tree = \
"""+ Node ROOT
  + Node PYTHON
    - text: '#some comment [...]'
  + Node ASSERT
    + Node 0
      - text: 'variable == 2'"""
    assertEq(s.syntax_tree.display(color=False), tree)


def test_latex_code_generator():
    test = "#{variable=3;b=1;}#{a=2}#IF{a>0}some text here#ELIF{b>0}some more text#ELSE variable value is #variable not #{variable+1} !#END ok"
    g = LatexGenerator()
    g.parse(test)
    assertEq(g.read(), '2some text here ok')

def test_CALC():
    test = "$#CALC{\dfrac{2}{3}+1}=#RESULT$ et $#CALC[a]{\dfrac{2}{3}-1}=#a$"
    g = LatexGenerator()
    g.parse(test)
    assertEq(g.read(), r'$\dfrac{2}{3}+1=\frac{5}{3}$ et $\dfrac{2}{3}-1=- \frac{1}{3}$')

def test_TABVAR():
    test = "$#{a=2;}\\alpha=#{alpha=3},\\beta=#{beta=5}\n\n#TABVAR[limites=False,derivee=False]f(x)=#a*(x-#alpha)^2+#beta#END$"
    result = \
'''$\\alpha=3,\\beta=5
\\[\\begin{tabvar}{|C|CCCCC|}
\\hline
x                                    &-\\infty      &        &3&      &+\\infty\\\\
\\hline
\\niveau{1}{2}\\raisebox{0.5em}{$f(x)$}&\\niveau{2}{2}&\\decroit&5&\\croit&\\\\
\\hline
\\end{tabvar}\\]
% x;f(x):(-oo;) >> (3;5) << (+oo;)
% f(x)=2*(x-3)^2+5
$'''
    g = LatexGenerator()
    g.parse(test)
    assertEq(g.read(), result)

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
    g = LatexGenerator()
    g.parse(test)
    assertEq(g.read(), result)
# À TESTER :
# "#IF{True}message 1#IF{False}message 2#ELSE message 3" -> voir si 'message 3' s'affiche bien.

def test_PICK():
    test = '''#PICK{a=1,2,3,4}'''
    g = LatexGenerator()
    assertEq(g.NUM, 0)
    g.parse(test)
    assertEq(g.read(), '1')
    g.clear()
    g.context['NUM'] = 2
    assertEq(g.NUM, 2)
    g.parse(test)
    assertEq(g.read(), '3')

def test_CASE():
    test = "#CASE{0}first case#CASE{1}second case#CASE{2}third one#END#CASE{1} bonus#END this is something else."
    result = "second case bonus this is something else."
    g = LatexGenerator()
    g.context['NUM'] = 1
    g.parse(test)
    assertEq(g.read(), result)

def test_IF_ELIF_ELSE():
    test = r"#{a=1;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END#{a=0;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END#{a=2;}#IF{a==0}0#ELIF{a==1}1#ELSE{}2#END."
    result = r"10{}2."
    g = LatexGenerator()
    g.parse(test)
    assertEq(g.read(), result)

def test_MACRO():
    test = r"#NEW_MACRO{a0}#IF{a==0}$a=0$#ELSE$a\neq 0$#END#END#{a=0;}Initially #MACRO{a0}#{a=2;}, but now #MACRO{a0}."
    result = r"Initially $a=0$, but now $a\neq 0$."
    g = LatexGenerator()
    g.parse(test)
    assertEq(g.read(), result)

def test_randchoice():
    for i in range(1000):
        assertEq(randchoice(0, 1, exclude=[0]), 1)
        assertEq(srandchoice(0, 1, exclude=[0, 1]), -1)
        assert randchoice([0, 1, 2], exclude=[0]) in [1, 2]
        assert srandchoice([0, 1, 2], exclude=[0, 1]) in [-1, -2, 2]

def test_latex_newcommand():
    # \newcommand parameters #1, #2... are not tags.
    test = r'''\newcommand{\rep}[1]{\ding{114}\,\,#1\hfill}'''
    result = test
    g = LatexGenerator()
    g.parse(test)
    assertEq(g.read(), result)


if __name__ == '__main__':
    test_PICK()
