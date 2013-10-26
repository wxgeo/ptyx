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
#    Copyright (C) 2009-2013  Nicolas Pourcelot
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


_version_ = "0.9"
_release_date_ = (24, 9, 2013)


print 'Ptyx ' + _version_ + ' ' + '/'.join(str(d) for d in _release_date_)

# <default_configuration>
param = {
                    'total': 1,
                    'format': ['pdf', 'tex'],
                    'tex_command': 'pdflatex -interaction=nonstopmode --shell-escape --enable-write18',
                    'quiet_tex_command': 'pdflatex -interaction=batchmode --shell-escape --enable-write18',
                    'sympy_is_default': True,
                    'sympy_path': None,
                    'wxgeometrie': None,
                    'wxgeometrie_path': None,
                    'debug': False,
                    'floating_point': ',',
                    }
# </default_configuration>

# <personnal_configuration>
param['sympy_path'] = '~/Dropbox/Programmation/wxgeometrie/wxgeometrie'
param['wxgeometrie_path'] = '~/Dropbox/Programmation/wxgeometrie'
# </personnal_configuration>


import optparse, re, random, os, tempfile, sys, codecs, csv, shutil
from functools import partial

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
    from sympy import S
except ImportError:
    print("** ERROR: sympy not found ! **")
    sympy = None
    param['sympy_is_default'] = False

try:
    import wxgeometrie
    try:
        from wxgeometrie.modules import tablatex
        from wxgeometrie.mathlib.printers import custom_latex
    except ImportError:
        print("WARNING: current wxgeometrie version is not compatible.")
except ImportError:
    print("WARNING: wxgeometrie not found.")
    wxgeometrie = None

try:
    import numpy
except ImportError:
    print("WARNING: numpy not found.")
    numpy = None


def pth(path):
        path = os.path.expanduser(path)
        path = os.path.normpath(path)
        return os.path.realpath(path)


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

math_list = ('cos', 'sin', 'tan', 'ln', 'exp', 'diff', 'limit',
             'integrate', 'E', 'pi', 'I', 'oo', 'gcd', 'lcm', 'floor',
             'ceiling',)

if sympy is not None:
    global_context['sympy'] = sympy
    global_context['sympify'] = global_context['SY'] = sympy.sympify
    for name in math_list:
        global_context[name] = getattr(sympy, name)
    global_context['x'] = sympy.Symbol('x')

if numpy is not None:
    global_context['numpy'] = numpy

global_context['sign'] = lambda x: ('+' if x > 0 else '-')
global_context['round'] = round
global_context['rand'] = global_context['random'] = random.random
global_context['ceil'] = global_context['ceiling']

def randint(a=2, b=9):
    val = random.randint(a, b)
    if param['sympy_is_default']:
        val = S(val)
    return val



def randsignint(a=2, b=9):
    return (-1)**randint(0, 1)*randint(a, b)

global_context['randint'] = randint
global_context['randsignint'] = randsignint
global_context['srandint'] = randsignint


