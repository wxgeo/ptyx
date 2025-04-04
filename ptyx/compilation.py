import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Iterable, Sequence, NewType, Callable, Any

import fitz

from ptyx.pretty_print import print_error
from ptyx.sys_info import CPU_PHYSICAL_CORES
from ptyx.compilation_options import DEFAULT_OPTIONS, CompilationOptions
from ptyx.config import param
from ptyx.latex_generator import Compiler
from ptyx.utilities import force_hardlink_to

ANSI_RED = "\u001B[31m"
ANSI_REVERSE_RED = "\u001B[41m"
ANSI_RESET = "\u001B[0m"


DocId = NewType("DocId", int)
PageCount = NewType("PageCount", int)


# def append_suffix(path: Path, suffix) -> Path:
#     """>>> append_suffix(Path("/home/user/file"), "-corr")
#     Path("/home/user/file-corr")
#     """
#     return path.with_name(path.name + suffix)


class CompilationState(Enum):
    STARTED = auto()
    GENERATING_DOCS = auto()
    MERGING_DOCS = auto()
    COMPLETED = auto()


@dataclass
class CompilationProgress:
    """This class is used to provide feedback about the compilation progress."""

    generated_latex_docs: int
    compiled_pdf_docs: int
    target: int
    state: CompilationState


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

    compilation_dir: Path
    basename: str
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
        return self.compilation_dir

    def sort(self) -> None:
        self.info_dict = {doc_id: self.info_dict[doc_id] for doc_id in sorted(self.info_dict)}

    def __len__(self):
        return len(self.info_dict)

    def __getitem__(self, item: DocId | slice):
        if isinstance(item, slice):
            info_dict = {key: self.info_dict[key] for key in list(self.info_dict)[item]}
            return MultipleFilesCompilationInfo(
                compilation_dir=self.compilation_dir, basename=self.basename, info_dict=info_dict
            )
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
    output_basename: str = None,
    number_of_documents: int = None,
    correction: bool = False,
    doc_ids_selection: Iterable[int] = None,
    compiler: Compiler = None,
    options: CompilationOptions = DEFAULT_OPTIONS,
    feedback_func: Callable[[CompilationProgress], Any] | None = None,
) -> tuple[MultipleFilesCompilationInfo, Compiler]:
    """Generate the tex and pdf files.

    Arguments:
    - `ptyx_file`: the path of the .ptyx file.
    - `output_basename`: the basename of the output file.
       For example, if `output_basename` is "doc", the latex file will be named "doc.tex",
        and the pdf file "doc.pdf".
    - `correction`: if True, include the solutions of the exercises
    - `number_of_documents`: the number of documents to generate (default: 1)
    - `doc_ids_selection` is used to manually set the documents ids when correction is set to `True`.
    - `compiler`: a Compiler instance.
       This is useful to avoid parsing the same ptyx code several times,
       when generating several documents with different parameters from
       the same source pTyX file.
    - `options`: a `CompilationOptions` instance, used to pass compilation options.
    - `feedback_func`: a function called each time the compilation state changed, typically
       used to display compilation progress. It will receive a `CompilationProgress` instance
       as argument. (No return is expected.)

    Return a MultipleFilesCompilationInfo instance, which contains all LaTeX errors
    detected during pdftex compilation.
    """

    if ptyx_file.suffix != ".ptyx":
        print_error(f"Invalid file extension, should be .ptyx: '{ptyx_file}'.")
        sys.exit(1)

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

    def feedback(generated_latex_docs: int, compiled_pdf_docs: int, state: CompilationState) -> None:
        if feedback_func is not None:
            feedback_func(
                CompilationProgress(
                    generated_latex_docs=generated_latex_docs,
                    compiled_pdf_docs=compiled_pdf_docs,
                    target=target,
                    state=state,
                )
            )

    feedback(
        generated_latex_docs=0,
        compiled_pdf_docs=0,
        state=CompilationState.STARTED,
    )

    # Create an empty `.compile/{input_name}` subfolder.
    compilation_dir = ptyx_file.parent / ".compile" / ptyx_file.stem
    if not correction and compilation_dir.is_dir():
        shutil.rmtree(compilation_dir)
    compilation_dir.mkdir(parents=True, exist_ok=True)

    # Set output base name
    if output_basename is None:
        output_basename = ptyx_file.stem
        if correction:
            output_basename += "-corr"

    # Information to collect
    all_compilation_info = MultipleFilesCompilationInfo(compilation_dir, output_basename)
    # compilation_info: Dict[int, Path] = {}
    # nums: List[int] = []
    # filenames: List[Path] = []
    # pages_per_document: {<page count>: {<document number>: <document path>}}
    pages_per_document: dict[PageCount, MultipleFilesCompilationInfo] = {}

    # Compilation number, used to initialize random numbers' generator.
    doc_id: DocId = DocId(options.start - 1)

    assert target is not None

    cpu_cores_to_use = (
        # Use only the physical cores, not the virtual ones !
        options.cpu_cores
        if options.cpu_cores >= 1
        else min(CPU_PHYSICAL_CORES, target)
    )
    with concurrent.futures.ProcessPoolExecutor(max_workers=cpu_cores_to_use) as executor:
        while len(all_compilation_info) < target:
            # ------------------------
            # Generate the LaTeX files
            # ------------------------
            # (Note that the actual number of generated files may be more than that,
            # because by default we aim to have documents with the same number of pages.)
            futures: dict[concurrent.futures.Future, DocId] = {}
            number_of_missing_docs: int = target - len(all_compilation_info)
            for new_latex_docs_count in range(number_of_missing_docs):
                # 1. Generate context.
                if doc_ids_selection is None:
                    # Restart from previous doc_id value (don't reset it!)
                    doc_id = DocId(doc_id + 1)
                else:
                    # Overwrite default numeration, since correction numeration must match first pass.
                    doc_id = DocId(doc_ids_selection.pop(0))
                context.update(PTYX_NUM=doc_id)
                filename = compilation_dir / (
                    f"{output_basename}-{doc_id}.tex" if target > 1 else f"{output_basename}.tex"
                )
                # 2. Compile to LaTeX.
                print(context)
                latex_file: Path = generate_latex_file(filename, compiler, context)
                feedback(
                    generated_latex_docs=len(all_compilation_info) + new_latex_docs_count,
                    compiled_pdf_docs=len(all_compilation_info),
                    state=CompilationState.GENERATING_DOCS,
                )
                if not options.no_pdf:
                    # Compile to pdf using parallelism.
                    # Tasks are added to executor, and executed in parallel.
                    future = executor.submit(compile_latex_to_pdf, latex_file, None, quiet=options.quiet)
                    futures[future] = doc_id

            if options.no_pdf:
                return all_compilation_info, compiler

            # ---------------
            # Analyze results
            # ---------------
            for future in concurrent.futures.as_completed(futures):
                info: SingleFileCompilationInfo = future.result()
                doc_id = futures[future]
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
                            info.page_count, MultipleFilesCompilationInfo(compilation_dir, output_basename)
                        )

                all_compilation_info.info_dict[doc_id] = info
                doc_id = DocId(doc_id + 1)
                if options.same_number_of_pages_compact:
                    # In compact mode, we try to minimize the number of pages of the generated documents.
                    # To not increase too drastically the time of compilation, we adopt the following heuristic:
                    # we'll use the shortest documents, if their frequency exceed 25% of the total documents.
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

                elif options.same_number_of_pages:
                    for compil_info in pages_per_document.values():
                        if len(compil_info.doc_ids) > len(all_compilation_info.doc_ids):
                            all_compilation_info = compil_info

                feedback(
                    generated_latex_docs=target,
                    compiled_pdf_docs=len(all_compilation_info),
                    state=CompilationState.GENERATING_DOCS,
                )

    # Sort generated documents by id, before joining them together.
    all_compilation_info.sort()

    if len(all_compilation_info) > target:
        all_compilation_info = all_compilation_info[:target]

    assert len(all_compilation_info) == target, len(all_compilation_info)
    filenames = all_compilation_info.pdf_paths

    feedback(
        generated_latex_docs=target,
        compiled_pdf_docs=target,
        state=CompilationState.MERGING_DOCS,
    )

    # If needed, join different versions in a single pdf, and compress if asked to do so.
    # (Ghostscript is needed for compression.)
    join_files_if_needed(compilation_dir / f"{output_basename}.pdf", filenames, options)

    if options.generate_batch_for_windows_printing:
        bat_file_name = ptyx_file.parent / ("print_corr.bat" if correction else "print.bat")
        with open(bat_file_name, "w") as bat_file:
            bat_file.write(param["win_print_command"] + " ".join(f'"{f.name}.pdf"' for f in filenames))

    # Copy pdf file/files to parent directory.
    _link_file_to_parent("pdf", filenames, ptyx_file, compilation_dir, output_basename, options)

    # Remove `.compile` folder if asked to.
    if options.remove:
        shutil.rmtree(compilation_dir)
    feedback(
        generated_latex_docs=target,
        compiled_pdf_docs=target,
        state=CompilationState.COMPLETED,
    )
    return all_compilation_info, compiler


