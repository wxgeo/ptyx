import sys
from os import fsync
from pathlib import Path
from tempfile import NamedTemporaryFile

from ptyx.compilation_options import CompilationOptions

from ptyx.compilation import make_files, compile_ptyx_file
from ptyx.latex_generator import Compiler
from ptyx.script import ptyx


PTYX_SAMPLE = r"""\documentclass[]{scrartcl}
#SEED{120}
\begin{document}

#PYTHON
a = randint(2, 9)
b = randint(2, 9)
#END_PYTHON

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


def test_compile_ptyx_file(tmp_path):
    print(tmp_path)
    ptyx_path: Path = tmp_path / "test.ptyx"
    with open(ptyx_path, "w", encoding="utf8") as f:
        f.write(PTYX_SAMPLE)
        f.flush()
        fsync(f.fileno())
    tex_path = ptyx_path.with_suffix(".tex")
    pdf_path = ptyx_path.with_suffix(".pdf")
    compile_ptyx_file(ptyx_path, tex_path)
    assert tex_path.is_file()
    assert not pdf_path.is_file()
    tex_path.unlink()
    compile_ptyx_file(ptyx_path, pdf_path)
    assert tex_path.is_file()
    assert pdf_path.is_file()


def test_make_files(tmp_path):
    print(tmp_path)
    ptyx_path: Path = tmp_path / "test.ptyx"
    with open(ptyx_path, "w", encoding="utf8") as f:
        f.write(PTYX_SAMPLE)
        f.flush()
        fsync(f.fileno())
    compiler = Compiler()
    compiler.parse(path=ptyx_path)
    pdf_path = ptyx_path.with_suffix(".pdf")
    make_files(ptyx_path, compiler=compiler, number_of_documents=2)
    assert (tmp_path / "test-1.pdf").is_file()
    assert (tmp_path / "test-2.pdf").is_file()
    assert not pdf_path.is_file()
    make_files(ptyx_path, compiler=compiler, options=CompilationOptions(cat=True))
    assert pdf_path.is_file()
    # Test a new compilation without removing generated files.
    # Use `compress` option this time, so Ghostscript needs to be installed.
    make_files(ptyx_path, compiler=compiler, options=CompilationOptions(compress=True))
    assert pdf_path.is_file()


def make_files_no_pdf(tmp_path):
    print(tmp_path)
    ptyx_path: Path = tmp_path / "test.ptyx"
    with open(ptyx_path, "w", encoding="utf8") as f:
        f.write(PTYX_SAMPLE)
        f.flush()
        fsync(f.fileno())
    make_files(ptyx_path, options=CompilationOptions(no_pdf=True))
    assert (tmp_path / f".compile/{ptyx_path.stem}/test-1.tex").is_file()
    assert (tmp_path / f".compile/{ptyx_path.stem}/test-2.tex").is_file()
    assert not (tmp_path / f".compile/{ptyx_path.stem}/test-1.pdf").is_file()
    assert not (tmp_path / f".compile/{ptyx_path.stem}/test-2.pdf").is_file()


if __name__ == "__main__":
    test_basic_test()
