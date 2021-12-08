# -*- coding: utf-8 -*-
"""
AutoQCM Command Line Interface

@author: Nicolas Pourcelot
"""

from argparse import ArgumentParser
from typing import Optional

from .compile.make import make


def main(args: Optional[list] = None) -> None:
    """Main entry point, called whenever `autoqcm` command is executed."""
    parser = ArgumentParser(description="Generate and manage pdf MCQs.")
    subparsers = parser.add_subparsers()
    add_parser = subparsers.add_parser
    # create the parser for the "init" command
    new_parser = add_parser("new", help="Create an empty ptyx file.")
    # parser_init.add_argument('--force', action='store_true', help='init --force help')
    new_parser.set_defaults(func=new)

    # create the parser for the "make" command
    make_parser = add_parser("make", help="Generate pdf file.")
    make_parser.add_argument("path", metavar="PATH", type=str)
    make_parser.add_argument(
        "--num",
        "-n",
        metavar="N",
        type=int,
        help="Specify how many versions of the document must be generated.",
    )
    make_parser.set_defaults(func=make)

    # create the parser for the "scan" command
    scan_parser = add_parser("scan", help="Generate scores from scanned documents.")
    scan_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help=(
            "Path to a directory which must contain "
            "a .autoqcm.config file and a .scan.pdf file "
            "(alternatively, this path may point to any file in this folder)."
        ),
    )
    scan_parser.add_argument(
        "--start", metavar="N", type=int, default=1, help="Start at picture N (skip first pages)."
    )
    scan_parser.add_argument(
        "--end",
        metavar="N",
        type=int,
        default=float("inf"),
        help="End at picture N (skip last pages).",
    )

    scan_parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all cached data." "The scanning process will restart from the beginning.",
    )
    scan_parser.add_argument(
        "--picture", metavar="P", type=str, help="Scan only given picture (useful for debugging)."
    )
    # Following options can't be used simultaneously.
    group2 = scan_parser.add_mutually_exclusive_group()
    group2.add_argument(
        "--never-ask",
        action="store_false",
        dest="manual_verification",
        default=None,
        help="Always assume algorithm is right, " "never ask user in case of ambiguity.",
    )
    group2.add_argument(
        "--always-ask",
        action="store_true",
        default=None,
        dest="manual_verification",
        help="For each page scanned, display a picture of "
        "the interpretation by the detection algorithm, "
        "for manual verification.",
    )

    scan_parser.add_argument(
        "--ask-for-name",
        action="store_true",
        default=None,
        help="For each first page, display a picture of "
        "the top of the page and ask for the student name.",
    )
    scan_parser.add_argument(
        "-d", "--dir", type=str, help="Specify a directory with write permission."
    )
    scan_parser.add_argument(
        "-s",
        "--scan",
        "--scan-dir",
        type=str,
        metavar="DIR",
        help="Specify the directory where the scanned tests can be found.",
    )
    scan_parser.add_argument(
        "-c",
        "--correction",
        action="store_true",
        help="For each test, generate a pdf file with the answers.",
    )
    scan_parser.add_argument(
        "--hide-scores",
        action="store_true",
        help="Print only answers, not scores, in generated pdf files.",
    )
    scan_parser.set_defaults(func=scan)

    parsed_args = parser.parse_args(args)
    try:
        # Launch the function corresponding to the given subcommand.
        kwargs = vars(parsed_args)
        kwargs.pop("func")(**kwargs)
    except KeyError:
        # No subcommand passed.
        parser.print_help()


def new() -> None:
    """Implement `autoqcm new` command."""
    raise NotImplementedError


def scan() -> None:
    """Implement `autoqcm scan` command."""
    raise NotImplementedError
