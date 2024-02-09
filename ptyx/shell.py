import sys
from typing import Any

ANSI_RESET = "\u001B[0m"
ANSI_BLACK = "\u001B[30m"
ANSI_RED = "\u001B[31m"
ANSI_GREEN = "\u001B[32m"
ANSI_YELLOW = "\u001B[33m"
ANSI_BLUE = "\u001B[34m"
ANSI_PURPLE = "\u001B[35m"
ANSI_CYAN = "\u001B[1;36m"
ANSI_WHITE = "\u001B[37m"
ANSI_GRAY = "\u001B[90m"
ANSI_BOLD = "\u001B[1m"
ANSI_REVERSE_PURPLE = "\u001B[45m"
ANSI_REVERSE_BLUE = "\u001B[44m"


shell_colors = {
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
}


def yellow(to_print: Any) -> str:
    """Convert `to_print` as string and put it in yellow in shell."""
    return f"{ANSI_YELLOW}{to_print}{ANSI_RESET}"


def custom_print(msg: str, color: str, label: str, bold=False, **kw) -> None:
    n = shell_colors[color]
    print(f"\33[3{n}m[\33[9{n}{';1' if bold else ''}m{label}\33[0m\33[3{n}m]\33[0m " + msg, **kw)


def print_error(msg: str) -> None:
    custom_print(msg, "red", "Error", bold=True, file=sys.stderr)


def print_warning(msg: str) -> None:
    custom_print(msg, "yellow", "Warning", bold=False)


def print_success(msg: str) -> None:
    custom_print(msg, "green", "OK", bold=True)


def print_info(msg: str) -> None:
    custom_print(msg, "blue", "Info", bold=False)
