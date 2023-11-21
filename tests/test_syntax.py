import os
import types
from os.path import dirname

import ptyx
from ptyx.latex_generator import SyntaxTreeGenerator, Compiler  # , parse
from ptyx.randfunc import randchoice, srandchoice, randfrac
from ptyx.utilities import latex_verbatim

TEST_DIR = dirname(__file__)


def test_syntax_tree():
    s = SyntaxTreeGenerator()
    text = "hello world !"
    s.generate_tree(text)
    tree = """
+ Node ROOT
  - text: 'hello world !'
""".strip()
    assert s.syntax_tree.display(color=False) == tree

    text = "#IF{a>0}some text here#ELIF{b>0}some more text#ELSE variable value is #variable not #{variable+1} !#END"
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

    text = "#PYTHON#some comment\nvariable = 2\n#END#ASSERT{variable == 2}"
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
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == "2some text here ok"


def test_hash():
    test = "#{a=5}###a####a"
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == "5#5##a"


# ADD A TEST :
# "#IF{True}message 1#IF{False}message 2#ELSE message 3" -> test that 'message 3' is printed.


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
    test = r"""\newcommand{\rep}[1]{\ding{114}\,\,#1\hfill}"""
    result = test
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


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
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == result


def test_hashtag_inside_python_block():
    test = """
    #PYTHON
    s = "#" # This should not be a problem.
    t = "#test" # Neither this.
    #END
    #s #t
    """
    c = Compiler()
    latex = c.parse(code=test)
    assert latex == "\n    # #test\n    "


def test_write():
    c = Compiler()
    test = r"""
#PYTHON
a = 5
write(r"$\#$ ")
write("#a ")
write("#a", parse=True)
#END
"""
    latex = c.parse(code=test)
    assert latex == "$\\#$ #a 5\n"


def test_latex_verbatim():
    s = latex_verbatim(r" \emph{$a^2 +  b_i$}" "\n" r"   x\ ")
    assert s == (
        r"\texttt{~\textbackslash{}emph\{\$a\textasciicircum{}2~+~~b\_i\$\}\linebreak"
        r"\phantom{}~~~x\textbackslash{}~}"
    )


def test_write_verbatim():
    c = Compiler()
    test = r"""
#PYTHON
a = 27
b = 5
write("$b_i=#a$", parse=True, verbatim=True)
#END
"""
    latex = c.parse(code=test)
    assert latex == "\\texttt{\\$b\\_i=27\\$}\n"


def main():
    for varname, content in globals().items():
        if varname.startswith("test_") and isinstance(content, types.FunctionType):
            os.chdir(os.path.join(dirname(ptyx.__file__), ".."))
            content()


if __name__ == "__main__":
    main()
