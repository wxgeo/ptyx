r"""
QUESTIONS

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
    """
from re import sub, DOTALL, MULTILINE

from ptyx.utilities import extract_verbatim_tag_content, restore_verbatim_tag_content

PYTHON_DELIMITER = "^[ \t]*\\.{4,}[ \t]*$"


# def _convert_let_directive(m: re.Match) -> str:


def parse_extended_python_code(code):
    """Convert 'extend python' code to pure python code."""
    python_code = code.split("\n")
    for line_number, line in enumerate(python_code):
        if not line.lstrip().startswith("let "):
            continue
        indent = (len(line) - len(line.lstrip())) * " "
        line = line.strip()[4:]
        i = line.find(" with ")
        if i != -1:
            condition = line[i + 6 :]
            line = line[:i]
        else:
            condition = None
        if " in " in line:
            names, val = line.split(" in ")
            # parse val
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

        names = [name.strip() for name in names.split(",")]
        if not all(name.isidentifier() for name in names):
            raise SyntaxError(f"Line {line!r} not understood.")

        # Append a final `,` after variables, since one should always do tuple unpacking!
        joined_names = ", ".join(names) + ","
        joined_args = ", ".join(args)
        function_call = f"many({len(names)}, {joined_args})"
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
            affectation += ", ".join(f"{name} := _tmp_ptyx_var[{i}]" for i, name in enumerate(names))
            line = f"while ((({affectation}) or True) and not ({condition})): pass"
        else:
            line = f"{joined_names} = {function_call}"

        # Restore indentation eventually.
        python_code[line_number] = indent + line
    return "\n".join(python_code)


def main(code, compiler):
    code, verbatim_contents = extract_verbatim_tag_content(code)

    def parse(m):
        content = m.group("content")
        return f"#PYTHON{parse_extended_python_code(content)}#END_PYTHON"

    # ............
    # Python code
    # ............
    code = sub(
        f"{PYTHON_DELIMITER}(?P<content>.*?){PYTHON_DELIMITER}",
        parse,
        code,
        flags=DOTALL | MULTILINE,
    )
    code = restore_verbatim_tag_content(code, verbatim_contents)
    return code
