r"""
QUESTIONS

This extension add some useful shortcuts to Python scripts.

An example:


    ...........................
    let a, b in 2..5
    let a, b +
    let c, d, e, f +-
    let a, b *
    let a, b /
    let a +
    let b -
    let a +-1
    let c,d in -5..
    let a, b +
    let c, d -
    let u in -3..-1
    ...........................
    """

from re import sub, DOTALL


def parse_extended_python_code(code):
    py = []
    for line in code.split('\n'):
        spaces = (len(line) - len(line.lstrip()))*' '
        line = line.strip()
        if line.startswith('let '):
            line = line[4:]
            if ' in ' in line:
                names, val = line.split(' in ')
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
                if not line:
                    raise SyntaxError('lonely `let`.')
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
                    names = line.rstrip('*')

            i = line.find(' with ')
            if i != -1:
                condition = line[i + 6:]
                #TODO: handle condition


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
