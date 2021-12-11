#!/usr/bin/env python3

# --------------------------------------
#                  Scan
#     Extract info from numerised tests
# --------------------------------------
#    PTYX
#    Python LaTeX preprocessor
#    Copyright (C) 2009-2020  Nicolas Pourcelot
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


## File `compilation.py` is in ../.., so we have to "hack" `sys.path` a bit.
# script_path = dirname(abspath(sys._getframe().f_code.co_filename))
# sys.path.insert(0, join(script_path, '../..'))

from .args import create_parser
from .scanner import MCQPictureParser


########################################################################
#                                                                      #
#                                                                      #
#                             MAIN PROCEDURE                           #
#                                                                      #
#                                                                      #
########################################################################


def scan():
    """Main procedure : mark the examination papers.

    Usually, one will call script `bin/scan` from command line,
    which itself calls `scan()` (this procedure).
    `parser` must be the `ArgumentParser` instance defined in `args.py`,
    but may be tuned for testing before passing it to `scan()`.
    """
    args = create_parser().parse_args()
    MCQPictureParser(args).run()
