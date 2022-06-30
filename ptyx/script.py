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
import sys
from ast import literal_eval
from pathlib import Path

from ptyx import __version__
from ptyx.compilation import make_files
from ptyx.config import param
from ptyx.latex_generator import compiler
from ptyx.utilities import pth

if sys.version_info.major == 2:
    raise RuntimeError("Python version 3.8+ is needed !")


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
            help="Number of pdf files to generate. Default is %s.\n \
                       Ex: ptyx -n 5 my_file.ptyx"
            % param["total"],
        )
        group.add_argument(
            "--names",
            metavar="CSV_FILE",
            help="Name of a CSV file containing a column of names \
                               (and optionally a second column with forenames). \n \
                               The names will be used to generate the #NAME tag \
                               replacement value.\n \
                               Additionally, if `-n` option is not specified, \
                               default value will be the number of names in the CSV file.",
        )
        self.add_argument(
            "-f",
            "--formats",
            default=param["default_formats"],
            choices=param["formats"],
            help="Output format. Default is %(default)s.\n" "Ex: ptyx -f tex my_file.ptyx",
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
            help="Cat all generated pdf files inside a single one. \
                       The pdftk command must be installed.",
        )
        self.add_argument(
            "-C",
            "--compress",
            action="store_true",
            help="Like --cat, but compress final pdf file using pdf2ps and ps2pdf.",
        )
        self.add_argument(
            "--reorder-pages",
            choices=["brochure", "brochure-reversed"],
            help="Reorder pages for printing.\n\
                Currently, only 'brochure' and 'brochure-reversed' mode are supported.\
                The `pdftk` command must be installed.\n\
                Ex: ptyx --reorder-pages=brochure-reversed -f pdf my_file.ptyx.",
        )
        group2 = self.add_mutually_exclusive_group()
        group2.add_argument(
            "-p",
            "--fixed_number_of_pages",
            metavar="N",
            nargs="?",
            type=int,
            default=argparse.SUPPRESS,
            help="Keep only pdf files whose pages number match N. \
                This may be useful for printing pdf later. \
                Note that the number of documents may not be respected then, so \
                you may have to adjust the number of documents manually.",
        )
        group2.add_argument(
            "-P",
            "--auto-fixed_number_of_pages",
            action="store_true",
            help=(
                "Ensure that all documents have the same number of pages. "
                "The number of documents is respected."
            ),
        )
        self.add_argument(
            "-nc",
            "--no-correction",
            action="store_true",
            help="Don't generate a correction of the test.",
        )
        self.add_argument(
            "-g",
            "--generate-batch-for-windows-printing",
            action="store_true",
            help="Generate a batch file for printing all pdf files using SumatraPDF.",
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
        options.formats = options.formats.split("+")
        if options.compress or options.cat:
            # pdftk and ghostscript must be installed.
            if "pdf" not in options.formats:
                raise RuntimeError("--cat or --compress option invalid unless pdf output is selected.")
        if options.debug:
            param["debug"] = True
        if options.names:
            with open(pth(options.names)) as f:
                options.names = [" ".join(line) for line in csv.reader(f)]
                print("Names extracted from CSV file:")
                print(options.names)
            options.number_of_documents = len(options.names)
        else:
            options.names = []
        if options.number_of_documents is None:
            options.number_of_documents = param["total"]
        return options


def ptyx(parser=PtyxArgumentParser()):
    """Main pTyX procedure."""
    # First, parse all arguments (filenames, options...)
    # --------------------------------------------------
    options = parser.parse_args()

    # TODO: remove kwargs and explicitly pass arguments, to verify types.
    kwargs = vars(options)
    if "fixed_number_of_pages" in kwargs:
        kwargs["pages"] = kwargs["fixed_number_of_pages"]
        kwargs["fixed_number_of_pages"] = True
    else:
        kwargs["fixed_number_of_pages"] = False

    context = {}
    for keyval in kwargs.pop("context", "").split(";"):
        if keyval.strip():
            key, val = keyval.split("=", 1)
            key = key.strip()
            if not str.isidentifier(key):
                raise NameError(f"{key} is not a valid variable name.")
            context[key] = literal_eval(val)

    # Time to act ! Let's compile all ptyx files...
    # ---------------------------------------------

    for input_name in options.filenames:
        # Read pTyX file.
        print(f"Reading {input_name}...")
        input_name = Path(input_name).expanduser().resolve()
        compiler.read_file(input_name)
        # Parse #INCLUDE tags, load extensions if needed, read seed.
        compiler.preparse()

        # Generate syntax tree.
        # The syntax tree is generated only once, and will then be used
        # for all the following compilations.
        compiler.generate_syntax_tree()
        # print(compiler.state['syntax_tree'].display())

        # Compile and generate output files (tex or pdf)
        output_basename, nums = make_files(input_name, **kwargs)

        # Keep track of the seed used.
        seed_value = compiler.seed
        seed_file_name = output_basename.parent / ".seed"
        with open(seed_file_name, "w") as seed_file:
            seed_file.write(str(seed_value))

        # If any of the so-called `ANSWER_tags` is present, compile a second
        # version of the documents with answers.
        # TODO: make an API to choose if the version with answers must be generated or not:
        # - there should be 3 modes, True, False and Auto (current mode).
        # - each mode should be accessible from the command line (add an option)
        # - it should be easy to modify mode for extensions.
        if not options.no_correction:
            ANSWER_tags = ("ANS", "ANSWER", "ASK", "ASK_ONLY")

            tags = compiler.syntax_tree.tags
            if any(tag in tags for tag in ANSWER_tags):
                make_files(input_name, correction=True, _nums=nums, context=context, **kwargs)


if __name__ == "__main__":
    ptyx()
