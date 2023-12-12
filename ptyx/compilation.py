import itertools
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Iterable, Sequence, NewType

import fitz

from ptyx.sys_info import CPU_PHYSICAL_CORES
from ptyx.compilation_options import DEFAULT_OPTIONS, CompilationOptions
from ptyx.config import param
from ptyx.latex_generator import Compiler

ANSI_RED = "\u001B[31m"
ANSI_REVERSE_RED = "\u001B[41m"
ANSI_RESET = "\u001B[0m"


DocId = NewType("DocId", int)
PageCount = NewType("PageCount", int)


def append_suffix(path: Path, suffix) -> Path:
    """>>> append_suffix(Path("/home/user/file"), "-corr")
    Path("/home/user/file-corr")
    """
    return path.with_name(path.name + suffix)


@dataclass
class SingleFileCompilationInfo:
    """Class returned when compiling a LaTeX file to PDF.

    Attributes:
        - page_count: int
          The number of pages of the generated pdf document.
        - errors: dict[str(<error-title>), str(<error-message>)]
          Errors extracted from pdftex output.
        - src: Path
          The original LaTeX file.
        - dest: Path
          The generated Pdf file.
    """

    page_count: PageCount
    errors: dict[str, str]
    src: Path
    dest: Path


@dataclass
class MultipleFilesCompilationInfo:
    """Class returned when compiling a LaTeX file to PDF."""

    basename: Path
    info_dict: dict[DocId, SingleFileCompilationInfo] = field(default_factory=dict)

    @property
    def tex_paths(self) -> list[Path]:
        return [info.src for info in self.info_dict.values()]

    @property
    def pdf_paths(self) -> list[Path]:
        return [info.dest for info in self.info_dict.values()]

    @property
    def doc_ids(self) -> list[DocId]:
        return list(self.info_dict)

    @property
    def errors(self) -> dict[DocId, dict[str, str]]:
        return {doc_id: info.errors for (doc_id, info) in self.info_dict.items()}

    @property
    def directory(self) -> Path:
        return self.basename.parent

    def __len__(self):
        return len(self.info_dict)

    def __getitem__(self, item: DocId | slice):
        if isinstance(item, slice):
            info_dict = {key: self.info_dict[key] for key in list(self.info_dict)[item]}
            return MultipleFilesCompilationInfo(basename=self.basename, info_dict=info_dict)
        else:
            return self.info_dict[item]


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

    def __init__(self, logfile_name: Path | str | None = None):
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


# def execute(string: str, quiet=False) -> str:
#     out = subprocess.Popen(string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
#     if out is not None:
#         encoding = locale.getpreferredencoding(False)
#         output = out.read().decode(encoding, errors="replace")
#         sys.stdout.write(output)
#         out.close()
#     else:
#         output = ""
#     if not quiet:
#         print(f"Command '{string}' executed.")
#     return output


def execute(command: str) -> str:
    """Execute command in shell."""
    out = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    out_bytes = out.read() if out is not None else b""
    try:
        out_str = out_bytes.decode("utf-8")
    except UnicodeDecodeError:
        out_str = out_bytes.decode("utf-8", errors="replace")
        print("Warning: UnicodeDecodeError when reading command output!")
        print(f"Command: {command!r}")
        print(f"Output: {out_str if len(out_str) < 100 else out_str[:100] + '...'}")
    return out_str


