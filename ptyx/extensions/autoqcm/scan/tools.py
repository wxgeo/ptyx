#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 22:40:40 2020

@author: nicolas
"""
import builtins
from os import listdir
from os.path import expanduser
from pathlib import Path
import pickle


def search_by_extension(directory: Path, ext: str) -> Path:
    """Search for a file with extension `ext` in given directory.

    Search is NOT case sensible.
    If no or more than one file is found, an error is raised.
    """
    ext = ext.lower()
    names = [name for name in listdir(directory) if name.lower().endswith(ext)]
    if not names:
        raise FileNotFoundError("No `%s` file found in that directory (%s) ! " % (ext, directory))
    elif len(names) > 1:
        raise RuntimeError(
            "Several `%s` file found in that directory (%s) ! "
            "Keep one and delete all others (or rename their extensions)." % (ext, directory)
        )
    return directory / names[0]


def print_framed_msg(msg):
    decoration = max(len(line) for line in msg.split("\n")) * "-"
    print(decoration)
    print(msg)
    print(decoration)


def tmp_store(obj):
    "For debuging."
    with open(expanduser("~/tmp.pickle"), "wb") as f:
        pickle.dump(obj, f)


def tmp_load():
    "For debuging."
    with open(expanduser("~/tmp.pickle"), "rb") as f:
        return pickle.load(f)


def round(f, n=None):
    # PEP3141 compatible round() implementation.
    # round(f) should return an integer, but the problem is
    # __builtin__.round(f) doesn't return an int if type(f) is np.float64.
    # See: https://github.com/numpy/numpy/issues/11810
    return (int(builtins.round(f)) if n is None else builtins.round(f, n))