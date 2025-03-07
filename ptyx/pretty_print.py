import sys
from enum import IntEnum


class TermColors(IntEnum):
    GRAY = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    PURPLE = 5
    CYAN = 6
    WHITE = 7


def bold(to_print: object):
    """Convert `to_print` as string and put it in bold in shell. Preserve any previously set color."""
    # Warning: to disable bold, use 22, not 21 (as wrongly documented in many websites...)
    # nor 0 (it would reset color too)
    return f"\033[1m{to_print}\033[22m"


def yellow(to_print: object, bold=False) -> str:
    """Convert `to_print` as string and put it in yellow in shell."""
    return term_color(to_print, color=TermColors.YELLOW, bold=bold)


def red(to_print: object, bold=False) -> str:
    """Convert `to_print` as string and put it in red in shell."""
    return term_color(to_print, color=TermColors.RED, bold=bold)


def green(to_print: object, bold=False) -> str:
    """Convert `to_print` as string and put it in red in shell."""
    return term_color(to_print, color=TermColors.GREEN, bold=bold)


def custom_print(msg: str, color: TermColors, title: str, bold=False, **kw) -> None:
    title = term_color("[", color) + term_color(title, color, bold=bold) + term_color("]", color)
    print(f"{title} {msg}", **kw)


def print_error(msg: str) -> None:
    custom_print(msg, TermColors.RED, "Error", bold=True, file=sys.stderr)


def print_warning(msg: str) -> None:
    custom_print(msg, TermColors.YELLOW, "Warning", bold=False)


def print_success(msg: str) -> None:
    custom_print(msg, TermColors.GREEN, "OK", bold=True)


def print_info(msg: str) -> None:
    custom_print(msg, TermColors.BLUE, "Info", bold=False)


def term_color(
    string: object,
    color: TermColors | None = None,
    bold: bool = False,
    dim: bool = False,
    italic: bool = False,
    underline: bool = False,
    highlight: bool = False,
    reverse: bool = False,
) -> str:
    """On Linux, format string for terminal printing.

    Available keywords: bold, dim, italic, underline and hightlight.

    >>> term_color('hello world !', TermColors.BLUE, bold=True, underline=True)
    '\x1b[4;1;34mhello world !\x1b[0m'
    """
    # doc: https://misc.flogisoft.com/bash/tip_colors_and_formatting
    formatting = [
        (1 if bold else None),
        (2 if dim else None),
        (3 if italic else None),
        (4 if underline else None),
        (7 if highlight else None),
        ((40 if reverse else 30) + color) if color else None,
    ]
    codes = ";".join(str(code) for code in formatting if code is not None)
    return f"\033[{codes}m{string}\033[0m"


EMOTICONS = {"pen": chr(9998), "danger": chr(9888)}


def pretty_box(
    content: str,
    title: str = "",
    symbol: str = EMOTICONS["pen"],
    display_line_numbers: bool = True,
    min_width: int = 0,
) -> list[str]:
    """Return a list of prettified lines of python code, ready to be printed."""
    # vertical line: │ = \u2502
    msg = [""]
    if title:
        msg.append(f"│ {symbol} {title} ")
    lines = [""] + content.split("\n")
    zfill = len(str(len(lines)))
    for i, line in enumerate(lines[1:], start=1):
        line_num = str(i).zfill(zfill)
        prefix = f"│ {line_num} " if display_line_numbers else ""
        msg.append(f"{prefix}│ {line} ")
    # top-left corner: ╭ = \u256D
    # horizontal line: ─ = \u2500
    # left crossing: ├ = \u251C
    # right crossing: ┤ = \u2524
    # bottom-left corner: ╰ = \u2570
    # top-right corner: ╮ = \u256E
    # bottom-right corner: ╯ = \u256F
    n = max(max(len(s) for s in msg), min_width)
    # The size of the horizontal rule is available only after all lines
    # have been generated, so we have to insert them at the top of the box.
    for i, line in enumerate(msg[1:], start=1):
        msg[i] = line.ljust(n) + "│"
    horizontal_rule = (n - 1) * "─"
    msg.insert(1, "╭" + horizontal_rule + "╮")
    if title:
        msg.insert(3, "├" + horizontal_rule + "┤")
    msg.append("╰" + horizontal_rule + "╯")
    return msg
