#!/usr/bin/env python3

# --------------------------------------
#                  pTyX
#              main script
# --------------------------------------
#    pTyX
#    Python LaTeX preprocessor
#    Copyright (C) 2009-2016  Nicolas Pourcelot
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


import argparse
import csv
import subprocess
import sys
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from ptyx import __version__
from ptyx.compilation_options import CompilationOptions
from ptyx.config import param

if TYPE_CHECKING:
    from ptyx.compilation import MultipleFilesCompilationInfo

if sys.version_info.major == 2:
    raise RuntimeError("Python 2 not supported, please update to latest python 3 version!")


class PtyxArgumentParser(argparse.ArgumentParser):
    """Parse pTyX command line interface options."""

    def __init__(self):
        super().__init__(
            prog="pTyX",
            description="Compile .ptyx files into .tex or .pdf files.",
            usage="ptyx [options] filename(s).\nTry 'ptyx --help' for more information.",
        )
        self.add_argument("filenames", nargs="+")
        group = self.add_mutually_exclusive_group()
        group.add_argument(
            "-n",
            "--number-of-documents",
            type=int,
            default=1,
            help="Number of pdf files to generate (1 by default).\n \
                       Ex: ptyx -n 5 my_file.ptyx",
        )
        group.add_argument(
            "--names",
            type=str,
            metavar="CSV_FILE",
            help="Name of a CSV file containing a column of names \
                               (and optionally a second column with forenames). \n \
                               The names will be used to generate the #NAME tag \
                               replacement value.\n \
                               Additionally, if `-n` option is not specified, \
                               default value will be the number of names in the CSV file.",
        )
        self.add_argument(
            "-r",
            "--remove",
            action="store_true",
            help="Remove the `.compile` folder after compilation.",
        )
        self.add_argument("-b", "--debug", action="store_true", help="Debug mode.")
        self.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            help="Suppress most of latex processor output.",
        )
        self.add_argument(
            "-s",
            "--start",
            default=1,
            type=int,
            help="Number of the first generated document \
                       (initial value of internal NUM counter). Default is %(default)s.",
        )
        self.add_argument(
            "-c",
            "--cat",
            action="store_true",
            help="Cat all generated pdf files inside a single one.",
        )
        self.add_argument(
            "-C",
            "--compress",
            action="store_true",
            help="Like --cat, but compress final pdf file using pdf2ps and ps2pdf."
            " Ghostscript must be present (on Linux, it is probably already installed).",
        )
        self.add_argument(
            "--view",
            action="store_true",
            help="Display pdf after compilation, using default viewer."
            " (If several files are generated, only one will be displayed.)",
        )
        self.add_argument(
            "--reorder-pages",
            choices=["brochure", "brochure-reversed", ""],
            default="",
            help="Reorder pages for printing.\n\
                Currently, only 'brochure' and 'brochure-reversed' mode are supported.\
                The `pdftk` command must be installed.\n\
                Ex: ptyx --reorder-pages=brochure-reversed -f pdf my_file.ptyx.",
        )
        group2 = self.add_mutually_exclusive_group()
        group2.add_argument(
            "--set-number-of-pages",
            metavar="N",
            type=int,
            default=0,
            help=(
                "Keep only pdf files whose pages number match N."
                " This may be useful for printing pdf later."
                " Note that the number of documents may not be respected then, so"
                " you may have to adjust the number of documents manually."
                " (Use 0 to disable (default))."
                " Using option `--same-number-of-pages` is usually a better choice."
            ),
        )
        group2.add_argument(
            "-sn",
            "--same-number-of-pages",
            action="store_true",
            help=(
                "Ensure that all documents have the same number of pages. "
                "Since the number of pages is automatically set, the requested"
                " number of documents is always respected, contrary to `--set-number-of-pages` option."
            ),
        )
        group2.add_argument(
            "-sc",
            "--same-number-of-pages-compact",
            action="store_true",
            help=(
                "Ensure that all documents have the same number of pages."
                " Since the number of pages is automatically set, the requested"
                " number of documents is always respected, contrary to `--set-number-of-pages` option."
                " Try to minimize the number of pages per document."
                " Note that this may increase significantly compilation time,"
                " compared to `--same-number-of-pages` option"
                " (the compilation may be up to 2 times slower)."
            ),
        )
        self.add_argument(
            "-nc",
            "--no-correction",
            action="store_true",
            help="Don't generate a correction of the test.",
        )
        self.add_argument(
            "--no-pdf",
            action="store_true",
            help=(
                "Don't generate Pdf files, only LaTeX ones."
                " (Generated LaTeX files are located in the `.compile` folder)."
            ),
        )
        self.add_argument(
            "-g",
            "--generate-batch-for-windows-printing",
            action="store_true",
            help="Generate a batch file for printing all pdf files using SumatraPDF.",
        )
        self.add_argument(
            "--cpu-cores",
            type=int,
            default=0,
            metavar="N_CORES",
            help="Number of cpu cores to use when compiling. (Use 0 for automatic detection (default)).",
        )
        self.add_argument(
            "--context",
            default="",
            type=str,
            help="Manually customize context (ie. internal namespace).\n \
                       Ex: ptyx --context \"a = 3; b = 2; t = 'hello'\"",
        )
        self.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    def parse_args(self, **kwargs):
        options = super().parse_args(**kwargs)
        if (options.compress or options.cat) and options.no_pdf:
            # (Note that Ghostscript must be installed for compress option.)
            raise RuntimeError("--cat or --compress option incompatible with --no-pdf option.")
        if options.debug:
            param["debug"] = True
        if options.names:
            with open(Path(options.names).expanduser().resolve()) as f:
                options.names_list = [" ".join(line) for line in csv.reader(f)]
                print("Names extracted from CSV file:")
                print(options.names_list)
            options.number_of_documents = len(options.names_list)
        else:
            options.names_list = []

        del options.names
        return options


