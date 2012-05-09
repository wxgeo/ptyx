#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
from __future__ import division # 1/2 == .5 (par defaut, 1/2 == 0)
#~ from __future__ import with_statement

# --------------------------------------
#                  PTYX
#              main script
# --------------------------------------
#    PTYX
#    Python LaTeX preprocessor
#    Copyright (C) 2009  Nicolas Pourcelot
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


_version_ = "0.4"
_release_date_ = (9, 1, 2012)

print 'Ptyx ' + _version_ + ' ' + '/'.join(str(d) for d in _release_date_)

# <default_configuration>
param = {
                    'total': 1,
                    'format': ['pdf', 'tex'],
                    'tex_command': 'pdflatex -interaction=nonstopmode',
                    'sympy_is_default': True,
                    'sympy_path': None,
                    'tablatex': None,
                    'debug': False,
                    'floating_point': ',',
                    }
# </default_configuration>

# <personnal_configuration>
param['sympy_path'] = '~/Programmation/wxgeometrie/wxgeometrie'
param['wxgeometrie_path'] = '~/Programmation/wxgeometrie'
# </personnal_configuration>


import optparse, re, random, os, tempfile, shutil, sys, codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('cp850')(sys.stdout)
else:
    sys.stdout = codecs.getwriter('utf8')(sys.stdout)

for pathname in ('sympy_path', 'wxgeometrie_path'):
    path = param[pathname]
    if path is not None:
        path = os.path.normpath(os.path.expanduser(path))
        sys.path.insert(0, path)
        param[pathname] = path

try:
    import sympy
    from sympy.core.sympify import SympifyError
except ImportError:
    print("** ERROR: sympy not found ! **")
    sympy = None
    param['sympy_is_default'] = False

try:
    from wxgeometrie.modules import tablatex
except ImportError:
    print("WARNING: tablatex not found.")
    tablatex = None

try:
    import numpy
except ImportError:
    print("WARNING: numpy not found.")
    numpy = None


#~ def is_negative_number(value):
    #~ is_python_num = isinstance(value, (float, int, long))
    #~ is_sympy_num = sympy and isinstance(value, sympy.Basic) and value.is_number
    #~ return (is_sympy_num or is_python_num) and value < 0


class CustomOutput(object):
    def __init__(self, logfile_name = ''):
        self.log_file_created = False
        self.logfile_name = logfile_name

    def write(self, string_):
        try:
            sys.__stdout__.write(string_)
            if self.logfile_name:
                try:
                    f = open(self.logfile_name, 'a')
                    f.write(string_)
                finally:
                    f.close()
        except Exception:
            sys.stderr = sys.__stderr__
            raise



class SpecialDict(dict):
    auto_sympify = False
    op_mode = None

    def __setitem__(self, key, value):
        if self.auto_sympify:
            try:
                value = sympy.sympify(value)
            except SympifyError:
                print('Warning: sympy error. Switching to standard evaluation mode.')
        dict.__setitem__(self, key, value)

    def copy(self):
        return SpecialDict(dict.copy(self))


global_context = SpecialDict()

math_list = ('cos', 'sin', 'tan', 'ln', 'exp', 'diff', 'limit', 'integrate', 'E', 'pi', 'I', 'oo', 'gcd', 'lcm')

if sympy is not None:
    global_context['sympy'] = sympy
    global_context['sympify'] = global_context['SY'] = sympy.sympify
    for name in math_list:
        global_context[name] = getattr(sympy, name)
if numpy is not None:
    global_context['numpy'] = numpy

global_context['sign'] = lambda x: ('+' if x > 0 else '-')

_special_cases =  [
                #           #CASE{int}
                r'(?P<name1>CASE)[ ]*(?P<case>\{[0-9 ]+\}|\[[0-9 ]+\])',
                #            #IFNUM{int}{code}
                r'(?P<name6>IFNUM)[ ]*(?P<num>\{[0-9 ]+\}|\[[0-9 ]+\])[ ]*\{',
                #            #IFTHEN{condition}{code}
                r'(?P<name7>TEST)[ ]*\{(?P<cond>[^}]+)\}[ ]*\{',
                r'(?P<name2>IF|ELIF)[ ]*\{',
                r'(?P<name3>PYTHON|SYMPY|RAND|TABVAR|TABSIGN|TABVAL|GEO|ELSE|SIGN|COMMENT|END)',
                ]