def _link_file_to_parent(
    ext: str,
    filenames: list[Path],
    input_name: Path,
    compilation_dir: Path,
    output_basename: str,
    options: CompilationOptions,
) -> None:
    """Create a hardlink to files in parent."""
    # TODO: this code needs to be rewritten, or at least reviewed.
    if ext[0] != ".":
        ext = f".{ext}"
    if (target := (compilation_dir / output_basename).with_suffix(ext)).is_file():
        # There is only one file (only one document was generated,
        # or they were several documents, but they were joined into a single document).
        # shutil.copy(target, input_name.parent)
        force_hardlink_to(input_name.parent / target.name, target)
    elif options.names_list:
        # Rename files according to the given names' list.
        assert len(options.names_list) == len(filenames)
        for filename, stem in zip(filenames, options.names_list):
            new_name = filename.with_stem(stem).name
            # shutil.copy(filename.with_suffix(ext), input_name.parent / new_name)
            force_hardlink_to(input_name.parent / new_name, filename.with_suffix(ext))
    else:
        # Copy files without changing names.
        for filename in filenames:
            # shutil.copy(filename.with_suffix(ext), input_name.parent)
            target = filename.with_suffix(ext)
            force_hardlink_to(input_name.parent / target.name, target)


def generate_latex_file(
    texfile_path: Path,
    compiler: Compiler,
    context: Optional[dict] = None,
    log=True,
) -> Path:
    """Generate latex from ptyx source file."""
    assert texfile_path.suffix == ".tex", texfile_path
    if log:
        # Output is redirected to a `.log` file.
        logfile: Optional[Path] = texfile_path.parent / f"{texfile_path.stem}-python.log"
        print("\nLog file:", logfile, "\n")
    else:
        logfile = None

    with Logging(logfile):
        if context is None:
            context = {}

        context.setdefault("PTYX_NUM", 1)
        latex = compiler.get_latex(**context)

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
    latex_file = generate_latex_file(output_name.with_suffix(".tex"), compiler=compiler, context=context)
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

    - `filename` is the latex file to compile.
    - `dest` is the destination folder, where the pdf file will be generated.

    Return a SingleFileCompilationInfo instance.
    """
    assert filename.suffix == ".tex", filename
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


def join_files_if_needed(
    pdf_name: Path,
    pdf_list: Sequence[Path],
    options: CompilationOptions,
):
    """Join different versions in a single pdf, then compress it if asked to do so.

    For compression, ghostscript must be installed.
    """
    assert pdf_name.suffix == ".pdf", pdf_name

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


def _join_pdf_files(output_basename: Path, pdfnames: Sequence[Path]) -> None:
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
    # TODO: use subprocess.run (with PIPE)
    # https://stackoverflow.com/questions/13332268/how-to-use-subprocess-command-with-pipes
    # Command `command`: https://www.ibm.com/docs/en/aix/7.3?topic=c-command-command
    command = f"""command pdftops \
                -paper match \
                -nocrop \
                -noshrink \
                -nocenter \
                -level3 \
                -q \
                "{pdf_name}" - \
                | command ps2pdf \
                -dEmbedAllFonts=true \
                -dUseFlateCompression=true \
                -dProcessColorModel=/DeviceCMYK \
                -dConvertCMYKImagesToRGB=false \
                -dOptimize=true \
                -dPDFSETTINGS=/prepress \
                - "{compressed_pdf_name}" """
    exit_status = os.system(command)
    old_size = os.path.getsize(pdf_name)
    if exit_status == 0 and (new_size := os.path.getsize(compressed_pdf_name)) < old_size:
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