def ptyx(parser=PtyxArgumentParser()):
    """Main pTyX procedure."""

    # First, parse all arguments (filenames, options...)
    # --------------------------------------------------

    options = CompilationOptions.load(parser.parse_args())

    if not options.filenames:
        # Exit quickly before main imports, so that `ptyx --help` is fast.
        exit(0)

    from ptyx.compilation import make_files
    from ptyx.latex_generator import Compiler

    # Time to act ! Let's compile all ptyx files...
    # ---------------------------------------------

    all_info: MultipleFilesCompilationInfo | None = None

    for input_name in options.filenames:
        # Read pTyX file.
        print(f"Reading {input_name}...")
        input_name = Path(input_name).expanduser().resolve()

        # Parse #INCLUDE tags, load extensions if needed, read seed.
        # Then generate syntax tree.
        # The syntax tree is generated only once, and will then be used
        # for all the following compilations.
        compiler = Compiler(path=input_name)
        make = partial(make_files, compiler=compiler, options=options)
        # print(compiler.state['syntax_tree'].display())

        # Compile and generate output files (tex or pdf)
        all_info = make(input_name)

        # TODO: DO NOT USE GLOBAL VARIABLE `compiler` anymore!
        #  Instead, generate a new Compiler instance each time.
        #  Then, add a parameter `syntax_tree` to make_files() and make_file(),
        #  to optionally get a `syntax_tree` instance, else create a Compiler
        #  instance inside make_files() and generate the syntax tree.

        # Keep track of the seed used.
        seed_value = compiler.seed
        seed_file_name = all_info.directory / ".seed"
        with open(seed_file_name, "w") as seed_file:
            seed_file.write(str(seed_value))

        # If any of the so-called `answer_tags` is present, compile a second
        # version of the documents with answers.
        # TODO: make an API to choose if the version with answers must be generated or not:
        # - there should be 3 modes, True, False and Auto (current mode).
        # - each mode should be accessible from the command line (add an option)
        # - it should be easy to modify mode for extensions.
        if not options.no_correction:
            answer_tags = ("ANS", "ANSWER", "ASK", "ASK_ONLY")

            tags = compiler.syntax_tree.tags
            if any(tag in tags for tag in answer_tags):
                all_info = make(input_name, correction=True, doc_ids_selection=all_info.doc_ids)

    if options.view and all_info is not None:
        if options.cat or options.compress:
            pdf_path = all_info.basename.with_suffix(".pdf")
        else:
            pdf_path = all_info.pdf_paths[0]
        subprocess.run(["xdg-open", pdf_path])


if __name__ == "__main__":
    ptyx()