_other_ones =  [
                #           #+, #-,  #*, #=  (special operators)
                r'(?P<name4>[-+*=?])',
                #           #RAND[option,int]{code} or #SEL[option,int]{code} or #[option,int]{code}
                r'(?P<name5>RAND|ASSERT|SEL(ECT)?)?(\[(?P<flag1>[0-9, a-z]+)\])?[ ]*\{',
                #           #varname or #[option,int]varname
                r'(\[(?P<flag2>[0-9, a-z]+)\])?(?P<varname>[A-Za-z_]+[0-9_]*)',
                ]

# (\n[ ]*)? is used to skip new lines before #IF, #ELSE, ...
RE_PTYX_TAGS = re.compile(r'(?<!\\)((\n[ ]*)?#(' + '|'.join(_special_cases) + r')|#(' + '|'.join(_other_ones) + '))')



def find_closing_bracket(expr, start = 0, brackets = '{}'):
    expr_deb = expr[:min(len(expr), 30)]
    # for debugging
    index = 0
    balance = 1
    # None if we're not presently in a string
    # Else, string_type may be ', ''', ", or """
    string_type = None
    reg = re.compile('["' + brackets + "']") # ', ", { and } matched
    open_bracket = brackets[0]
    close_bracket = brackets[1]
    if start:
        expr = expr[start:]
    while balance:
        m = re.search(reg, expr)
        #~ print 'scan:', m
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
                if expr[i:].startswith(3*result):
                    string_type = 3*result
                    i += 2
                else:
                    string_type = result
            elif string_type == result:
                string_type = None
            elif string_type == 3*result:
                if expr[i:].startswith(3*result):
                    string_type = None
                    i += 2

        i += 1 # counting the current caracter as already scanned text
        index += i
        expr = expr[i:]

    else:
        return start + index - 1 # last caracter is the searched bracket :-)

    raise ValueError, 'ERROR: unbalanced brackets (%s) while scanning %s...' %(balance, repr(expr_deb))



def _exec(code, context):
    u"""exec is encapsulated in this function so as to avoid problems
    with free variables in nested functions."""
    try:
        exec(code, context)
    except:
        print "** ERROR found in the following code: **"
        print(code)
        print "-----"
        print repr(code)
        print "-----"
        raise


def _exec_python_code(code, context):
    code = code.replace('\r', '')
    code = code.rstrip().lstrip('\n')
    # Indentation test
    initial_indent = len(code) - len(code.lstrip(' '))
    if initial_indent:
        # remove initial indentation
        code = '\n'.join(line[initial_indent:] for line in code.split('\n'))
    _exec(code, context)
    return code


def _apply_flag(result, context, **flags):
    '''Apply [num] and [rand] special parameters to result.

    Note that both parameters require that result is iterable, otherwise, nothing occures.
    If result is iterable, an element of result is returned, choosed according to current flag.'''
    if  hasattr(result, '__iter__'):
        if flags.get('rand', False):
            result = random.choice(result)
        elif flags.get('select', False):
            result = result[context['NUM']%len(result)]
    if flags.has_key('round'):
        try:
            round_result = round(result, flags['round'])
        except ValueError:
            print "** ERROR while rounding value: **"
            print result
            print "-----"
            print context['text'][-100:]
            print "-----"
            raise
        context.result_is_exact = (result == round_result)
        result = round_result
    else:
        context.result_is_exact = True
    return result


#~ def _eval_sympy_expr(code, context, flag = None):
    #~ if sympy is None:
        #~ raise ImportError, 'sympy library not found.'
    #~ varname = ''
    #~ i = code.find('='):
    #~ if i != -1 and len(code) > i + 1 and code[i + 1] != '=':
        #~ varname = code[:i]
        #~ code = code[i + 1:]
    #~ if not varname:
        #~ varname = '_'
    #~ result = sympy.sympify(code, locals = context)
    #~ result = _apply_flag(result, flag)
    #~ context[varname] = result
    #~ return sympy.latex(result)[1:-1]


