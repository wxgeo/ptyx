from __future__ import division, unicode_literals, absolute_import, print_function

import sys
from os import fsync
from os.path import isfile, join, normpath, split
from tempfile import NamedTemporaryFile
#import re

#~ print sys.path
sys.path.append('..')

#from latexgenerator import SyntaxTreeGenerator, Compiler#, parse
#from utilities import find_closing_bracket, round, print_sympy_expr
#from randfunc import randchoice, srandchoice, randfrac
#
#from testlib import assertEq

from ptyx import parser, main

def test_basic_test():
    with NamedTemporaryFile(suffix='.ptyx', delete=False) as f:
        f.write(
r'''\documentclass[]{scrartcl}
#SEED{120}
\begin{document}

#PYTHON
a = randint(2, 9)
b = randint(2, 9)
#END

Is $x \mapsto #{a*x+b}$ a linear function~?

\end{document}'''.encode('utf-8'))
        f.flush()
        fsync(f.fileno())
    sys.argv = ['ptyx', f.name]
    main(parser)
    folder, fname = split(f.name)
    assert isfile(join(folder, '.compile', fname, f"{fname[:-5]}.tex"))
    assert isfile(join(folder, '.compile', fname, f"{fname[:-5]}.pdf"))

if __name__ == '__main__':
    test_basic_test()