_special_cases =  [
                #           #CASE{int} ou #SEED{int}
                r'(?P<name1>CASE|SEED)[ ]*(?P<case>\{[0-9 ]+\}|\[[0-9 ]+\])',
                #            #IFNUM{int}{code}
                r'(?P<name6>IFNUM)[ ]*(?P<num>\{[0-9 ]+\}|\[[0-9 ]+\])[ ]*\{',
                #            #TEST{condition}{code}
                r'(?P<name7>TEST)[ ]*\{(?P<cond>[^}]+)\}[ ]*\{',
                r'(?P<name2>IF|ELIF)[ ]*\{',
                r'(?P<name3>PYTHON|SYMPY|RAND|TABVAR|TABSIGN|TABVAL|GEO|ELSE|SIGN|COMMENT|END|DEBUG|SHUFFLE|ITEM)',
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


#ASSERT{}
#CASE{int}...#CASE{int}...#END
#COMMENT...#END
#DEBUG
#GEO...#END
#IF{bool}...#ELIF{bool}...#ELSE...#END
#IFNUM{int}{...}
#MACRO{name}
#NEW_MACRO{name}...#END
#PICK[option,int]{list}
#PYTHON...#END
#RAND[option,int]{list}
#SEED{int}
#SHUFFLE #ITEM...#ITEM...#END
#SIGN
#SYMPY...#END
#TABSIGN[options]...#END
#TABVAL[options]...#END
#TABVAR[options]...#END
#TEST{bool}{...}
#TEST_ELSE{bool}{...}{...}
#+, #-,  #*, #=, #? (special operators)
#varname or #[option,int]varname
## options : sympy, python, float
## int : round



# For each tag, indicate:
#   1. The number of arguments.
#   2. If the tag opens a block, a list of all the tags closing the block.
#
#  Notice that by default, the tag closing the block will not be consumed.
#  This means that the same tag will be parsed again to open or close another block.
#  To consume the closing tag, prefix the tag name with the '@' symbol.
#  This is usually the wished behaviour for #END tag.



class Node(object):
    u"""A node.

    name is the tag name, or the argument number."""
    def __init__(self, name):
        self.parent = None
        self.name = name
        self.options = None
        #~ self.args = []
        self.children = []

    def add_child(child):
        self.children.append(child)
        child.parent = self
        return child





class SyntaxTreeGenerator(object):
    tags = {'ASSERT':       (1, None),
            'CASE':         (1, ['CASE', 'ELSE', '@END']),
            'COMMENT':      (0, ['@END']),
            'DEBUG':        (0, None),
            'EVAL':         (1, None),
            'GEO':          (0, ['@END']),
            'IF':           (1, ['ELIF', 'ELSE', '@END']),
            'ELIF':         (1, ['ELIF', 'ELSE', '@END']),
            'ELSE':         (0, ['@END']),
            'IFNUM':        (2, None),
            'MACRO':        (1, None),
            'NEW_MACRO':    (1, ['@END']),
            'PICK':         (1, None),
            'PYTHON':       (0, ['@END']),
            'RAND':         (1, None),
            'SEED':         (1, None),
            'SHUFFLE':      (0, ['@END']),
            # Do *NOT* consume #END tag, which must be used to end #SHUFFLE block.
            'ITEM':         (0, ['ITEM', 'END']),
            'SIGN':         (0, None),
            'SYMPY':        (0, ['@END']),
            'TABSIGN':      (0, ['@END']),
            'TABVAL':       (0, ['@END']),
            'TABVAR':       (0, ['@END']),
            'TEST':         (2, None),
            'TEST_ELSE':    (3, None),
            '-':            (0, None),
            '+':            (0, None),
            '*':            (0, None),
            '=':            (0, None),
            '?':            (0, None),
            }

    # Tags sorted by length (longer first).
    # This is used for matching tests.
    sorted_tags = sorted(tags, key=len,reverse=True)

    def __init__(self, text):
        #~ self.syntax_tree = ['ROOT', None, []]
        self.syntax_tree = Node('ROOT')
        self.parse(self.syntax_tree, text)

    def parse(self, node, text):
        position = 0
        #~ number_of_args = 0
        node._closing_tags = []
        while True:
            last_position = position
            position = tag_position = text.find('#', position)
            if position == -1:
                break
            position += 1
            for tag in sorted_tags:
                if text[position:].startswith(tag):
                    next_character = text[position + len(tag)]
                    if not(next_character == '_' or next_character.isalnum()):
                        position += len(tag)
                        break
            else:
                if text[position].isdigit():
                    # LaTeX uses #0, #1, #2...
                    continue
                else:
                    # This is not a known tag name.
                    # Default tag name is EVAL.
                    tag = 'EVAL'

            # Tag name found.
            if tag in node._closing_tags:
                # Close node, but don't consume tag.
                node = node.parent
                position = tag_position
                continue
            if '@' + tag in node._closing_tags:
                # Close node and consume tag.
                node = node.parent
            else:
                node.add_child(text[last_position:tag_position])
                # Open a new node for this new command.
                number_of_args, closing_tags = self.tags[node.name]
                new_node = node.add_child(Node(tag))
                # Detect command optional argument.
                # XXX: tolerate \n and spaces before bracket.
                if text[position] == '[':
                    end = find_closing_bracket(text, position, brackets='[]')
                    new_node.options = text[position + 1:end]
                    position = end + 1
                # Detect command arguments.
                # Each argument become a node with its number as name.
                for i in range(number_of_args):
                    if text[position] == '{':
                        end = find_closing_bracket(text, position, brackets='{}')
                    else:
                        end = position
                        while end < len(text) and text[end].isalnum():
                            end += 1
                    arg_node = new_node.add_child(Node(i))
                    self.parse(arg_node, text[position + 1:end]
                if closing_tags is not None:
                    # Enter inside node.
                    node = new_node
                node._closing_tags = closing_tags
        node.add_child(text[last_position:])







class LatexGenerator(object):

    def __init__(self, context):
        self.content = []
        self.context = context
        self.context['LATEX'] = []
        self.macros = {}

    @property
    def NUM(self):
        return self.context.get('NUM', 0)

    #~ def parse(self, item):
        #~ if isinstance(item, list):
            #~ self.parse_block(item)
        #~ else:
            #~ self.parse_plain(item)

    def parse_text(self, text):
        pass

    def parse_block(self, tag, args, content):
        u"""Parse a block of pTyX syntax tree.

        Return True if block content was recursively parsed, and False else.

        In particular, when parsing an IF block, True will be returned if and
        only if the block condition was satisfied.
        """
        try:
            return getattr(self, 'parse_%s_block' % tag)(args, content)
        except AttributeError:
            print("Warning: method 'parse_%s_block' not found" % tag)


    def parse_content(self, content, function=None, **options):
        if function is not None:
            backup = self.context['LATEX']
            self.context['LATEX'] = []

        last_item_tag = None
        for item in content:
            if isinstance(item, basestring):
                self.write(self.parse_text(item))
                last_item_tag = None
            else:
                assert isinstance(item, list) and len(item) >= 2
                item_tag, item_arg = item[0:2]
                item_content = item[2:]
                # If an IF or ELIF block was executed, all successive ELIF
                # or ELSE blocks must be skipped.
                if last_item_tag in ('IF', 'ELIF') and item_tag in ('ELIF', 'ELSE'):
                    continue
                if last_item_tag == 'CASE' and item_tag in ('CASE', 'ELSE'):
                    continue
                block_parsed = self.parse_block(item_tag, item_arg, item_content)
                if block_parsed or item_tag not in ('IF', 'ELIF', 'CASE'):
                    # item block was processed.
                    # (A non processed block is typically an IF or CASE block whose condition was not satisfied).
                    last_item_tag = item_tag

            if function is not None:
                code = function(''.join(self.context['LATEX']), **options)
                self.context['LATEX'] = backup
                self.write(code)
        return True

    def parse_options(self, arg):
        u'Parse a tag options, following the syntax {key1=val1,...}.'
        options_list = arg.split(',')
        options = {}
        for option in options_list:
            key, val = option.split('=')
            options[key] = eval(val, self.context)
        return options

    def write(self, text):
        self.context['LATEX'].append(text)


    def parse_IF_tag(self, args, content):
        test = eval(args[0], self.context)
        if test:
            self.parse_content(content)
        return test

    parse_ELIF_tag = parse_IF_tag

    def parse_CASE_tag(self, args, content):
        test = eval(args[0], self.context) == self.NUM
        if test:
            self.parse_content(content)
        return test

    def parse_PYTHON_tag(self, args, content):
        assert isinstance(content, basestring)
        self._exec_python_code(content, self.context)

    #Remove comments before generating tree ?
    def parse_COMMENT_tag(self, arg, content):
        pass

    def parse_ASSERT_tag(self, args, content):
        assert not content
        test = eval(args[0], self.context)
        if not test:
            print "Error in assertion (NUM=%s):" % self.NUM
            print "***"
            print code
            print "***"
            assert test
            assert False

    def parse_NEW_MACRO_tag(self, arg, content):
        name = args[0]
        self.macros[name] = content

    def parse_MACRO_tag(self, args, content):
        name = args[0]
        if name not in self.macros:
            raise NameError, ('Error: MACRO "%s" undefined.' % name)
        self.parse_content(self.macros[name])

    def parse_SHUFFLE_tag(self, args, content):
        content = random.shuffle(content)
        self.parse_content(content)

    def parse_ITEM_tag(self, args, content):
        self.parse_content(content)

    def parse_SEED_tag(self, args, content):
        assert not content
        if self.NUM == 0:
            random.seed(int(args[0]))

    def parse_PICK_tag(self, args, content):
        assert not content
        varname, values = args[0].split('=')
        values = values.split(',')
        self.context[varname.strip] = values[self.NUM%len(values)]

    def parse_TABVAL_tag(self, args, content):
        from wxgeometrie import tabval
        options = self.parse_options(args[0])
        self.parse_content(content, function=tabval, **options)

    def parse_TABVAR_tag(self, args, content):
        from wxgeometrie import tabvar
        options = self.parse_options(args[0])
        self.parse_content(content, function=tabvar, **options)

    def parse_TABSIGN_tag(self, args, content):
        from wxgeometrie import tabsign
        options = self.parse_options(args[0])
        self.parse_content(content, function=tabsign, **options)

    def parse_TEST_tag(self, args, content):
        if eval(args[0], self.context):
            self.parse_content(args[1])







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

"IFNUM|SYMPY|RAND|GEO|SIGN|DEBUG|[-+*=?])"
                #           #RAND[option,int]{code} or #SEL[option,int]{code} or #[option,int]{code}
                #           #varname or #[option,int]varname
















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
            print ''.join(context['POINTER'])[-100:]
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
    elif wxgeometrie is not None:
        return custom_latex(expr, mode='plain')
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
    # So, #{5;} will affect 5 to _, but will not display 5 on final document.
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
            except (SympifyError, AttributeError):
                # sympy.sympify() can't parse attributes and methods inside
                # code for now (AttributeError is raised then).
                sympy_code = False
                print('Warning: sympy error. Switching to standard evaluation mode.')
            except Exception:
                print("Uncatched error when evaluating %s" % repr(code))
                raise
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
                symb = ' = '
            else:
                symb = r' \approx '
            # Search backward for temporary `None` marker in list, and replace
            # by appropriate symbol.
            textlist = context['POINTER']
            for i, elt in enumerate(reversed(textlist)):
                if elt is None:
                    textlist[len(textlist) - i - 1] = symb
                    break
            else:
                print("Debug warning: `None` couldn't be found when scanning context !")
    return latex






def convert_ptyx_to_latex(text, context=None, clear_text=True):
    u"""Convert text containing ptyx tags to plain LaTeX.

    :param text: a pTyX file content, to be converted to plain LaTeX.
    :type text: str
    :param context: current space name.
                    Nota: parsed text blocks are stored in context['POINTER'].
    :type context: dict or None
    :param clear_text: reset context['POINTER'] to [].
    :type clear_text: bool
    :rtype: string
    """
    # XXX: Currently, ptyx files are opened as string, not as unicode.
    # Pro:
    # - Ptyx doesn't have to be encoding aware (no need to specify encoding before proceeding).
    # Contra:
    # - Python variables defined in a ptyx file must not contain unicode context.
    # - This will break in Python 3+.
    # TODO: Use unicode instead. Autodetect encoding on Linux (`file --mime-encoding FILENAME`).
    if context is None:
        context = global_context.copy()
    if clear_text:
        context['DOCUMENT-ROOT'] = []
        context['POINTER'] = context['DOCUMENT-ROOT']

    def write(block, context=context, parse=False):
        u"""Append a block of text to context['POINTER'].

        :param block: a block of (usually parsed) text, or a list of such blocks.
        :type block: string or list
        :param context: current name space.
        :type context: bool
        :param parse: indicate text have to be parsed.
        :type parse: bool

        .. note:: Param `parse` defaults to False, since in most cases text is already
                  parsed at this state.
                  As an exception, when called from inside a #PYTHON [...] #END bloc,
                  write() may be applied to unparsed text.

        .. note:: `block` is a string of parsed text, or a (possibly nested) list of strings.
                  Lists are generared by #SHUFFLE #ITEM [...] [#ITEM [...]...] #END structures.
        """
        assert isinstance(block, (basestring, list))
        if parse and isinstance(block, basestring) and '#' in block:
            if param['debug']:
                print('Parsing %s...' % repr(block))
            convert_ptyx_to_latex(block, context=context, clear_text=False)
        else:
            context['POINTER'].append(block)

    context['write'] = partial(write, parse=True)
    tree = ['root']
    conditions = [True]

    while True:
        if tree[-1] in ('SYMPY', 'PYTHON', 'TABVAR', 'TABSIGN', 'TABVAL'):
            # Those tags don't support nested tags.
            name = 'END'
            start = text.find('#END')
            if start == -1:
                raise SyntaxError, ('#END not found while parsing #%s bloc !' % tree[-1])
            end = start + 4
        else:
            m = re.search(RE_PTYX_TAGS, text)
            if m is None:
                write(text)
                break

            flag = m.group('flag1') or m.group('flag2')
            varname = m.group('varname')
            name = m.group('name1') or m.group('name2') or m.group('name3') or m.group('name4') or m.group('name5')
            num = m.group('num')
            case = m.group('case')
            cond = m.group('cond')
            #~ op = m.group('op')
            #~ cond_op = m.group('cond_op')
            #~ context['POINTER'] += text[:m.start()]
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

        if name == 'DEBUG':
            while True:
                command = raw_input('Debug point. Enter command, or quit (q! + ENTER):')
                if command == 'q!':
                    break
                else:
                    print(eval(command))

        elif name == 'END':
            condition = conditions.pop()
            last_node = tree.pop()
            # tree should contain ['root'] at least
            assert tree, ('Error: lonely #END found after %s.' % repr(text[:start]))
            if condition and all(conditions):
                if last_node == 'PARAM':
                    _exec_python_code(text[:start], param)
                elif last_node in ('SYMPY', 'PYTHON'):
                    context.auto_sympify = (last_node == 'SYMPY' )
                    _exec_python_code(text[:start], context)
                    context.auto_sympify = False
                elif last_node in ('TABVAR', 'TABSIGN', 'TABVAL'):
                    assert wxgeometrie is not None
                    context_text_backup = context['POINTER']
                    context['POINTER'] = []
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
                    context['POINTER'] = context_text_backup
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
                    # All operations occur just before number, except for `=`.
                    # Between `=` and the result, some formating instructions
                    # may occure (like '\fbox{' for example).
                    if name == '=':
                        context['POINTER'].append(None)
                        # `None` is used as a temporary marker, and will be
                        # replaced by '=' or '\approx' later.
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
                # Display '=' or '\approx' when a rounded result is requested :
                # if rounded is equal to exact one, '=' is displayed.
                # Else, '\approx' is displayed instead.

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

                if name == 'IF':
                    tree.append('IF')
                    # False means 'there was never a True before in the current IF/ELIF/ELIF/[...]/ELSE succession ',
                    # while None means 'one of previous node led to a True condition' ; so condition will never be True
                    # again in the current IF/ELIF/ELIF/[...]/ELSE succession.
                    # Note that False/None distinction is essential to correctly interpret next ELIF or ELSE.
                    #
                    # In case of nested IF, there is no need to evaluate present condition
                    # if others conditions failed.
                    conditions.append(eval_func(code, locals = context)
                                      if all(conditions) else None)

                else: # ELIF
                    assert tree[-1] == 'IF'
                    if conditions[-1]:
                        conditions[-1] = None
                    elif conditions[-1] is False: # False, not None !
                        conditions[-1] = eval_func(code, locals = context)

            elif name  == 'ELSE':
                assert tree[-1] == 'IF'
                conditions[-1] = (conditions[-1] is False)

            elif name == 'SHUFFLE':
                tree.append(name)
                bloc_list = []

            elif name == 'ITEM':
                bloc_list.append('')

            elif name == 'PARAM':
                tree.append(name)
                conditions.append(True)

            elif name == 'SEED':
                if context.get('NUM', 0) == 0:
                    random.seed(int(case[1:-1]))

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
                            print "Error in assertion (NUM=%s):" % context['NUM']
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

    # Denest context['DOCUMENT-ROOT']

    # Filter list, since some `None` may remain if a lonely `#=` appears in document.
    # (Yet, this shouldn't happen if document is properly written).
    return ''.join(txt for txt in context['POINTER'] if txt)





def compile_file(input_name, output_name, make_tex_file=False,
                 make_pdf_file=True, options=None):
    remove = getattr(options, 'remove', False)
    quiet = getattr(options, 'quiet', False)
    input_file = None
    try:
        input_file = open(input_name, 'rU')
        text = input_file.read()
    finally:
        if input_file is not None:
            input_file.close()
    dir_name = os.path.split(output_name)[0]
    extra = (' -output-directory ' + dir_name if dir_name else '')
    latex = convert_ptyx_to_latex(text)
    if make_tex_file:
        try:
            texfile = open(output_name + '.tex', 'w')
            texfile.write(latex)
            if make_pdf_file:
                texfile.flush()
                os.system(param['tex_command'] + extra + ' ' + texfile.name)
                if remove:
                    os.remove(output_name + '.log')
                    os.remove(output_name + '.aux')
        finally:
            texfile.close()
    else:
        try:
            texfile = tempfile.NamedTemporaryFile(suffix='.tex')
            texfile.write(latex)
            if make_pdf_file:
                tmp_name  = os.path.split(texfile.name)[1][:-4] # without .tex extension
                pdf_name = tmp_name + '.pdf'
                log_name = tmp_name + '.log'
                aux_name = tmp_name + '.aux'
                texfile.flush()
                if quiet:
                    command = param['quiet_tex_command']
                else:
                    command = param['tex_command']
                os.system(command + extra + ' ' + texfile.name)
                os.rename(pdf_name, output_name + '.pdf')
                if remove:
                    os.remove(log_name)
                else:
                    os.rename(log_name, output_name + '.log')
                if remove:
                    os.remove(aux_name)
                else:
                    os.rename(aux_name, output_name + '.aux')
        finally:
            texfile.close()





if __name__ == '__main__':

    # Options parsing
    parser = optparse.OptionParser(prog = "Ptyx",
            usage = "usage: %prog [options] filename",
            version = "%prog " + _version_)
    parser.add_option("-n", "--number",
            help = "Number of pdf files to generate.\n \
                   Ex: ptyx -n 5 my_file.ptyx")
    #~ parser.add_option("-o", "--output", help = "Name of the output file (without extension).")
    parser.add_option("-f", "--format",
            help = "Output format (default is "
                   + '+'.join(param['format'])
                   + ").\nEx: ptyx -f tex my_file.ptyx")
    parser.add_option("-r", "--remove", action = "store_true",
            help = "Remove any generated .log and .aux file after compilation.\n \
                    Note that references in LaTeX code could be lost.")
    parser.add_option("-R", "--remove-all", action = "store_true",
            help = "Remove any generated .log and .aux file after compilation.\n \
                    If --cat option or --compress option is used, remove also \
                    all pdf files, except for the concatenated one.")
    parser.add_option("-m", "--make_directory", action = "store_true",
            help = "Create a new directory to store all generated files.")
    parser.add_option("-a", "--auto_make_dir", action = "store_true",
            help = "Switch to --make_directory mode, except if .ptyx file \
                   is already in a directory with the same name \
                   (e.g. myfile123/myfile123.ptyx).")
    parser.add_option("-b", "--debug", action = "store_true",
            help = "Debug mode.")
    parser.add_option("-q", "--quiet", action = "store_true",
            help = "Suppress most of latex processor output.")
    parser.add_option("-s", "--start", default = 0,
            help = "Number of the first generated file \
                   (initial value of internal NUM counter). Default is 0.")
    parser.add_option("-c", "--cat", action = "store_true",
            help = "Cat all generated pdf files inside a single one. \
                   The pdftk command must be installed.")
    parser.add_option("-C", "--compress", action = "store_true",
            help = "Like --cat, but compress final pdf file using pdf2ps and ps2pdf.")
    parser.add_option("--names",
            help = "Name of a CSV file containing a column of names \
                   (and optionnaly a second column with fornames). \n \
                   The names will be used to generate the #NAME tag \
                   replacement value.\n \
                   Additionnaly, if `-n` option is not specified, \
                   default value will be the number of names in the CSV file.")


    options, args = parser.parse_args()

    options.remove = options.remove or options.remove_all

    number = options.number
    total = global_context['TOTAL'] = (int(number) if number else param['total'])

    formats = options.format.split('+') if options.format else param['format']
    if options.debug:
        param['debug'] = True

    start = int(options.start)

    if options.names:
        with open(pth(options.names)) as f:
            names = [' '.join(l) for l in csv.reader(f)]
        total = global_context['TOTAL'] = (int(number) if number else len(names))
    else:
        names = []

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
        input_name = pth(input_name)
        os.chdir(os.path.split(input_name)[0])
        if input_name.endswith('.ptyx'):
            output_name = input_name[:-5]
        elif input_name.endswith('.tex'):
            output_name = input_name[:-4]
            if make_tex:
                output_name += '_'
            # the trailing _ avoids name conflicts with the .tex file generated
        else:
            output_name = input_name + '_'

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
            global_context['NAME'] = (names[num] if names else '')
            suffixe = '-' + str(num) if total > 1 else ''
            # Output is redirected to a .log file
            sys.stdout = sys.stderr = CustomOutput((output_name + suffixe + '-python.log') if not options.remove else '')
            compile_file(input_name, output_name + suffixe, make_tex_file=make_tex, \
                        make_pdf_file=('pdf' in formats), options=options
                        )
        if options.compress or (options.cat and total > 1):
            # pdftk and ghostscript must be installed.
            if not ('pdf' in formats):
                print("Warning: --cat or --compress option meaningless if pdf output isn't selected.")
            else:
                pdf_name = output_name + '.pdf'
                if total > 1:
                    filenames = ['%s-%s.pdf' % (output_name, num) for num in xrange(start, start + total)]
                    files = ' '.join(filenames)
                    os.system('pdftk ' + files + ' output ' + pdf_name)
                    if options.remove_all:
                        for name in filenames:
                            os.remove(name)
                if options.compress:
                    temp_dir = tempfile.mkdtemp()
                    compressed_pdf_name = os.path.join(temp_dir, 'compresse.pdf')
                    command = \
                        """command pdftops \
                        -paper match \
                        -nocrop \
                        -noshrink \
                        -nocenter \
                        -level3 \
                        -q \
                        "%s" - \
                        | command ps2pdf14 \
                        -dEmbedAllFonts=true \
                        -dUseFlateCompression=true \
                        -dProcessColorModel=/DeviceCMYK \
                        -dConvertCMYKImagesToRGB=false \
                        -dOptimize=true \
                        -dPDFSETTINGS=/prepress \
                        - "%s" """ % (pdf_name, compressed_pdf_name)
                    os.system(command)
                    old_size = os.path.getsize(pdf_name)
                    new_size = os.path.getsize(compressed_pdf_name)
                    if new_size < old_size:
                        shutil.copyfile(compressed_pdf_name, pdf_name)
                        print('Compression ratio: {0:.2f}'.format(old_size/new_size))
                    else:
                        print('Warning: compression failed.')