def print_sympy_expr(expr, **flags):
    if isinstance(expr, float) or (sympy and isinstance(expr, sympy.Float)) \
            or flags.get('float'):
        # -0.06000000000000001 means probably -0.06 ; that's because
        # floating point arithmetic is not based on decimal numbers, and
        # so some decimal numbers do not have exact internal representation.
        # Python str() handles this better than sympy.latex()
        latex = str(float(expr))
        #TODO: sympy.Float instance may only be part of an other expression.
        # It would be much better to subclass sympy LaTeX printer

        # Strip unused trailing 0.
        latex = latex.rstrip('0').rstrip('.')
        # In french, german... a comma is used as floating point.
        # However, if `float` flag is set, floating point is left unchanged
        # (useful for Tikz for example).
        if not flags.get('float'):
            latex = latex.replace('.', param['floating_point'])
    elif sympy and expr is sympy.oo:
        latex = r'+\infty'
    else:
        latex = sympy.latex(expr)
    #TODO: subclass sympy LaTeX printer (cf. mathlib in wxgeometrie)
    latex = latex.replace(r'\operatorname{log}', r'\operatorname{ln}')
    return latex

global_context['latex'] = print_sympy_expr

if sympy is not None:
    sympy.Basic.__str__ = print_sympy_expr


def _eval_python_expr(code, context, **flags):
    if not code:
        return ''
    sympy_code = flags.get('sympy', param['sympy_is_default'])

    # Special shortcuts
    display_result = True
    # If code ends with ';', the result will not be included in the LaTeX file.
    # So, \python{5;} will affect 5 to _, but will not display 5 on final document.
    if code[-1] == ';':
        code = code[:-1]
        display_result = False

    if ';' in code:
        for subcode in code.split(';'):
            result = _eval_python_expr(subcode, context, **flags)
            # Only last result will be displayed
    else:
        if sympy_code and sympy is None:
            raise ImportError, 'sympy library not found.'
        varname = ''
        i = code.find('=')
        if i != -1 and len(code) > i + 1 and code[i + 1] != '=':
            varname = code[:i].strip()
            code = code[i + 1:]
        # Last value will be accessible through '_' variable
        if not varname:
            varname = '_'
        if ' if ' in code and not ' else ' in code:
            code += " else ''"
        if sympy_code:
            try:
                result = sympy.sympify(code, locals = context)
                if isinstance(result, basestring):
                    result = result.replace('**', '^')
            except SympifyError:
                sympy_code = False
                print('Warning: sympy error. Switching to standard evaluation mode.')
        if not sympy_code:
            result = eval(code, context)
        i = varname.find('[')
        # for example, varname == 'mylist[i]' or 'mylist[2]'
        if i == -1:
            context[varname] = result = _apply_flag(result, context, **flags)
        else:
            key = eval(varname[i+1:-1], context)
            varname = varname[:i]
            context[varname][key] = result = _apply_flag(result, context, **flags)


    if not display_result:
        return ''
    if sympy_code:
        latex = print_sympy_expr(result, **flags)
    else:
        latex = str(result)


    def neg(latex):
        return latex.lstrip()[0] == '-'

    if context.op_mode:
        mode = context.op_mode
        context.op_mode = None
        if mode == '+':
            if not neg(latex):
                latex = '+' + latex
        elif mode == '*':
            if neg(latex):
                latex = r'\left(' + latex + r'\right)'
            latex = r'\times ' + latex
        elif mode == '-':
            if neg(latex):
                latex = r'\left(' + latex + r'\right)'
            latex = '-' + latex
        elif mode == '?':
            if result == 0:
                latex += '=0'
            elif result > 0:
                latex += '>0'
            else:
                latex += '<0'
        elif mode == '=':
            if context.result_is_exact:
                latex = ' = ' + latex
            else:
                latex = r' \approx ' + latex

    return latex






