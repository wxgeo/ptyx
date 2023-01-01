import locale
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Iterable, List, Sequence, Tuple, Union

from ptyx.config import param
from ptyx.latex_generator import compiler


def append_suffix(path: Path, suffix):
    """>>> append_suffix(Path("/home/user/file"), "-corr")
    Path("/home/user/file-corr")
    """
    return path.with_name(path.name + suffix)


class _LoggedStream(object):
    """Add logging to a data stream, like stdout or stderr.

    * `logfile` is a file already opened in appending mode ;
    * `default` is default output (`sys.stdout` or `sys.stderr`).
    """

    def __init__(self, logfile, default):
        self.logfile = logfile
        self.default = default

    def write(self, s):
        self.default.write(s)
        self.logfile.write(s)

    def flush(self):
        self.default.flush()
        self.logfile.flush()


class _DevNull(object):
    def write(self, *_):
        pass

    close = flush = write


class Logging(object):
    """Context manager. All output (sys.stdout/stderr) will be logged in a file.

    Note this logging occurs in addition to standard output, which is not suppressed.
    """

    def __init__(self, logfile_name=""):
        self.logfile = open(logfile_name, "a") if logfile_name else _DevNull()

    def __enter__(self):
        self.previous = {"stdout": sys.stdout, "stderr": sys.stderr}
        sys.stdout = _LoggedStream(self.logfile, sys.stdout)
        sys.stderr = _LoggedStream(self.logfile, sys.stderr)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        assert isinstance(sys.stdout, _LoggedStream)
        assert isinstance(sys.stderr, _LoggedStream)
        sys.stdout = sys.stdout.default
        sys.stderr = sys.stderr.default

        self.logfile.close()