def make_files(
    ptyx_file: Path,
    number_of_documents: int = None,
    correction: bool = False,
    doc_ids_selection: Iterable[int] = None,
    compiler: Compiler = None,
    options: CompilationOptions = DEFAULT_OPTIONS,
) -> MultipleFilesCompilationInfo:
    """Generate the tex and pdf files.

    Arguments:
    - `input_name`: the path of the .pyx file.
    - `correction`: if True, include the solutions of the exercises
    - `number_of_documents`: the number of documents to generate (default: 1)
    - `doc_ids_selection` is used to manually set the documents ids when correction is set to `True`.
    - `compiler`: a Compiler instance.
       This is useful to avoid parsing the same ptyx code several times,
       when generating several documents with different parameters from
       the same source pTyX file.
    - `options`: a `CompilationOptions` instance, used to pass compilation options.

    Return a MultipleFilesCompilationInfo instance, which contains all LaTeX errors
    detected during pdftex compilation.
    """

    context = options.context
    context["PTYX_WITH_ANSWERS"] = correction

    if compiler is None:
        compiler = Compiler(path=ptyx_file)

    if doc_ids_selection is None:
        target: int = number_of_documents or options.number_of_documents
        # if correction:
        #     raise RuntimeError("Please specify documents ids list when `correction` is set to True.")
    else:
        # `doc_ids_selection` is used when generating the correction of the documents.
        # In the first pass, when generating the documents, some numbers may
        # have been skipped (because they didn't satisfy the pages number constraint).
        # if not correction:
        #     raise RuntimeError("Documents ids list should only be provided"
        #                        " when `correction` is set to True.")
        doc_ids_selection = list(doc_ids_selection)  # Important: make a copy!
        target = len(doc_ids_selection)
    assert isinstance(target, int)

    # Create an empty `.compile/{input_name}` subfolder.
    compilation_dir = ptyx_file.parent / ".compile" / ptyx_file.stem
    if not correction and compilation_dir.is_dir():
        shutil.rmtree(compilation_dir)
    compilation_dir.mkdir(parents=True, exist_ok=True)

    # Set output base name
    output_basename = compilation_dir / ptyx_file.stem
    if ptyx_file.suffix != ".ptyx":
        # Avoid potential name conflict between input and output.
        output_basename = append_suffix(output_basename, "_")
    if correction:
        output_basename = append_suffix(output_basename, "-corr")

    # Information to collect
    all_compilation_info = MultipleFilesCompilationInfo(output_basename)
    # compilation_info: Dict[int, Path] = {}
    # nums: List[int] = []
    # filenames: List[Path] = []
    # pages_per_document: {<page count>: {<document number>: <document path>}}
    pages_per_document: dict[PageCount, MultipleFilesCompilationInfo] = {}

    # Compilation number, used to initialize random numbers' generator.
    doc_id: DocId = DocId(options.start - 1)

    assert target is not None

    while len(all_compilation_info) < target:
        # ------------------------
        # Generate the LaTeX files
        # ------------------------
        # (Note that the actual number of generated files may be more than that,
        # because by default we aim to have documents with the same number of pages.)
        latex_files: dict[DocId, Path] = {}
        for _ in range(target - len(all_compilation_info)):
            # 1. Generate context.
            if doc_ids_selection is None:
                # Restart from previous doc_id value (don't reset it!)
                doc_id = DocId(doc_id + 1)
            else:
                # Overwrite default numeration, since correction numeration must match first pass.
                doc_id = DocId(doc_ids_selection.pop(0))
            context.update(PTYX_NUM=doc_id)
            filename = append_suffix(output_basename, f"-{doc_id}") if target > 1 else output_basename
            # 2. Compile to LaTeX.
            print(context)
            latex_files[doc_id] = generate_latex_file(filename, compiler, context)

        if options.no_pdf:
            return all_compilation_info

        # --------------------------------
        # Compile to pdf using parallelism
        # --------------------------------
        # Use only the physical cores, not the virtual ones !
        # with Pool(CPU_PHYSICAL_CORES) as pool:
        #     infos_list = pool.starmap(make_file, tasks)

        cpu_cores_to_use = (
            options.cpu_cores if options.cpu_cores >= 1 else min(CPU_PHYSICAL_CORES, len(latex_files))
        )
        args = [(path, None, options.quiet) for path in latex_files.values()]

        if cpu_cores_to_use > 1:
            with multiprocessing.get_context("forkserver").Pool(cpu_cores_to_use) as pool:
                compile_info_list: list[SingleFileCompilationInfo] = pool.starmap(compile_latex_to_pdf, args)
        else:
            compile_info_list = list(itertools.starmap(compile_latex_to_pdf, args))

        # pages_numbers: list[int] = [info.page_count for info in compile_info_list]

        # ---------------
        # Analyze results
        # ---------------
        info: SingleFileCompilationInfo
        for doc_id, info in zip(latex_files, compile_info_list):
            if doc_ids_selection is None:
                # 3. Test if the new generated file satisfies all options constraints.
                if options.set_number_of_pages not in (0, info.page_count):
                    # Pages number is set manually, and don't match.
                    print(f"Warning: skipping {info.src} (incorrect page number) !")
                    continue
                elif options.same_number_of_pages or options.same_number_of_pages_compact:
                    # Determine automatically the best fixed page count.
                    # This is a bit subtle. We want all compiled documents to have
                    # the same pages number, yet we don't want to set it manually.
                    # So, we compile documents and memorize their size.
                    # We'll group compilation results by the length of the resulting document.
                    # We'll keep one dictionary {document id: Path}  for each size of document.
                    # At each loop, if the compiled document is of size n,
                    # we update the dictionary of all the n-sized documents with the document ID
                    # and its path.
                    # Before beginning the next loop, the dictionary size will be checked,
                    # to see if it contains enough documents.
                    # (There's no need to have a look on the others dicts, since they haven't changed...)
                    all_compilation_info = pages_per_document.setdefault(
                        info.page_count, MultipleFilesCompilationInfo(output_basename)
                    )

            all_compilation_info.info_dict[doc_id] = info
            doc_id = DocId(doc_id + 1)
        if options.same_number_of_pages_compact:
            # In compact mode, we try to minimize the number of pages of the generated documents.
            # To not increase too drastically the time of compilation, we adopt the following heuristic:
            # we'll use the shorter documents, if their frequency exceed 25% of the total documents.
            total = sum(len(compil_info.doc_ids) for compil_info in pages_per_document.values())
            for page_count in sorted(pages_per_document):
                if len(pages_per_document[page_count].doc_ids) > total / 4:
                    all_compilation_info = pages_per_document[page_count]
                    break
            else:
                # Exceptionally, if the length of each document is highly variable, each page count value
                # may occur less than 25%. Then, we'll select the most frequent page count.
                for compil_info in pages_per_document.values():
                    if len(compil_info.doc_ids) > len(all_compilation_info.doc_ids):
                        all_compilation_info = compil_info

            if len(all_compilation_info) > target:
                all_compilation_info = all_compilation_info[:target]

        elif options.same_number_of_pages:
            for compil_info in pages_per_document.values():
                if len(compil_info.doc_ids) > len(all_compilation_info.doc_ids):
                    all_compilation_info = compil_info

    assert len(all_compilation_info) == target, len(all_compilation_info)
    filenames = all_compilation_info.pdf_paths

    # Join different versions in a single pdf, and compress if asked to do so.
    join_files(output_basename, filenames, options)

    if options.generate_batch_for_windows_printing:
        bat_file_name = ptyx_file.parent / ("print_corr.bat" if correction else "print.bat")
        with open(bat_file_name, "w") as bat_file:
            bat_file.write(param["win_print_command"] + " ".join(f'"{f.name}.pdf"' for f in filenames))

    # Copy pdf file/files to parent directory.
    _copy_file_to_parent("pdf", filenames, ptyx_file, output_basename, options)

    # Remove `.compile` folder if asked to.
    if options.remove:
        shutil.rmtree(compilation_dir)

    return all_compilation_info