def convert_ptyx_to_latex(text, context = None):
    if context is None:
        context = global_context.copy()
    context['text'] = ''
    def write(arg, context = context, str = str):
        context['text'] += str(arg)
    context['write'] = write
    tree = ['root']
    conditions = [True]

    while True:
        if tree[-1] in ('SYMPY', 'PYTHON', 'TABVAR', 'TABSIGN', 'TABVAL'):
            name = 'END'
            start = text.find('#END')
            if start == -1:
                raise SyntaxError, '#END not found while parsing #' + tree[-1] +' bloc !'
            end = start + 4
        else:
            m = re.search(RE_PTYX_TAGS, text)
            if m is None:
                context['text'] += text
                break

            flag = m.group('flag1') or m.group('flag2')
            varname = m.group('varname')
            name = m.group('name1') or m.group('name2') or m.group('name3') or m.group('name4') or m.group('name5')
            num = m.group('num')
            case = m.group('case')
            cond = m.group('cond')
            #~ op = m.group('op')
            #~ cond_op = m.group('cond_op')
            #~ context['text'] += text[:m.start()]
            #~ # By default, skip the balise
            start = m.start()
            end = m.end()

        if param['debug']:
            print('------')
            print('#' + str(name))
            print(repr(text[start:start + 30] + '...'))
            _context = context.copy()
            _context['__builtins__'] = None
            _context.pop('write')
            _context.pop('text')
            _context.pop('NUM')
            _context.pop('TOTAL')
            print _context.keys()
            print zip(tree, conditions)

        if name == 'END':
            condition = conditions.pop()
            last_node = tree.pop()
            assert tree
            if condition and all(conditions):
                if last_node == 'PARAM':
                    _exec_python_code(text[:start], param)
                elif last_node in ('SYMPY', 'PYTHON'):
                    context.auto_sympify = (last_node == 'SYMPY' )
                    _exec_python_code(text[:start], context)
                    context.auto_sympify = False
                elif last_node in ('TABVAR', 'TABSIGN', 'TABVAL'):
                    assert tablatex is not None
                    context_text_backup = context['text']
                    context['text'] = ''
                    # We check if any options have to be passed to TABVAR, TABSIGN, TABVAL
                    # Exemples:
                    # TABSIGN[cellspace=True]
                    # TABVAR[derivee=False,limites=False]
                    m_opts = re.match(r'(\n| )*(\[|{)(?P<opts>[^]]+)(\]|})', text[:start])
                    options = {}
                    if m_opts:
                        text = text[m_opts.end():]
                        start -= m_opts.end()
                        end -= m_opts.end()
                        opts = m_opts.group('opts').split(',')
                        for opt in opts:
                            if '=' in opt:
                                arg, val = opt.split('=', 1)
                                options[arg] = eval(val, context)
                    tbvcode = convert_ptyx_to_latex(text[:start], context).strip()
                    context['text'] = context_text_backup
                    func = getattr(tablatex, last_node.lower())
                    write(func(tbvcode, **options))
                else:
                    if param['debug']:
                        print('------')
                        print('WRITING (1):')
                        print(text[:start])
                    write(text[:start])

        else:
            if all(conditions):
                if param['debug']:
                    print('------')
                    print('WRITING (2):')
                    print(text[:start])
                write(text[:start])
            if name in ('-', '+', '*', '?', 'SIGN', '='):
                if all(conditions):
                    context.op_mode = name if name != 'SIGN' else '?'
                # Mode '+':
                # a '+' will be displayed at the beginning of the next result if positive ;
                # if result is negative, nothing will be done, and if null, no result at all will be displayed.
                # Mode '*':
                # a '\times' will be displayed at the beginning of the next result, and the result
                # will be embedded in parenthesis if negative.
                # Mode '-':
                # a '-' will be displayed at the beginning of the next result, and the result
                # will be embedded in parenthesis if negative.
                # Mode '?' (alias 'SIGN'):
                # '>0', '<0' or '=0' will be displayed after the next result, depending on it's sign.
                # Mode '=':
                # Affiche '=' ou '\approx' après un arrondi, selon si le résultat
                # est exact ou non.

            elif name == 'COMMENT':
                tree.append(name)
                conditions.append(False)

            elif name == 'CASE':
                condition = (int(case[1:-1]) == context.get('NUM', 0))
                if tree[-1] == name:
                    conditions[-1] = condition
                else:
                    tree.append(name)
                    conditions.append(condition)

            elif name in ('PYTHON', 'SYMPY', 'TABVAR', 'TABSIGN', 'TABVAL'):
                tree.append(name)
                conditions.append(True)

            elif name in ('IF', 'ELIF'):
                closing = find_closing_bracket(text, end)
                code = text[end:closing]
                end = closing + 1 # include closing bracket
                eval_func = sympy.sympify if param['sympy_is_default'] else eval
                if all(conditions):
                    # Lambdify condition for lazy evaluation
                    condition = lambda:eval_func(code, locals = context)
                else:
                    condition = lambda:None

                if name == 'IF':
                    tree.append('IF')
                    # False means 'there was never a True before in the current IF/ELIF/ELIF/[...]/ELSE succession ',
                    # while None means 'one of previous node led to a True condition' ; so condition will never be True
                    # again in the current IF/ELIF/ELIF/[...]/ELSE succession.
                    # Note that False/None distinction is essential to correctly interpret next ELIF or ELSE.
                    conditions.append(condition())

                else: # ELIF
                    assert tree[-1] == 'IF'
                    if conditions[-1]:
                        conditions[-1] = None
                    elif conditions[-1] is False: # False, not None !
                        conditions[-1] = condition()

            elif name  == 'ELSE':
                assert tree[-1] == 'IF'
                conditions[-1] = (conditions[-1] is False)

            elif name == 'PARAM':
                tree.append(name)
                conditions.append(True)

            else:
                if varname:
                    code = varname
                else:
                    closing = find_closing_bracket(text, end)
                    code = text[end:closing]
                    end = closing + 1
                if all(conditions):
                    flags = {}
                    if flag is not None:
                        for flag in flag.split(','):
                            flag = flag.strip()
                            if 'python'.startswith(flag):
                                flags['sympy'] = False
                            elif 'sympy'.startswith(flag):
                                flags['sympy'] = True
                            elif flag == 'float':
                                flags['float'] = True
                            elif flag == 'num':
                                print "WARNING: 'num' flag is deprecated. Use #SELECT command instead."
                                flags['select'] = True
                            else:
                                try:
                                    flags['round'] = int(flag)
                                except ValueError:
                                    print 'WARNING: Unknown flag "%s".' %flag

                    if name == 'RAND':
                        flags['rand'] = True
                    elif name in ('SEL', 'SELECT'):
                        flags['select'] = True
                    if name == 'ASSERT':
                        test = eval(code, context)
                        if not test:
                            print "Error in assertion:"
                            print "***"
                            print code
                            print "***"
                            assert test
                    elif cond is not None: #TEST
                        if eval(cond, context):
                            text = code + text[end:]
                            continue
                    elif num is None or int(num[1:-1]) == context.get('NUM', 0):
                        result = _eval_python_expr(code, context, **flags)
                        write(result)

        text = text[end:]

    return context['text']





