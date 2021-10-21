import sys
from os import fsync
from os.path import isfile, join, split
from tempfile import NamedTemporaryFile


from ptyx.script import parser, ptyx

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
    ptyx(parser)
    folder, fname = split(f.name)
    assert isfile(join(folder, '.compile', fname, f"{fname[:-5]}.tex"))
    assert isfile(join(folder, '.compile', fname, f"{fname[:-5]}.pdf"))

if __name__ == '__main__':
    test_basic_test()