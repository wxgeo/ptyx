r"""
QUESTIONS

This extension add some useful shortcuts to Python scripts.

An example:


    ...........................
    a, b in 2..5
    a, b +
    c, d, e, f +-
    a, b *
    a, b /
    a +
    b -
    a +-1
    c,d in -5..
    @ a, b +
    let a, b +
    let c, d -
    let u in -3..-1,
    h, y -
    let a, b
    a, b, c

    ...........................
    """

from __future__ import division, unicode_literals, absolute_import, print_function

from re import sub, DOTALL


def parse_extended_python_code(code):
    py = []
    for line in code.split('\n'):
        spaces = (len(line) - len(line.lstrip()))*' '
        line = line.strip()
        if line.startswith('let '):
            line = line[4:]
            if 'in' in line:
                names, val = line.split('in')
                # parse val
                if '..' in val:
                    a, b = val.split('..')
                    if a.startswith('+-') or a.startswith('-+'):
                        a = a[2:]
                        f = 'srandint'
                    else:
                        f = 'randint'
                    args = [f, 'a=%s' % a.strip(), 'b=%s' % b.strip()]

            else:
                assert line, 'Syntax error: lonely `let`.'
                if line.endswith('+-') or line.endswith('-+'):
                    args = ['srandint']
                    names = line[:-2]
                elif line.endswith('+'):
                    args = ['randint']
                    names = line[:-1]
                elif line.endswith('-'):
                    args = ['randint', 'a=-9', 'b=-2']
                    names = line[:-1]
                else:
                    args = ['srandint']
                    names = line

            #TODO: define nrandint

            names = [n.strip() for n in names.split(',')]

            line = '%s, = many(%s, %s)' % (', '.join(names), len(names), ', '.join(args))
        py.append(spaces + line)
    return '\n'.join(py)



def main(text, compiler):
    def parse(m):
        content = m.group('content')
        return '\n#PYTHON\n%s\n#END\n' % parse_extended_python_code(content)

    # ............
    # Python code
    # ............
    return sub("\n[ \t]*\\.{3,}[ \t]*\n(?P<content>.*?)\n[ \t]*\\.{3,}[ \t]*\n",
               parse, text, flags=DOTALL)
