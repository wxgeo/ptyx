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


__version__ = "19.8"
# API version number changes only when backward compatibility is broken.
__api__ = "4.3"
__release_date__ = (19, 8, 2019)


import argparse, os, sys, csv
from ast import literal_eval

from ptyx.config import param
from ptyx.utilities import pth
from ptyx.compilation import make_files
from ptyx.latexgenerator import compiler


if sys.version_info.major == 2:
    raise RuntimeError("Python version 3.6+ requis !")


# Options parsing
parser = argparse.ArgumentParser(prog='pTyX',
        description='Compile .ptyx files into .tex or .pdf files.',
        usage="usage: %(prog)s [options] filename")

parser.add_argument("filenames", nargs='+')

parser.add_argument("-n", "--number", type=int,
        help="Number of pdf files to generate. Default is %s.\n \
               Ex: ptyx -n 5 my_file.ptyx" % param['total']
               )
parser.add_argument("-f", "--formats", default=param['default_format'],
        choices=['pdf', 'tex', 'pdf+tex', 'tex+pdf'],
        help="Output format. Default is %(default)s.\n"
               "Ex: ptyx -f tex my_file.ptyx"
               )
parser.add_argument("-r", "--remove", action="store_true",
        help="Remove the `.compile` folder after compilation."
                )
parser.add_argument("-b", "--debug", action="store_true",
        help="Debug mode."
                )
parser.add_argument("-q", "--quiet", action="store_true",
        help="Suppress most of latex processor output."
                )
parser.add_argument("-s", "--start", default=1, type=int,
        help="Number of the first generated file \
               (initial value of internal NUM counter). Default is %(default)s."
               )
parser.add_argument("-c", "--cat", action="store_true",
        help="Cat all generated pdf files inside a single one. \
               The pdftk command must be installed."
               )
parser.add_argument("-C", "--compress", action="store_true",
        help="Like --cat, but compress final pdf file using pdf2ps and ps2pdf."
                )
parser.add_argument("--reorder-pages", choices=['brochure', 'brochure-reversed'],
        help="Reorder pages for printing.\n\
        Currently, only 'brochure' and 'brochure-reversed' mode are supported.\
        The `pdftk` command must be installed.\n\
        Ex: ptyx --reorder-pages=brochure-reversed -f pdf myfile.ptyx."
        )
parser.add_argument("--names", metavar='CSV_FILE',
        help="Name of a CSV file containing a column of names \
               (and optionnaly a second column with fornames). \n \
               The names will be used to generate the #NAME tag \
               replacement value.\n \
               Additionnaly, if `-n` option is not specified, \
               default value will be the number of names in the CSV file."
               )

parser.add_argument("-p", "--filter-by-pages-number", metavar='N', type=int,
        help="Keep only pdf files whose pages number match N. \
        This may be useful for printing pdf later. \
        Note that the number of files may not be respected then, so \
        you may have to adjust the number of files manually."
        )

parser.add_argument("-nc", "--no-correction", action="store_true",
        help="Don't generate a correction of the test."
               )

parser.add_argument("-g", "--generate-batch-for-windows-printing", action="store_true",
        help="Generate a batch file for printing all pdf files using SumatraPDF."
        )
parser.add_argument("--context", default='',
        help="Manually customize context (ie. internal namespace).\n \
               Ex: ptyx --context \"a = 3; b = 2; t = 'hello'\""
               )
parser.add_argument("--version", action='version', version='%(prog)s ' +
                    '%s (%s/%s/%s)' % ((__version__,) + __release_date__))


def ptyx(parser=parser):
    # First, parse all arguments (filenames, options...)
    # --------------------------------------------------
    options = parser.parse_args()
    options.formats = options.formats.split('+')

    if options.compress or options.cat:
        # pdftk and ghostscript must be installed.
        if 'pdf' not in options.formats:
            raise RuntimeError("--cat or --compress option invalid unless pdf output is selected.")

    if options.debug:
        param['debug'] = True

    if options.names:
        with open(pth(options.names)) as f:
            options.names = [' '.join(l) for l in csv.reader(f)]
            print('Names extracted from CSV file:')
            print(options.names)
    else:
        options.names = []

    if options.number is None:
        options.number = len(options.names) or param['total']

    ctxt = options.context
    options.context = {}
    for keyval in ctxt.split(';'):
        if keyval.strip():
            key, val = keyval.split('=', 1)
            key = key.strip()
            if not str.isidentifier(key):
                raise NameError(f'{key} is not a valid variale name.')
            options.context[key] = literal_eval(val)


    # Time to act ! Let's compile all ptyx files...
    # ---------------------------------------------

    for input_name in options.filenames:
        # Read pTyX file.
        print(f'Reading {input_name}...')
        input_name = pth(input_name)
        compiler.read_file(input_name)
        # Load extensions if needed.
        compiler.call_extensions()

        # Generate syntax tree.
        # The syntax tree is generated only once, and will then be used
        # for all the following compilations.
        compiler.generate_syntax_tree()
        # print(compiler.state['syntax_tree'].display())

        # Set the seed used for pseudo-random numbers generation.
        # (The seed value is set in the ptyx file using special tag #SEED{}).
#        compiler.read_seed()
        # Compile and generate output files (tex or pdf)
        filenames, output_name, nums = make_files(input_name, **vars(options))

        # Keep track of the seed used.
        seed_value = compiler.state['seed']
        seed_file_name = os.path.join(os.path.dirname(output_name), '.seed')
        with open(seed_file_name, 'w') as seed_file:
            seed_file.write(str(seed_value))


        # If any of the so-called `ANSWER_tags` is present, compile a second
        # version of the documents with answers.
        # TODO: make an API to choose if the version with answers must be generated
        # or not:
        # - there should be 3 modes, True, False and Auto (current mode).
        # - each mode should be accessible from the command line (add an option)
        # - it should be easy to modify mode for extensions.
        if not options.no_correction:
            ANSWER_tags = ('ANS', 'ANSWER', 'ASK', 'ASK_ONLY')

            tags = compiler.state['syntax_tree'].tags
            if any(tag in tags for tag in ANSWER_tags):
                filenames, output_name, nums2 = make_files(input_name, correction=True, _nums=nums, **vars(options))
                assert nums2 == nums, repr((nums, nums2))

        compiler.close()



if __name__ == '__main__':
    ptyx(parser)