def _copy_file_to_parent(
    ext: str, filenames: list[Path], input_name: Path, output_basename: Path, options: CompilationOptions
) -> None:
    assert ext[0] != "."
    ext = f".{ext}"
    name = output_basename.with_suffix(ext)
    if name.is_file():
        # There is only one file (only one document was generated,
        # or they were several documents, but they were joined into a single document).
        shutil.copy(name, input_name.parent)
    elif options.names_list:
        # Rename files according to the given names' list.
        assert len(options.names_list) == len(filenames)
        for filename, stem in zip(filenames, options.names_list):
            new_name = filename.with_stem(stem).name
            shutil.copy(filename.with_suffix(ext), input_name.parent / new_name)
    else:
        # Copy files without changing names.
        for filename in filenames:
            shutil.copy(filename.with_suffix(ext), input_name.parent)


def generate_latex_file(
    output_name: Path,
    compiler: Compiler,
    context: Optional[dict] = None,
    log=True,
) -> Path:
    """Generate latex from ptyx source file."""
    if log:
        # Output is redirected to a `.log` file.
        logfile: Optional[Path] = append_suffix(output_name, "-python.log")
        print("\nLog file:", logfile, "\n")
    else:
        logfile = None

    with Logging(logfile):
        if context is None:
            context = {}

        context.setdefault("PTYX_NUM", 1)
        latex = compiler.get_latex(**context)

        texfile_path = output_name.with_suffix(".tex")
        with open(texfile_path, "w") as texfile:
            texfile.write(latex)
        return texfile_path


