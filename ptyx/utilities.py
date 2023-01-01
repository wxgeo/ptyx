import re
from math import ceil, floor, isnan, isinf
from os.path import realpath, normpath, expanduser
from typing import List, Sequence

from ptyx.config import sympy

if sympy is not None:
    from sympy import preorder_traversal, Symbol


def round_away_from_zero(val, ndigits=0) -> float:
    """Round using round-away-from-zero strategy for halfway cases.

    Python 3+ implements round-half-even, and Python 2.7 has a random behaviour
    from end user point of view (in fact, result depends on internal
    representation in floating point arithmetic).
    """
    val = float(val)
    if isnan(val) or isinf(val):
        return val
    val *= 10**ndigits
    if val >= 0.0:
        val = floor(val + 0.5)
    else:
        val = ceil(val - 0.5)
    val *= 10 ** (-ndigits)
    return val


def find_closing_bracket(text: str, start: int = 0, brackets: str = "{}", detect_strings=True) -> int:
    """Find the closing bracket, starting from position `start`.

    Note that start have to be a position *after* the opening bracket.

    >>> from ptyx.utilities import find_closing_bracket
    >>> find_closing_bracket('{{hello} world !}', start=1)
    16

    By default, inner strings are handled, so that in "{'}'}", second } will be
    reported as closing bracket, since '}' is seen as an inner string.
    To disable the detection of inner strings, use `detect_strings=False`.

    >>> find_closing_bracket("{'}'}", start=1)
    4
    >>> find_closing_bracket("{'}'}", start=1, detect_strings=False)
    2
    """
    text_beginning = text[start : start + 30]
    # for debugging
    index = 0
    balance = 1
    # None if we're not presently in a string
    # Else, string_type may be ', ''', ", or """
    string_type = None

    open_bracket = brackets[0]
    close_bracket = brackets[1]

    # ', ", { and } are matched.
    # Note that if brackets == '[]', bracket ] must appear first in
    # regular expression ('[]"\'[]' is valid, but '[["\']]' is not).
    reg_str = "[%s\"'%s]" if detect_strings else "[%s%s]"
    reg = re.compile(reg_str % (close_bracket, open_bracket))

    if start:
        text = text[start:]
    while balance:
        m = re.search(reg, text)
        if m is None:
            break

        result = m.group()
        i = m.start()
        if result == open_bracket:
            if string_type is None:
                balance += 1
        elif result == close_bracket:
            if string_type is None:
                balance -= 1

        # Brackets in string should not be recorded...
        # so, we have to detect if we're in a string at the present time.
        elif result in ("'", '"'):
            if string_type is None:
                if text[i:].startswith(3 * result):
                    string_type = 3 * result
                    i += 2
                else:
                    string_type = result
            elif string_type == result:
                string_type = None
            elif string_type == 3 * result:
                if text[i:].startswith(3 * result):
                    string_type = None
                    i += 2

        i += 1  # counting the current character as already scanned text
        index += i
        text = text[i:]

    else:
        return start + index - 1  # last character is the searched bracket :-)

    raise ValueError("ERROR: unbalanced brackets (%s) while scanning %s..." % (balance, repr(text_beginning)))


def advanced_split(
    string: str, separator: str, quotes: str = "\"'", brackets: Sequence[str] = ("()", "[]", "{}")
) -> List[str]:
    """Split string "main_string" smartly, detecting brackets group and inner strings.

    Return a list of strings."""
    if len(separator) != 1:
        raise ValueError("Separator must be a single caracter, not %s." % repr(separator))
    if separator in quotes + "".join(brackets):
        raise ValueError("%s can't be used as separator.")
    # Little optimisation since `not in` is very fast.
    if separator not in string:
        return [string]
    breaks: List[int] = [-1]  # those are the points where the string will be cut
    stack = ["."]  # ROOT
    for i, letter in enumerate(string):
        if letter in quotes:
            if stack[-1] in quotes:
                # We are inside a string.
                if stack[-1] == letter:
                    # Closing string.
                    stack.pop()
            else:
                stack.append(letter)
        elif letter == separator and len(stack) == 1:
            breaks.append(i)
        else:
            start: str
            end: str
            # mypy bug: "Unpacking a string is disallowed"
            for start, end in brackets:  # type: ignore
                if letter == start:
                    stack.append(letter)
                elif letter == end:
                    if stack[-1] != start:
                        raise ValueError("Unbalanced brackets in %s !" % repr(string))
                    stack.pop()
    if len(stack) != 1:
        raise ValueError("Unbalanced brackets in %s !" % repr(string))
    breaks.append(None)  # type: ignore
    # mystring[i:None] returns the end of the string.
    return [string[i + 1 : j] for i, j in zip(breaks[:-1], breaks[1:])]


def _float_me_if_you_can(expr):
    """Convert expr to float if possible, else left it untouched."""
    # noinspection PyBroadException
    try:
        return float(expr)
    except Exception:
        return expr


def numbers_to_floats(expr, integers=False, ndigits=None):
    """Convert all numbers (except integers) to floats inside a sympy expression."""
    if not sympy or not isinstance(expr, sympy.Basic):
        if isinstance(expr, int) and not integers:
            return expr
        elif ndigits is not None:
            return round_away_from_zero(expr, ndigits)
        else:
            return float(expr)
    for sub in preorder_traversal(expr):
        sub = sympy.sympify(sub)
        if not sub.has(Symbol) and (integers or not sub.is_Integer):
            new = sub.evalf()
            if ndigits is not None:
                new = round_away_from_zero(new, ndigits)
            expr = expr.subs(sub, new)
    return expr


def term_color(string, color, **kw):
    """On Linux, format string for terminal printing.

    Available keywords: bold, dim, italic, underline and hightlight.

    >>> color('hello world !', 'blue', bold=True, underline=True)
    '\x1b[4;1;34mhello world !\x1b[0m'
    """
    colors = {
        "gray": 30,
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "purple": 35,
        "cyan": 36,
        "white": 37,
    }
    styles = {"bold": 1, "dim": 2, "italic": 3, "underline": 4, "highlight": 7}
    if color not in colors:
        raise KeyError("Color %s is unknown. Available colors: %s." % (repr(color), list(colors.keys())))
    formatting = []
    for style, code in styles.items():
        appply_style = kw.get(style)
        if appply_style is not None:
            formatting.append(str(code) if appply_style else str(20 + code))
    formatting.append(str(colors[color]))
    return "\033[%sm%s\033[0m" % (";".join(formatting), string)


def pth(path):
    return realpath(normpath(expanduser(path)))
