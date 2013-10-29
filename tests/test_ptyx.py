# -*- coding: utf-8 -*-
from __future__ import division # 1/2 == .5

import sys

#~ print sys.path
sys.path.append('..')

from ptyx2 import SyntaxTreeGenerator, LatexGenerator, find_closing_bracket
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




# À TESTER :
# "#IF{True}message 1#IF{False}message 2#ELSE message 3" -> voir si 'message 3' s'affiche bien.
