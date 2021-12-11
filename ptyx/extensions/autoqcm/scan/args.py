#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 19:21:17 2020

@author: nicolas
"""
from argparse import ArgumentParser


def create_parser():
    "Create the argument parser used by class `MCQPictureParser`."
    parser = ArgumentParser(description="Extract information from numerised tests.")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help=(
            "Path to a directory which must contain "
            "a .autoqcm.config file and a .scan.pdf file "
            "(alternatively, this path may point to any file in this folder)."
        ),
    )
    parser.add_argument(
        "--start", metavar="N", type=int, default=1, help="Start at picture N (skip first pages)."
    )
    parser.add_argument(
        "--end",
        metavar="N",
        type=int,
        default=float("inf"),
        help="End at picture N (skip last pages).",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all cached data." "The scanning process will restart from the beginning.",
    )
    parser.add_argument(
        "--picture", metavar="P", type=str, help="Scan only given picture (useful for debugging)."
    )
    # Following options can't be used simultaneously.
    group2 = parser.add_mutually_exclusive_group()
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

    parser.add_argument(
        "--ask-for-name",
        action="store_true",
        default=None,
        help="For each first page, display a picture of "
        "the top of the page and ask for the student name.",
    )
    parser.add_argument("-d", "--dir", type=str, help="Specify a directory with write permission.")
    parser.add_argument(
        "-s",
        "--scan",
        "--scan-dir",
        type=str,
        metavar="DIR",
        help="Specify the directory where the scanned tests can be found.",
    )
    parser.add_argument(
        "-c",
        "--correction",
        action="store_true",
        help="For each test, generate a pdf file with the answers.",
    )
    parser.add_argument(
        "--hide-scores",
        action="store_true",
        help="Print only answers, not scores, in generated pdf files.",
    )
    return parser
