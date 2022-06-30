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

from re import sub, DOTALL


def parse_extended_python_code(code):
    "Convert 'extend python' code to pure python code."
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

        line = "%s, = many(%s, %s)" % (", ".join(names), len(names), ", ".join(args))
        if condition:
            sublines = [f"{indent}while True:"]
            indent += 4 * " "
            sublines.append(indent + line)
            sublines.append(f"{indent}if {condition}:")
            indent += 4 * " "
            sublines.append(f"{indent}break")
            python_code[line_number] = "\n".join(sublines)

        else:
            python_code[line_number] = indent + line
    return "\n".join(python_code)


def main(text, compiler):
    def parse(m):
        content = m.group("content")
        return "\n#PYTHON\n%s\n#END\n" % parse_extended_python_code(content)

    # ............
    # Python code
    # ............
    return sub(
        "\n[ \t]*\\.{3,}[ \t]*\n(?P<content>.*?)\n[ \t]*\\.{3,}[ \t]*\n",
        parse,
        text,
        flags=DOTALL,
    )