def compile(input, output, make_tex_file = False, make_pdf_file = True, del_log = False, del_aux = False):
    input_file = None
    try:
        input_file = open(input, 'rU')
        text = input_file.read()
    finally:
        if input_file is not None:
            input_file.close()
    dir = os.path.split(output)[0]
    extra = (' -output-directory ' + dir if dir else '')
    #~ if head:
        #~ os.chdir(head)
    latex = convert_ptyx_to_latex(text)
    if make_tex_file:
        try:
            texfile = open(output + '.tex', 'w')
            texfile.write(latex)
            if make_pdf_file:
                texfile.flush()
                os.system(param['tex_command'] + extra + ' ' + texfile.name)
                if del_log:
                    os.remove(output + '.log')
                if del_aux:
                    os.remove(output + '.aux')
        finally:
            texfile.close()
    else:
        try:
            texfile = tempfile.NamedTemporaryFile(suffix = '.tex')
            texfile.write(latex)
            if make_pdf_file:
                tmp_name  = os.path.split(texfile.name)[1][:-4] # without .tex extension
                pdf_name = tmp_name + '.pdf'
                log_name = tmp_name + '.log'
                aux_name = tmp_name + '.aux'
                texfile.flush()
                os.system(param['tex_command'] + extra + ' ' + texfile.name)
                os.rename(pdf_name, output + '.pdf')
                if del_log:
                    os.remove(log_name)
                else:
                    os.rename(log_name, output + '.log')
                if del_aux:
                    os.remove(aux_name)
                else:
                    os.rename(aux_name, output + '.aux')
        finally:
            textfile.close()





