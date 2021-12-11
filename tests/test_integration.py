import sys
from os import fsync
from pathlib import Path
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
    filename = Path(f.name)
    compile_directory = filename.parent / '.compile' / filename.stem
    for ext in ".tex", ".pdf":
        assert (compile_directory / (filename.stem + ext)).is_file()

if __name__ == '__main__':
    test_basic_test()