import random
import math

import builtins

import ptyx.randfunc as randfunc
from ptyx.printers import sympy2latex
from ptyx.sys_info import SYMPY_AVAILABLE, NUMPY_AVAILABLE
from ptyx.utilities import latex_verbatim

GLOBAL_CONTEXT = dict()

for fname in [
    "abs",
    "all",
    "any",
    "ascii",
    "bin",
    "callable",
    "chr",
    "divmod",
    "format",
    "getattr",
    "hasattr",
    "hash",
    "hex",
    "id",
    "isinstance",
    "issubclass",
    "iter",
    "len",
    "max",
    "min",
    "next",
    "oct",
    "ord",
    "pow",
    "print",
    "repr",
    "round",
    "sorted",
    "sum",
]:
    GLOBAL_CONTEXT[fname] = getattr(builtins, fname)


if SYMPY_AVAILABLE:
    import sympy

    GLOBAL_CONTEXT["sympy"] = sympy
    GLOBAL_CONTEXT["sympify"] = GLOBAL_CONTEXT["SY"] = sympy.sympify
    # ~ for name in math_list:
    # ~ global_context[name] = getattr(sympy, name)
    exec("from sympy import *", GLOBAL_CONTEXT)
    exec('var("x y")', GLOBAL_CONTEXT)
    # ~ global_context['x'] = sympy.Symbol('x')

if NUMPY_AVAILABLE:
    import numpy

    GLOBAL_CONTEXT["numpy"] = numpy

GLOBAL_CONTEXT["sign"] = lambda x: ("+" if x > 0 else "-")
GLOBAL_CONTEXT["round"] = round
GLOBAL_CONTEXT["min"] = min
GLOBAL_CONTEXT["max"] = max
GLOBAL_CONTEXT["rand"] = GLOBAL_CONTEXT["random"] = random.random
GLOBAL_CONTEXT["ceil"] = GLOBAL_CONTEXT["ceiling"] if sympy is not None else math.ceil
GLOBAL_CONTEXT["float"] = float
GLOBAL_CONTEXT["int"] = int
GLOBAL_CONTEXT["str"] = str

for fname in (
    "randpoint",
    "srandpoint",
    "randint",
    "randbool",
    "srandint",
    "randsign",
    "randfrac",
    "srandfrac",
    "randfloat",
    "srandfloat",
    "randchoice",
    "srandchoice",
    "randsample",
    "randmatrix",
    "randpop",
    "shuffle",
    "many",
    "distinct",
    "_print_state",
    "randmaketrans",
):
    GLOBAL_CONTEXT[fname] = getattr(randfunc, fname)

# If a document is compiled several times (to produce different versions of the same document),
# PTYX_NUM is the compilation number (starting from 0).
GLOBAL_CONTEXT["PTYX_NUM"] = 0
GLOBAL_CONTEXT["latex"] = sympy2latex
GLOBAL_CONTEXT["latex_verbatim"] = latex_verbatim