def compile_ptyx_file(
    ptyx_file: Path,
    output_name: Path,
    context: Optional[dict] = None,
    quiet: Optional[bool] = None,
) -> SingleFileCompilationInfo | None:
    """Generate latex and/or pdf file from ptyx source file.

    Output name may be either a LaTeX file, or a Pdf file.
    - If output is a Pdf file, return a SingleFileCompilationInfo, including LaTeX compilation error.
    - Else, if output is only LaTeX, return None.

    Note that when output format is Pdf, a LaTeX file will also be generated in the same directory.
    """
    compiler = Compiler(path=ptyx_file)
    latex_file = generate_latex_file(output_name, compiler=compiler, context=context)
    return compile_latex_to_pdf(latex_file, quiet=quiet) if output_name.suffix == ".pdf" else None


def _print_latex_errors(out: str, filename: Path) -> dict[str, str]:
    """Filter pdftex output, and print only errors, highlighting import stuff.

    Return a dictionary: {error_title: error_message}
    """
    print(f"File {filename} compiled.")
    is_error_message = False
    is_first_error_line = False
    error_type = ""
    errors: dict[str, str] = {}
    error_title = ""
    error_message: list[str] = []
    for line in out.split("\n"):
        if line.startswith("!"):
            # New LaTeX error found!
            print(f"{ANSI_RED}{line}{ANSI_RESET}")
            is_error_message = True
            is_first_error_line = True
            error_type = line
            error_title = line.lstrip("! ")
            error_message = []
        elif is_error_message:
            # This is the continuation of the same error.
            error_message.append(line)
            if is_first_error_line:
                if error_type == "! Undefined control sequence.":
                    # The undefined macro is the last displayed on this line.
                    pos = line.rfind("\\")
                    if pos == -1:
                        print("Warning (pTyX): can't find any macro on previous line!")
                    else:
                        print("".join((line[:pos], ANSI_REVERSE_RED, line[pos:], ANSI_RESET)))
                is_first_error_line = False
            else:
                print(line)
            if line.startswith("l."):
                # The error ends here, with error line number.
                is_error_message = False
                errors[error_title] = "\n".join(error_message)

    print(f"Full log written on {filename.with_suffix('.log')}.")
    return errors


def compile_latex_to_pdf(
    filename: Path, dest: Optional[Path] = None, quiet: Optional[bool] = False
) -> SingleFileCompilationInfo:
    """Compile the latex file.

    Return a SingleFileCompilationInfo instance.
    """
    # By default, pdflatex use current directory as destination folder.
    # However, much of the time, we want destination folder to be the one
    # where the tex file was found.
    if dest is None:
        dest = filename.parent

    command = _build_command(filename, dest, quiet)
    out = execute(command)
    errors: dict[str, str] = _print_latex_errors(out, filename)
    # Run command twice if references were found.
    if "Rerun to get cross-references right." in out or "There were undefined references." in out:
        # ~ input('- run again -')
        out = execute(command)
        errors = _print_latex_errors(out, filename)
    return SingleFileCompilationInfo(
        page_count=_extract_page_number(out), errors=errors, src=filename, dest=filename.with_suffix(".pdf")
    )