if __name__ == '__main__':

    # Options parsing
    parser = optparse.OptionParser(prog = "Ptyx", usage = "usage: %prog [options] filename",  version = "%prog " + _version_)
    parser.add_option("-n", "--number", help = "Number of pdf files to generate.\nEx: ptyx -n 5 my_file.ptyx")
    #~ parser.add_option("-o", "--output", help = "Name of the output file (without extension).")
    parser.add_option("-f", "--format", help = "Output format (default is " + '+'.join(param['format']) + ").\nEx: ptyx -f tex my_file.ptyx")
    parser.add_option("-r", "--remove", action = "store_true", help = "Remove any generated .log and .aux file after compilation.\nNote that references in LaTeX code could be lost.")
    parser.add_option("-m", "--make_directory", action = "store_true", help = "Create a new directory to store all generated files.")
    parser.add_option("-a", "--auto_make_dir", action = "store_true", help = "Switch to --make_directory mode, except if .ptyx file is already in a directory with the same name (e.g. myfile123/myfile123.ptyx).")
    parser.add_option("-b", "--debug", action = "store_true", help = "Debug mode.")
    parser.add_option("-s", "--start", default = 0, help = "Number of the first generated file (initial value of internal NUM counter). Default is 0.")

    options, args = parser.parse_args()

    total = global_context['TOTAL'] = (int(options.number) if options.number else param['total'])

    formats = options.format.split('+') if options.format else param['format']
    if options.debug:
        param['debug'] = True

    start = options.start


    #~ output = options.output if options.output else 'newfile'

    # On Unix-like OS, spaces in arguments are strangely managed by Python.
    # For example, "my file.ptyx" would be split in "my" and "file.ptyx", even if written between ' or ".
    arguments = []
    full = True
    for arg in args:
        if full:
            arguments.append(arg)
        else:
            arguments[-1] += " " + arg
        full = arg.endswith(".ptyx") or arg.endswith('.tex')

    if not arguments:
        print("Warning: no input.\nType 'ptyx --help' for more info.")

    make_tex = ('tex' in formats)

    for input_name in arguments:
        input_name = os.path.expanduser(input_name)
        input_name = os.path.normpath(input_name)
        input_name = os.path.realpath(input_name)
        os.chdir(os.path.split(input_name)[0])
        if input_name.endswith('.ptyx'):
            output_name = input_name[:-5]
        elif input_name.endswith('.tex'):
            output_name = input_name[:-4]
            if make_tex:
                output_name += '_'
            # the trailing _ avoids name conflicts with the .tex file generated

        head, tail = os.path.split(output_name)
        if options.auto_make_dir:
            # Test if the .ptyx file is already in a directory with same name.
            options.make_directory = (os.path.split(head)[1] != tail)
        if options.make_directory:
            # Create a directory with the same name than the .ptyx file,
            # which will contain all generated files.
            if not os.path.isdir(tail):
                os.mkdir(tail)
            output_name = output_name + os.sep + tail

            print output_name
        for num in xrange(start, start + total):
            global_context['NUM'] = num
            suffixe = '-' + str(num) if total > 1 else ''
            # Output is redirected to a .log file
            sys.stdout = sys.stderr = CustomOutput((output_name + suffixe + '-python.log') if not options.remove else '')
            compile(input_name, output_name + suffixe, make_tex_file = make_tex, \
                        del_log = options.remove, del_aux = options.remove,
                        make_pdf_file = ('pdf' in formats),
                        )
