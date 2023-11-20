import sys
from os import fsync
from pathlib import Path
from tempfile import NamedTemporaryFile

from ptyx.compilation import make_files, make_file
from ptyx.latex_generator import compiler
from ptyx.script import ptyx


PTYX_SAMPLE = r"""\documentclass[]{scrartcl}
#SEED{120}
\begin{document}

#PYTHON
a = randint(2, 9)
b = randint(2, 9)
#END

Is $x \mapsto #{a*x+b}$ a linear function~?

\end{document}
"""


def test_basic_test():
    with NamedTemporaryFile(suffix=".ptyx", delete=False) as f:
        f.write(PTYX_SAMPLE.encode("utf-8"))
        f.flush()
        fsync(f.fileno())
    sys.argv = ["ptyx", f.name]
    ptyx()
    filename = Path(f.name)
    compile_directory = filename.parent / ".compile" / filename.stem
    for ext in ".tex", ".pdf":
        assert (compile_directory / (filename.stem + ext)).is_file()


def test_make_file(tmp_path):
    print(tmp_path)
    ptyx_path: Path = tmp_path / "test.ptyx"
    with open(ptyx_path, "w", encoding="utf8") as f:
        f.write(PTYX_SAMPLE)
        f.flush()
        fsync(f.fileno())
    compiler.reset()
    compiler.parse(path=ptyx_path)
    pdf_path = ptyx_path.with_suffix(".pdf")
    make_file(pdf_path)
    assert pdf_path.is_file()


def test_make_files(tmp_path):
    print(tmp_path)
    ptyx_path: Path = tmp_path / "test.ptyx"
    with open(ptyx_path, "w", encoding="utf8") as f:
        f.write(PTYX_SAMPLE)
        f.flush()
        fsync(f.fileno())
    compiler.reset()
    compiler.parse(path=ptyx_path)
    pdf_path = ptyx_path.with_suffix(".pdf")
    make_files(ptyx_path, number_of_documents=2)
    assert (tmp_path / "test-1.pdf").is_file()
    assert (tmp_path / "test-2.pdf").is_file()
    assert not pdf_path.is_file()
    make_files(ptyx_path, number_of_documents=2, cat=True)
    assert pdf_path.is_file()


if __name__ == "__main__":
    test_basic_test()