def _build_command(filename: Path, dest: Path, quiet: Optional[bool] = False) -> str:
    """Generate the command used to compile the LaTeX file."""
    command: str = param["quiet_tex_command"] if quiet else param["tex_command"]
    command += f' -output-directory "{dest}" "{filename}"'
    return command


def _extract_page_number(pdflatex_log: str) -> PageCount:
    """Return the number of pages of the pdf generated, or -1 if it was not found."""
    i = pdflatex_log.find("Output written on ")
    if i == -1:
        return PageCount(-1)
    pattern = r"Output written on .+ \(([0-9]+) pages, [0-9]+ bytes\)\."
    # Line breaks may occur anywhere in the log after the file path,
    # so using re.DOTALL flag is not enough, we have to manually remove all `\n`.
    m = re.search(pattern, pdflatex_log[i:].replace("\n", ""))
    return PageCount(int(m.group(1)) if m is not None else -1)


def join_files(
    pdf_name: Path,
    pdf_list: Sequence[Path | str],
    options: CompilationOptions,
):
    """Join different versions in a single pdf, then compress it if asked to do so.

    For compression, ghostscript must be installed.
    """
    pdf_name = pdf_name.with_suffix(".pdf")

    if options.compress or options.cat:
        # Nota: don't exclude the case `number == 1`,
        # since the following actions rename file,
        # so excluding the case `number == 1` would break autoqcm scan for example.
        # For compression, ghostscript must be installed.

        if len(pdf_list) > 1:
            _join_pdf_files(pdf_name, pdf_list)
        if options.compress:
            # Need Ghostscript.
            _compress_pdf(pdf_name)
        if len(pdf_list) > 1:
            print(f"{len(pdf_list)} files merged.")

    if options.reorder_pages:
        # Need Pdftk.
        _reorder_pdf(pdf_name, options.reorder_pages)


def _join_pdf_files(output_basename: Path | str, pdfnames: Sequence[Path | str]) -> None:
    """Join all the generated pdf files into one file."""
    # pdf: Document
    if len(pdfnames) == 0:
        print("Warning: no PDF files to join.")
        return
    with fitz.Document() as pdf:
        for pdfname in pdfnames:
            # f: Document
            with fitz.Document(pdfname) as f:
                pdf.insert_pdf(f)
        pdf.save(output_basename)


def _compress_pdf(pdf_name: Path) -> None:
    """Compress pdf using Ghostscript (which must have been installed previously)."""
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


def _reorder_pdf(pdf_name: Path, mode: str) -> None:
    """Reorder pdf pages using Pdftk (which must have been installed previously)."""
    # Use pdftk to detect how many pages has the pdf document.
    n = int(execute(f"pdftk {pdf_name} dump_data output | grep -i NumberOfPages:").strip().split()[-1])
    if mode == "brochure":
        if n % 4:
            raise RuntimeError(f"The number of pages is {n}, while it must be a multiple of 4.")
        order = []
        for i in range(int(n / 4)):
            order.extend([2 * i + 1, 2 * i + 2, n - 2 * i - 1, n - 2 * i])
    elif mode == "brochure-reversed":
        if n % 4:
            raise RuntimeError(f"The number of pages is {n}, while it must be a multiple of 4.")
        order = n * [0]
        for i in range(int(n / 4)):
            order[2 * i] = 4 * i + 1
            order[2 * i + 1] = 4 * i + 2
            order[n - 2 * i - 2] = 4 * i + 3
            order[n - 2 * i - 1] = 4 * i + 4
    else:
        raise NameError(f"Unknown mode {mode} for option --reorder-pages !")
    # monfichier.pdf -> monfichier-brochure.pdf
    new_name = "%s-%s.pdf" % (pdf_name.stem, mode)
    execute("pdftk %s cat %s output %s" % (pdf_name, " ".join(str(i) for i in order), new_name))
