import os
import types
from os.path import dirname

import pytest

import ptyx
from ptyx.latex_generator import SyntaxTreeGenerator  # , parse
from tests import parse, Compiler


@pytest.fixture
def compiler():
    return Compiler()


def test_syntax_tree():
    s = SyntaxTreeGenerator()
    text = "hello world !"
    s.generate_tree(text)
    tree = """
+ Node ROOT
  - text: 'hello world !'
""".strip()
    assert s.syntax_tree.display(color=False) == tree

    text = (
        "#IF{a>0}some text here#ELIF{b>0}some more text"
        "#ELSE variable value is #variable not #{variable+1} !#END"
    )
    s.generate_tree(text)
    tree = """
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

    text = "#PYTHON#some comment\nvariable = 2\n#END_PYTHON#ASSERT{variable == 2}"
    s.generate_tree(text)
    tree = """
+ Node ROOT
  + Node PYTHON
    - text: '#some comment\\nvariable  [...]'
  + Node ASSERT
    + Node 0
      - text: 'variable == 2'
""".strip()
    assert s.syntax_tree.display(color=False) == tree


def test_latex_code_generator():
    test = (
        "#{variable=3;b=1;}#{a=2}"
        "#IF{a>0}some text here"
        "#ELIF{b>0}some more text"
        "#ELSE variable value is #variable not #{variable+1} !"
        "#END ok"
    )
    assert parse(test) == "2some text here ok"


def test_hash():
    test = "#{a=5}###a####a"
    assert parse(test) == "5#5##a"


def test_latex_newcommand():
    # \newcommand parameters #1, #2... are not tags.
    test = r"""\newcommand{\rep}[1]{\ding{114}\,\,#1\hfill}"""
    assert parse(test) == test


def test_comments():
    test = """# Let's test comments.
First, $a=#{a=7}$ # This is a comment
# This is another comment
# Comment are introduced using an hashtag followed by a space : # comment
# The hashtag must also be preceded by a space or be the first caracter of the line.
Last, $a=#a$ still.
#a#a#a#a # comment must support things like #a of course (there are remove
# before parsing).
## is just displayed as a hash, it is not a comment.
# # is comment though."""
    result = """First, $a=7$
Last, $a=7$ still.
7777
# is just displayed as a hash, it is not a comment.
#"""
    assert parse(test) == result


def test_write():
    test = r"""
#PYTHON
a = 5
write(r"$\#$ ")
write("#a ")
write("#a", parse=True)
#END_PYTHON
"""
    assert parse(test) == "$\\#$ #a 5\n"


def test_write_verbatim():
    test = r"""
#PYTHON
a = 27
b = 5
write("$b_i=#a$", parse=True, verbatim=True)
#END_PYTHON
"""
    assert parse(test) == "\\texttt{\\$b\\_i=27\\$}\n"


def test_matrix_latex(compiler):
    # Default matrix environment should be pmatrix.
    latex = compiler.parse(code=r"#{Matrix([[1,2],[3,4]])}")
    assert latex == r"\begin{pmatrix}1 & 2\\3 & 4\end{pmatrix}"
    latex = compiler.parse(code=r"#{latex(Matrix([[1,2],[3,4]]))}")
    assert latex == r"\begin{pmatrix}1 & 2\\3 & 4\end{pmatrix}"
    # Use matrix instead of pmatrix environment.
    latex = compiler.parse(code=r"#{latex(Matrix([[1,2],[3,4]]), mat_str='matrix')}")
    assert latex == r"\begin{matrix}1 & 2\\3 & 4\end{matrix}"


def main():
    for varname, content in globals().items():
        if varname.startswith("test_") and isinstance(content, types.FunctionType):
            os.chdir(os.path.join(dirname(ptyx.__file__), ".."))
            content()


if __name__ == "__main__":
    main()
