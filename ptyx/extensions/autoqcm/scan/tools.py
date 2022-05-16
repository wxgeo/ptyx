#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 22:40:40 2020

@author: nicolas
"""
import builtins
from os.path import expanduser
from pathlib import Path
import pickle


def search_by_extension(directory: Path, ext: str) -> Path:
    """Search for a file with extension `ext` in given directory.

    Search is NOT case sensible.
    If no or more than one file is found, an error is raised.
    """
    ext = ext.lower()
    paths = [pth for pth in directory.glob("*") if pth.name.lower().endswith(ext)]
    if not paths:
        raise FileNotFoundError(f"No {ext!r} file found in that directory: {directory} ! ")
    elif len(paths) > 1:
        raise RuntimeError(
            f"Several {ext!r} file found in that directory: {directory} ! "
            "Keep only one of them and delete all the others (or rename their extensions)."
        )
    return paths[0]


def print_framed_msg(msg):
    decoration = max(len(line) for line in msg.split("\n")) * "-"
    print(decoration)
    print(msg)
    print(decoration)


def tmp_store(obj):
    """For debugging."""
    with open(expanduser("~/tmp.pickle"), "wb") as f:
        pickle.dump(obj, f)


def tmp_load():
    """For debugging."""
    with open(expanduser("~/tmp.pickle"), "rb") as f:
        return pickle.load(f)


def round(f, n=None):
    # PEP3141 compatible round() implementation.
    # round(f) should return an integer, but the problem is
    # __builtin__.round(f) doesn't return an int if type(f) is np.float64.
    # See: https://github.com/numpy/numpy/issues/11810
    return int(builtins.round(f)) if n is None else builtins.round(f, n)


def levenshtein_distance(string1: str, string2: str) -> int:
    """Return the Levenshtein distance between the two strings.

    The Levenshtein distance between two words is the minimum number
    of single-character edits (insertions, deletions or substitutions)
    required to change one word into the other.
    """
    # cf. https://en.wikipedia.org/wiki/Levenshtein_distance
    # Create two work vectors of integer distances
    # Initialize previous_row (the previous row of distances)
    # this row is A[0][i]: edit distance from an empty s to t;
    # that distance is the number of characters to append to  s to make t.
    m = len(string1)
    n = len(string2)

    previous_row = list(range(n + 1))
    current_row = [0 for _ in previous_row]

    for i in range(m):
        # Calculate current_row (current row distances) from the previous row previous_row
        # first element of current_row is A[i + 1][0]
        # edit distance is delete (i + 1) chars from s to match empty t
        current_row[0] = i + 1
        # use formula to fill in the rest of the row
        for j in range(n):
            # calculating costs for A[i + 1][j + 1]
            deletionCost = previous_row[j + 1] + 1
            insertionCost = current_row[j] + 1
            if string1[i] == string2[j]:
                substitutionCost = previous_row[j]
            else:
                substitutionCost = previous_row[j] + 1
            current_row[j + 1] = min(deletionCost, insertionCost, substitutionCost)
        # copy current_row to previous_row for next iteration
        # since data in current_row is always invalidated, a swap without copy is more efficient
        previous_row, current_row = current_row, previous_row
    # after the last swap, the results of current_row are now in previous_row
    return previous_row[n]
