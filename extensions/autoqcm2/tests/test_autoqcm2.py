"""
QUESTIONS

This extension offers a new syntaw to write tests and answers.
"""


import sys, os
from os.path import join, dirname, realpath

from testlib import assertEq
from latexgenerator import Compiler, Node

def test_MCQ():
    c = Compiler()
    print(os.getcwd())
    c.read_file('extensions/autoqcm2/tests/test-partiel.ptyx')
    c.read_seed()
    c.call_extensions()
    assert 'VERSION' in c.syntax_tree_generator.tags
    assert 'VERSION' in c.latex_generator.preparser.tags
    assert 'END_QCM' in c.syntax_tree_generator.tags
    assert 'END_QCM' in c.latex_generator.preparser.tags
    c.generate_syntax_tree()
    header_found = False
    mcq_found = False
    seed_found = False
    for child in c.syntax_tree.children:
        if isinstance(child, Node):
            name = child.name
            if name == 'QCM_HEADER':
                header_found = True
            elif child.name == 'QCM':
                mcq_found = True
            elif name == 'SEED':
                seed_found = True
    assert not seed_found 
    assert header_found
    assert mcq_found
    #TODO: add tests
    latex = c.generate_latex()
    #TODO: add tests
        
    