def execute(string, quiet=False):
    out = subprocess.Popen(string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    encoding = locale.getpreferredencoding(False)
    output = out.read().decode(encoding, errors="replace")
    sys.stdout.write(output)
    out.close()
    if not quiet:
        print(f"Command '{string}' executed.")
    return output


def make_files(
    input_name: Path,
    correction: bool = False,
    fixed_number_of_pages: bool = False,
    pages: Optional[int] = None,
    context: Optional[dict] = None,
    quiet: Optional[bool] = None,
    remove: Optional[bool] = None,
    _nums: Iterable[int] = None,
    **options,
) -> Tuple[Path, List[int]]:
    """Generate the tex and pdf files.

    - `correction`: if True, include the solutions of the exercises
    - `fixed_number_of_pages`: if True, all pdf files must have the same number of pages
    - `context`: parameters to be passed to the LaTeX generator.
    - `quiet`: if True, turn off debugging information
    - `remove`: if True, remove `.compile` folder after successful compilation.
    """

    target = options.get("number_of_documents", param["total"])
    # `_nums` is used when generating the answers of the quiz.
    # In the first pass, when generating the quizzes, some numbers may
    # have been skipped (because they don't satisfy the pages number constraint).
    if _nums is not None:
        assert correction
        _nums = list(_nums)  # make a copy
        target = len(_nums)
    if context is None:
        context = {"PTYX_WITH_ANSWERS": correction}
    formats = options.get("formats", param["default_formats"].split("+"))  # type: ignore

    # Create an empty `.compile/{input_name}` subfolder.
    compilation_dir = input_name.parent / ".compile" / input_name.stem
    if not correction and compilation_dir.is_dir():
        shutil.rmtree(compilation_dir)
    compilation_dir.mkdir(parents=True, exist_ok=True)

    # Set output base name
    output_basename = compilation_dir / input_name.stem
    if input_name.suffix != ".ptyx":
        # Avoid potential name conflict between input and output.
        output_basename = append_suffix(output_basename, "_")
    if correction:
        output_basename = append_suffix(output_basename, "-corr")

    # Information to collect
    compilation_info: Dict[int, Path] = {}
    # nums: List[int] = []
    # filenames: List[Path] = []
    pages_per_document: Dict[int, Dict[int, Path]] = {}

    # Compilation number, used to initialize random numbers' generator.
    num = options.get("start", 1)
    assert target is not None
    while len(compilation_info) < target:
        # 1. Generate context.
        if correction and _nums is not None:
            num = _nums.pop(0)
        context.update(PTYX_NUM=num)
        filename = append_suffix(output_basename, f"-{num}") if target > 1 else output_basename
        # 2. Compile.
        # Output is redirected to a `.log` file.
        logfile = append_suffix(filename, "-python.log")
        print("\nLog file:", logfile, "\n")
        with Logging(logfile if not remove else ""):
            infos = make_file(filename, formats, context=context, quiet=quiet)
        pdf_pages_number = infos.get("pages_number")

        if not correction:
            # 3. Test if the new generated file satisfies all options constraints.
            if fixed_number_of_pages:
                if pages is None:
                    # This is a bit subtle. We want all compiled documents to have
                    # the same pages number, yet we don't want to set it manually.
                    # So, we compile documents and memorize their size.
                    # We'll sort compilation results by the length of the resulting document.
                    # We'll keep one "bag" for each size of document.
                    # However, at each loop, if the compiled document is of size n,
                    # it's enough to put on the table the bag of all the n-sized and to
                    # put the new document inside. Before beginning next loop, the bag size will be tested.
                    # There's no need to have a look on the others, since they haven't change...
                    compilation_info = pages_per_document.setdefault(pdf_pages_number, {})
                elif pages != pdf_pages_number:
                    # Pages number is set manually, and don't match.
                    print(f"Warning: skipping {filename} (incorrect page number) !")
                    continue

        compilation_info[num] = filename
        num += 1

    assert len(compilation_info) == target
    filenames = list(compilation_info.values())

    # Join different versions in a single pdf, and compress if asked to do so.
    join_files(output_basename, filenames, **options)

    if options.get("generate_batch_for_windows_printing"):
        bat_file_name = input_name.parent / ("print_corr.bat" if correction else "print.bat")
        with open(bat_file_name, "w") as bat_file:
            bat_file.write(
                param["win_print_command"]
                + " ".join('"%s.pdf"' % os.path.basename(f) for f in filenames)  # type: ignore
            )

    # Copy tex/pdf file to parent directory.
    for ext in formats:
        assert ext[0] != "."
        ext = f".{ext}"
        name = output_basename.with_suffix(ext)
        if name.is_file():
            # There is only one file (only one document was generated,
            # or they were several documents, but they were joined into a single document).
            shutil.copy(name, input_name.parent)
        elif options.get("names"):
            # Rename files according to the given names' list.
            names = options["names"]
            assert len(names) == len(filenames)
            for filename, name in zip(filenames, names):
                new_name = filename.with_stem(name).name
                shutil.copy(filename.with_suffix(ext), input_name.parent / new_name)
        else:
            # Copy files without changing names.
            for filename in filenames:
                shutil.copy(filename.with_suffix(ext), input_name.parent)

    # Remove `.compile` folder if asked to.
    if remove:
        shutil.rmtree(compilation_dir)

    return output_basename, list(compilation_info.keys())


def make_file(
    output_name: Path,
    formats: Optional[Iterable] = None,
    context: Optional[Dict] = None,
    quiet: Optional[bool] = None,
):
    """Generate latex and/or pdf file from ptyx source file."""
    # TODO: Current make_file() API is a bit strange.
    # Instead of using `formats` and `plain_latex`, use `input_format` (ptyx|tex)
    # and `output_format` (tex|pdf).
    # Raise an error if input_format and output_format are both set to tex.
    infos = {}
    if formats is None:
        formats = param["default_formats"].split("+")  # type: ignore
    if context is None:
        context = {}

    # make_file() can be used to compile plain LaTeX too.
    context.setdefault("PTYX_NUM", 1)
    latex = compiler.get_latex(**context)

    texfile_name = output_name.with_suffix(".tex")
    with open(texfile_name, "w") as texfile:
        texfile.write(latex)
        if "pdf" in formats:
            texfile.flush()
            pages_number = compile_latex(texfile_name, quiet=quiet)
            infos["pages_number"] = pages_number
    return infos


def compile_latex(
    filename: Path, dest: Optional[Path] = None, quiet: Optional[bool] = False
) -> Optional[int]:
    """Compile the latex file and return the number of pages of the pdf
    (or None if not found)."""
    # By default, pdflatex use current directory as destination folder.
    # However, much of the time, we want destination folder to be the one
    # where the tex file was found.
    if dest is None:
        dest = filename.parent

    command: str = param["quiet_tex_command"] if quiet else param["tex_command"]  # type: ignore
    command += f' -output-directory "{dest}" "{filename}"'
    # ~ input('- run -')
    log = execute(command)
    # Run command twice if references were found.
    if "Rerun to get cross-references right." in log or "There were undefined references." in log:
        # ~ input('- run again -')
        log = execute(command)

    # Return the number of pages of the pdf generated.
    i = log.find("Output written on ")
    if i == -1:
        return None
    pattern = r"Output written on .+ \(([0-9]+) pages, [0-9]+ bytes\)\."
    # Line breaks may occur anywhere in the log after the file path,
    # so using re.DOTALL flag is not enough, we have to manually remove all `\n`.
    m = re.search(pattern, log[i:].replace("\n", ""))
    return int(m.group(1)) if m is not None else None


def join_files(
    output_basename: Path,
    pdfnames: Sequence[Union[Path, str]],
    seed_file_name=None,
    **options,
):
    """Join different versions in a single pdf, then compress it if asked to do so."""
    # TODO: use pathlib.Path instead
    pdf_name = str(output_basename) + ".pdf"
    number = len(pdfnames)

    if options.get("compress") or options.get("cat"):
        # Nota: don't exclude the case `number == 1`,
        # since the following actions rename file,
        # so excluding the case `number == 1` would break autoqcm scan for example.
        # pdftk and ghostscript must be installed.
        pdfnames = [str(filename) + ".pdf" for filename in pdfnames]

        files = " ".join(f'"{filename}"' for filename in pdfnames)
        if len(pdfnames) > 1:
            print("Pdftk output:")
            print(execute(f'pdftk {files} output "{pdf_name}"'))
        if options.get("remove_all"):
            for name in pdfnames:
                os.remove(name)
        if options.get("compress"):
            temp_dir = tempfile.mkdtemp()
            compressed_pdf_name = os.path.join(temp_dir, "compresse.pdf")
            command = f"""command pdftops \
                -paper match \
                -nocrop \
                -noshrink \
                -nocenter \
                -level3 \
                -q \
                "{pdf_name}" - \
                | command ps2pdf14 \
                -dEmbedAllFonts=true \
                -dUseFlateCompression=true \
                -dProcessColorModel=/DeviceCMYK \
                -dConvertCMYKImagesToRGB=false \
                -dOptimize=true \
                -dPDFSETTINGS=/prepress \
                - "{compressed_pdf_name}" """
            os.system(command)
            old_size = os.path.getsize(pdf_name)
            new_size = os.path.getsize(compressed_pdf_name)
            if new_size < old_size:
                shutil.copyfile(compressed_pdf_name, pdf_name)
                print(f"Compression ratio: {old_size / new_size:.2f}")
            else:
                print("Warning: compression failed.")
            if seed_file_name is not None:
                temp_dir = tempfile.mkdtemp()
                pdf_with_seed = os.path.join(temp_dir, "with_seed.pdf")
                execute(f'pdftk "{pdf_name}" attach_files "{seed_file_name}" output "{pdf_with_seed}"')
                shutil.copyfile(pdf_with_seed, pdf_name)
        if number > 1:
            print(f"{len(pdfnames)} files merged.")

    if options.get("reorder_pages"):
        # Use pdftk to detect how many pages has the pdf document.
        n = int(execute(f"pdftk {pdf_name} dump_data output | grep -i NumberOfPages:").strip().split()[-1])
        mode = options.get("reorder_pages")
        if mode == "brochure":
            if n % 4:
                raise RuntimeError(f"Page number is {n}, but must be a multiple of 4.")
            order = []
            for i in range(int(n / 4)):
                order.extend([2 * i + 1, 2 * i + 2, n - 2 * i - 1, n - 2 * i])
        elif mode == "brochure-reversed":
            if n % 4:
                raise RuntimeError(f"Page number is {n}, but must be a multiple of 4.")
            order = n * [0]
            for i in range(int(n / 4)):
                order[2 * i] = 4 * i + 1
                order[2 * i + 1] = 4 * i + 2
                order[n - 2 * i - 2] = 4 * i + 3
                order[n - 2 * i - 1] = 4 * i + 4
        else:
            raise NameError(f"Unknown mode {mode} for option --reorder-pages !")
        # monfichier.pdf -> monfichier-brochure.pdf
        new_name = "%s-%s.pdf" % (pdf_name[: pdf_name.index(".")], mode)
        execute("pdftk %s cat %s output %s" % (pdf_name, " ".join(str(i) for i in order), new_name))
