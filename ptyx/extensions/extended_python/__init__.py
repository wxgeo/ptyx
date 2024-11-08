r"""
EXTENDED PYTHON

This extension add some useful shortcuts to Python scripts.

An example:

    ...........................
    let a, b
    let a, b in 2..5
    let a, b +
    let c, d, e, f +-
    let a, b /
    let a +
    let b -
    let a +-1
    let c,d in -5..
    let a, b +
    let c, d -
    let u in -3..-1
    let p in 2,3,5,7,11,13,17,19
    let a, b in 2..20 with a > 2*b
    ...........................


    IMPORTANT!
    This syntax extension does only support one line statements!
    After conversion, each "extended python" one-line statement
    must result in a pure python one-line statement too!
    This makes parsing a lot easier and faster,
    and enables to extend python checking tools much more easily too
    (line numbers don't change after parsing, only columns, which
    is only a minor inconvenient!)
    """

from re import sub, DOTALL, MULTILINE, Match
from typing import Protocol

from ptyx.latex_generator import Compiler

from ptyx.utilities import extract_verbatim_tag_content, restore_verbatim_tag_content

PYTHON_DELIMITER = "^[ \t]*\\.{4,}[ \t]*$"


# def _convert_let_directive(m: re.Match) -> str:


def parse_extended_python_code(code: str) -> str:
    """Convert 'extended python' code to pure python code.

    Known issue:
    -----------
    If the parsed python code defines a literal multiline string
    with a line starting with "let" (or " let", "  let"...),
    everything in this line will be parsed like extended python code.
    This will result in an altered string, and maybe broken python code.
    """

    def f(m: Match) -> str:
        print("Extended python code detected: ", m.group(0))
        return parse_extended_python_line(m.group(0))

    return sub("^ *let .+$", f, code, flags=MULTILINE)


def parse_extended_python_line(original_line: str) -> str:
    """Convert one line of 'extended python' code to pure python code.

    `SyntaxError` is raised if the line can not be parsed.
    """
    line = original_line.lstrip()
    # An extended python line always starts with "let ".
    if not line.startswith("let "):
        return original_line
    # Memorize indent to restore it later.
    indent = (len(original_line) - len(line)) * " "
    # Remove "let " from the start of the line.
    line = line[4:].strip()
    # Now, let's handle the special `let ... with <condition>` syntax, to get `<condition>`.
    i = line.find(" with ")
    if i != -1:
        condition = line[i + 6 :]
        line = line[:i]
    else:
        condition = None
    # Handle `let <varname> in <values>` syntax.
    if " in " in line:
        names, val = line.split(" in ")
        # Parse <values>, which may be a range, like `-7..10`, or a list of values, like `2,3,5,7,11`.
        if ".." in val:
            a, b = val.split("..")
            if a.startswith("+-") or a.startswith("-+"):
                a = a[2:]
                f = "srandint"
            else:
                f = "randint"
            args = [f, "a=%s" % a.strip(), "b=%s" % b.strip()]
        else:
            f = "randchoice"
            args = [f, "items=[%s]" % val.strip()]
    # If no values are specified, use default ones.
    else:
        if not line:
            raise SyntaxError("lonely `let`.")
        if line.endswith("+-") or line.endswith("-+"):
            # let a, b +-
            args = ["srandint"]
            names = line[:-2]
        elif line.endswith("+"):
            # let a, b +
            args = ["randint"]
            names = line[:-1]
        elif line.endswith("-"):
            # let a, b -
            args = ["randint", "a=-9", "b=-2"]
            names = line[:-1]
        elif line.endswith("/"):
            # let a, b /
            args = ["srandfrac"]
            names = line[:-1]
        else:
            # let a, b
            args = ["srandint"]
            names = line

    names_list = [name.strip() for name in names.split(",")]
    if not all(name.isidentifier() for name in names_list):
        raise SyntaxError(f"Line {line!r} not understood.")

    # Append a final `,` after variables, since one should always do tuple unpacking!
    joined_names = ", ".join(names_list) + ","
    joined_args = ", ".join(args)
    function_call = f"many({len(names_list)}, {joined_args})"
    if condition:
        # Loop while condition is false.
        # It's better to do it in one line, to not change line numbering when debugging.
        # Ideally, we should do this:
        #  line = f"while ((({joined_names}) := {function_call} or True) and not ({condition})): pass"
        # However, tuple unpacking is not allowed in walrus operator for now:
        # https://github.com/python/cpython/issues/87309
        # So, we'll have to create a temporary variable:
        # let's call it `_tmp_ptyx_var` to avoid name collisions.
        # Then, we will affect all its values to each variable.
        affectation = f"_tmp_ptyx_var := {function_call}, "
        affectation += ", ".join(f"{name} := _tmp_ptyx_var[{i}]" for i, name in enumerate(names_list))
        line = f"while ((({affectation}) or True) and not ({condition})): pass"
    else:
        line = f"{joined_names} = {function_call}"

    # We must keep the statement on only one line,
    # to not change the line number for debugging tools!
    assert "\n" not in line
    # Restore indentation eventually.
    return indent + line


class PythonBlockParser(Protocol):
    def __call__(self, *, start: str, end: str, content: str) -> str:
        ...


def parse_code_block(code: str, parser: PythonBlockParser) -> str:
    """Parse a python code block, delimited by `.....` lines by default.

    Function `parser` must define 3 keyword-only arguments, `start`, `end`
    and `content`, corresponding to the block start and end delimiters,
    and to the block content itself.
    """

    def parse(m: Match) -> str:
        return parser(start=m.group("start"), end=m.group("end"), content=m.group("content"))

    return sub(
        f"(?P<start>{PYTHON_DELIMITER})(?P<content>.*?)(?P<end>{PYTHON_DELIMITER})",
        parse,
        code,
        flags=DOTALL | MULTILINE,
    )


def main(code: str, compiler: Compiler = None) -> str:
    code, verbatim_contents = extract_verbatim_tag_content(code)

    def parse(*, start: str, end: str, content: str) -> str:
        return f"#PYTHON{parse_extended_python_code(content)}#END_PYTHON"

    # ............
    # Python code
    # ............
    # noinspection PyTypeChecker
    code = parse_code_block(code, parser=parse)
    code = restore_verbatim_tag_content(code, verbatim_contents)
    return code
