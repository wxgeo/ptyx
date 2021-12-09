"""
QUESTIONS

This extension offers a new syntax to write tests and answers.
"""

import os
import re
from pathlib import Path
import atexit

from ptyx.latexgenerator import Compiler, Node
from ptyx.extensions.autoqcm.compile.ptyx2latex import  SameAnswerError


TEST_DIR = Path(__file__).parent.resolve()
TMP_PDF = ["test_questions_context.pdf", "test_questions_context-corr.pdf"]


def load_ptyx_file(filename):
    """Load ptyx file, create a `Compiler` instance and call extensions to
    generate a plain ptyx file.

    Return the `Compiler` instance."""
    path = TEST_DIR / filename
    c = Compiler()
    c.read_file(path)
    c.preparse()
    return c


def test_MCQ_basics():
    c = load_ptyx_file('partial-test.ptyx')
    assert 'VERSION' in c.syntax_tree_generator.tags
    assert 'VERSION' in c.latex_generator.parser.tags
    assert 'END_QCM' in c.syntax_tree_generator.tags
    assert 'END_QCM' in c.latex_generator.parser.tags
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
    assert not seed_found # `#SEED` is parsed and removed before generating the syntax tree.
    assert header_found
    assert mcq_found
    #TODO: add tests
    latex = c.get_latex()
    #TODO: add tests
    assert "Jean de la Fontaine" in latex


def test_MCQ_shuffling():
    c = load_ptyx_file('test_shuffle.ptyx')
    c.generate_syntax_tree()
    root = c.syntax_tree
    assert isinstance(root, Node)
    assert root.name == 'ROOT'
    assert repr(root) == f'<Node ROOT at {hex(id(root))}>'
    header = root.children[0]
    assert isinstance(header, Node)
    assert header.name == 'QCM_HEADER'
    mcq = root.children[-2]
    assert isinstance(mcq, Node)
    assert mcq.name == 'QCM'
    section = mcq.children[-1]
    assert isinstance(section, Node)
    assert section.name == 'SECTION'

    # Test question structure.
    qlist = []
    for question in section.children:
        assert isinstance(question, Node)
        assert question.name in ('NEW_QUESTION', 'CONSECUTIVE_QUESTION')
        assert len(question.children) == 1
        version = question.children[0]
        assert isinstance(version, Node)
        assert version.name == 'VERSION'
        question_text = version.children[1].strip()
        qlist.append(question_text.split()[0])
        if 'must follow' in question_text:
            assert question.name == 'CONSECUTIVE_QUESTION'
        else:
            assert question.name == 'NEW_QUESTION'
    assert qlist == [f'question{c}' for c in 'ABCDEFGHIJ'], qlist

    # Test questions order
    latex = c.get_latex()
    questions = []
    i = 0
    while i != -1:
        i = latex.find('question', i)
        if i!= -1:
            i += len('question')
            questions.append(latex[i:i+1])
    ordering = ''.join(questions)
    assert 'DEFGHI' in ordering
    assert ordering != ''.join(sorted(questions))
    e0 = latex.find('ansE0')
    e1 = latex.find('ansE1')
    e2 = latex.find('ansE2')
    e3 = latex.find('ansE3')
    e4 = latex.find('ansE4')
    f1 = latex.find('ansF1')
    f2 = latex.find('ansF2')
    f3 = latex.find('ansF3')
    assert all(i != -1 for i in (e0, e1, e2, e3, e4, f1, f2, f3))
    assert max(f1, f2) < f3
    assert f1 < f3
    assert e0 < min(e1, e2, e3) < max(e1, e2, e3) < e4
    assert '\n\n' not in latex[f1:f2]
    assert '\n\n' in latex[f2:f3]
    assert '\n\n' not in latex[e0:e1]
    assert '\n\n' not in latex[e1:e2]
    assert '\n\n' not in latex[e2:e3]
    assert '\n\n' not in latex[e3:e4]
    return latex

def test_include():
    os.chdir(TEST_DIR)
    c = load_ptyx_file('test_include.ptyx')
    # Test for support of:
    # - no star at all at the beginning of the question (must be automatically added)
    with open('exercises/ex1.txt') as f:
        assert not f.read().startswith('*')
    # - a line break after the star. This should be Ok too.
    with open('exercises/ex2.txt') as f:
        assert f.read().startswith('*\n')
    c.generate_syntax_tree()
    latex = c.get_latex()
    assert r"$2\times(-1)^2$" in latex
    assert "an other answer" in latex

def test_include_glob():
    os.chdir(TEST_DIR)
    c1 = load_ptyx_file('test_include.ptyx')
    c1.generate_syntax_tree()
    latex1 = c1.get_latex()
    c2 = load_ptyx_file('test_include_glob.ptyx')
    c2.generate_syntax_tree()
    latex2 = c2.get_latex()
    assert r"$2\times(-1)^2$" in latex2
    assert "an other answer" in latex2
    assert latex1.split() == latex2.split()


def test_question_context():
    c = load_ptyx_file('test_questions_context.ptyx')
    c.generate_syntax_tree()
    latex = c.get_latex()

    for match in re.finditer(r'TEST\((\w+)=(\w+)\)', latex):
        assert match.group(1) == match.group(2)


def test_unicity_of_answers():
    c = load_ptyx_file('test_unicity_of_answers.ptyx')
    c.generate_syntax_tree()
    try:
        c.get_latex()
        # The same answer appeared twice, it should have raised an error !
        assert False
    except SameAnswerError:
        # Alright, identical answers were detected.
        pass


@atexit.register
def cleanup():
    files_found = False
    # Remove .ptyx.plain-ptyx files generated during tests.
    for tmp_filename in TEST_DIR.glob("*.ptyx.plain-ptyx"):
        tmp_filename.unlink()
        files_found = True
    assert files_found
    for tmp_filename in TMP_PDF:
        (TEST_DIR / Path(tmp_filename)).unlink()


if __name__ == '__main__':
    test_MCQ_shuffling()
    print('OK')