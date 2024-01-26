import re
from math import ceil, floor, isnan, isinf
from typing import Sequence, Any


RE_VERBATIM_BLOCK = r"#VERBATIM\W.*?#END(?:_VERBATIM)?"


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
    escape_string_char = False

    # ', ", { and } are matched.
    # Note that if brackets == '[]', bracket ] must appear first in
    # regular expression ('[]"\'[]' is valid, but '[["\']]' is not).
    # So, close_bracket must appear at first in the reg.
    reg_str = (
        f"[{close_bracket}\"'\\\\{open_bracket}]" if detect_strings else f"[{close_bracket}{open_bracket}]"
    )
    reg = re.compile(reg_str)

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
        # (Note: we have to take care of the `\` escape character, see below).
        elif result in ("'", '"') and not escape_string_char:
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

        # `\` character is used to escape and `"` and `'` characters inside a python string.
        # As an exception, two consecutive `\` don't escape following `'`, `"`.
        if string_type is not None and result == "\\":
            escape_string_char = not escape_string_char
        else:
            escape_string_char = False
        i += 1  # counting the current character as already scanned text
        index += i
        text = text[i:]

    else:
        return start + index - 1  # last character is the searched bracket :-)

    raise ValueError("ERROR: unbalanced brackets (%s) while scanning %s..." % (balance, repr(text_beginning)))


def advanced_split(
    string: str, separator: str, quotes: str = "\"'", brackets: Sequence[str] = ("()", "[]", "{}")
) -> list[str]:
    """Split string "main_string" smartly, detecting brackets group and inner strings.

    Return a list of strings."""
    if len(separator) != 1:
        raise ValueError("Separator must be a single caracter, not %s." % repr(separator))
    if separator in quotes + "".join(brackets):
        raise ValueError("%s can't be used as separator.")
    # Little optimisation since `not in` is very fast.
    if separator not in string:
        return [string]
    breaks: list[int] = [-1]  # those are the points where the string will be cut
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


def numbers_to_floats(expr: Any, integers: bool = False, ndigits: int = None) -> float:
    """Convert all numbers (except integers) to floats inside a sympy expression."""
    import sympy

    if not isinstance(expr, sympy.Basic):
        if isinstance(expr, int) and not integers:
            return expr
        elif ndigits is not None:
            return round_away_from_zero(expr, ndigits)
        else:
            return float(expr)
    for sub in sympy.preorder_traversal(expr):
        sub = sympy.sympify(sub)
        if not sub.has(sympy.Symbol) and (integers or not sub.is_Integer):
            new = sub.evalf()
            if ndigits is not None:
                new = round_away_from_zero(new, ndigits)
            expr = expr.subs(sub, new)
    return expr


def term_color(string, color, **kw):
    """On Linux, format string for terminal printing.

    Available keywords: bold, dim, italic, underline and hightlight.

    >>> term_color('hello world !', 'blue', bold=True, underline=True)
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


def latex_verbatim(s: str) -> str:
    """Try to emulate verbatim (which is not allowed inside a macro argument in LaTeX).

    LaTeX special characters are escaped, so that the string is displayed as it.
    A fixed-width font is used too.

        >>> latex_verbatim("\\emph{$a^2+b_i$}")
        '\\texttt{\\textbackslash{}emph\\{\\$a\\textasciicircum{}2+b\\_i\\$\\}}'
    """
    # Strip the first \n, to avoid beginning with a \linebreak.
    if s.startswith("\n"):
        s = s[1:]
    # Replace \ first !
    s = s.replace("\\", r"\textbackslash<!ø5P3C14Lø?>")
    for char in "#$%&_{}":
        s = s.replace(char, rf"\{char}")
    s = s.replace("<!ø5P3C14Lø?>", "{}")
    s = s.replace("~", r"\raisebox{0.5ex}{\texttildelow}")
    s = s.replace("^", r"\textasciicircum{}")
    s = s.replace("'", r"\textquotesingle{}")
    # Use \phantom{} after \linebreak to preserve spaces at the beginning of the line.
    s = s.replace("\n", "\\linebreak\\phantom{}")
    s = s.replace("\t", 4 * " ")
    s = s.replace(" ", "~")
    return rf"\texttt{{{s}}}"


def extract_verbatim_tag_content(code: str) -> tuple[str, list[str]]:
    """Return the string with verbatim tag content replaced by `\n`, and a list of verbatim contents.

    In the list of verbatim contents, the #VERBATIM and #END tags are included.
    """
    substitutions = []

    def substitute(m: re.Match) -> str:
        substitutions.append(m.group(0))
        return "#VERBATIM\n#END"

    return re.sub(RE_VERBATIM_BLOCK, substitute, code, flags=re.DOTALL), substitutions


def restore_verbatim_tag_content(code: str, substitutions: list[str]) -> str:
    """Reverse `extract_verbatim_tag_content()` operation."""

    def substitute(_: re.Match) -> str:
        return substitutions.pop(0)

    return re.sub(RE_VERBATIM_BLOCK, substitute, code, flags=re.DOTALL)
