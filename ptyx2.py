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
        self.children = []

    def add_child(self, child):
        if not child:
            return None
        self.children.append(child)
        if isinstance(child, Node):
            child.parent = self
        return child

    #~ @property
    #~ def content(self):
        #~ if len(self.children) != 1:
            #~ raise ValueError, "Ambiguous: node has several subnodes."
        #~ return self.children[0]

    def arg(self, i):
        u"Return argument number i content."
        child = self.children[i]
        if child.name != i:
            raise ValueError, 'Incorect argument number.'
        if len(child.children) != 1:
            raise ValueError, ("Don't use pTyX code inside %s argument number %s." % (self.name, i + 1))
        return child.children[0]


    def display(self, color=True, indent=0):
        texts = ['%s+ Node %s' % (indent*' ', self._format(self.name, color))]
        for child in self.children:
            if isinstance(child, Node):
                texts.append(child.display(color, indent + 2))
            else:
                texts.append('%s  - text: %s' % (indent*' ', repr(child.split('\n')[0])))
        return '\n'.join(texts)

    def _format(self, val, color):
        if not color:
            return str(val)
        if isinstance(val, basestring):
            return self.yellow(val)
        elif isinstance(val, int):
            return self.blue(str(val))
        return val

    def blue(self, s):
        return '\033[0;36m' + s + '\033[0m'

    #~ def blue2(self, s):
        #~ return '\033[1;36m' + s + '\033[0m'
#~
    #~ def red(self, s):
        #~ return '\033[0;31m' + s + '\033[0m'
#~
    #~ def green(self, s):
        #~ return '\033[0;32m' + s + '\033[0m'
#~
    #~ def green2(self, s):
        #~ return '\033[1;32m' + s + '\033[0m'
#~
    def yellow(self, s):
        return '\033[0;33m' + s + '\033[0m'
#~
    #~ def white(self, s):
        #~ return '\033[1;37m' + s + '\033[0m'




#TODO:
# #PYTHON...#END content should not be parsed.
# (No need to parse #COMMENT...#END content too).



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
            'END':          (0, None),
            'IFNUM':        (2, None),
            'MACRO':        (1, None),
            'NEW_MACRO':    (1, ['@END']),
            'PICK':         (1, None),
            'PYTHON':       (0, ['@END']),
            'RAND':         (1, None),
            # ROOT isn't a real tag, and is never closed.
            'ROOT':         (0, []),
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


    def parse(self, text):
        u"""Parse pTyX code and generate a syntax tree.

        :param text: some pTyX code.
        :type text: string

        .. note:: To access generated syntax tree, use `.syntax_tree` attribute.
        """
        self.syntax_tree = Node('ROOT')
        self._parse(self.syntax_tree, text)

    def _parse(self, node, text):
        position = 0
        #~ number_of_args = 0
        node._closing_tags = []
        while True:
            last_position = position
            position = tag_position = text.find('#', position)
            if position == -1:
                break
            position += 1
            for tag in self.sorted_tags:
                if text[position:].startswith(tag):
                    if position + len(tag) == len(text):
                        # Last text character reached.
                        position += len(tag)
                        break
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


            node.add_child(text[last_position:tag_position])

            if tag in node._closing_tags:
                # Close node, but don't consume tag.
                node = node.parent
            elif '@' + tag in node._closing_tags:
                # Close node and consume tag.
                node = node.parent
                continue

            # Tag #END is not a true tag: it doesn't correspond to any command.
            if tag != 'END':
                # Create and enter new node.
                node = node.add_child(Node(tag))
                # Detect command optional argument.
                # XXX: tolerate \n and spaces before bracket.
                if text[position] == '[':
                    end = find_closing_bracket(text, position + 1, brackets='[]')
                    node.options = text[position + 1:end]
                    position = end + 1
                # Detect command arguments.
                # Each argument become a node with its number as name.
                number_of_args, closing_tags = self.tags[node.name]
                for i in range(number_of_args):
                    if text[position] == '{':
                        position += 1
                        end = find_closing_bracket(text, position, brackets='{}')
                        new_pos = end + 1
                    else:
                        end = position
                        while end < len(text) and text[end].isalnum():
                            end += 1
                        new_pos = end
                    # Each argument of a command is a node itself.
                    # Nodes corresponding to arguments have no name,
                    # but are numbered instead.
                    arg = node.add_child(Node(i))
                    self._parse(arg, text[position:end])
                    position = new_pos
                if closing_tags is None:
                    # Quit node (tag is self-closing).
                    node = node.parent
                else:
                    node._closing_tags = closing_tags

        node.add_child(text[last_position:])







class LatexGenerator(object):

    convert_tags = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '=': 'EQUAL', '?': 'SIGN'}

    def __init__(self):
        self.parser = SyntaxTreeGenerator()
        self.clear()

    def clear(self):
        self.macros = {}
        self.context = global_context.copy()
        self.context['LATEX'] = []
        # When write() is called from inside a #PYTHON ... #END code block,
        # its argument may contain pTyX code needing parsing.
        self.context['write'] = partial(self.write, parse=True)
        # Internal flags
        self.flags = {}

    def parse(self, text):
        self.parser.parse(text)
        self.parse_node(self.parser.syntax_tree)

    @property
    def NUM(self):
        return self.context.get('NUM', 0)


    def parse_node(self, node):
        u"""Parse a node in a pTyX syntax tree.

        Return True if block content was recursively parsed, and False else.

        In particular, when parsing an IF block, True will be returned if and
        only if the block condition was satisfied.
        """
        tag = self.convert_tags.get(node.name, node.name)
        try:
            method = getattr(self, 'parse_%s_tag' % tag)
        except AttributeError:
            print("Warning: method 'parse_%s_tag' not found" % tag)
        return method(node)

    def parse_children(self, children, function=None, **options):
        if function is not None:
            # Store generated text in a temporary location, instead of self.context['LATEX'].
            # Function `function` will then be applied to this text,
            # before text is appended to self.context['LATEX'].
            backup = self.context['LATEX']
            self.context['LATEX'] = []

        if_state = case_state = False
        for child in children:
            if isinstance(child, basestring):
                self.write(child)
                if_state = case_state = False
            else:
                # All remaining children should be nodes now.
                assert isinstance(child, Node)
                child_name = child.name
                # Nodes are either numbered, or have a name.
                # Numbered nodes correspond to command arguments. Those should
                # have been processed before, and not be passed to parse_children().
                assert isinstance(child_name, basestring)

                # If an IF or ELIF node was processed, all successive ELIF
                # or ELSE nodes must be skipped.
                # So, once an IF or ELIF node is processed, `if_state` is set to True,
                # to indicate that next ELIF or ELSE nodes must be skipped.
                # (The same for CASE.)
                if child_name == 'IF':
                    if_state = self.parse_node(child)
                elif child_name == 'ELIF':
                    # Don't process ELIF node if previous IF node was processed.
                    if if_state:
                        continue
                    if_state = self.parse_node(child)
                elif child_name == 'ELSE':
                    # Don't process ELSE node if previous IF or CASE node was processed.
                    if if_state or case_state:
                        continue
                elif child_name == 'CASE':
                    if case_state:
                        continue
                    case_state = self.parse_node(child)
                else:
                    self.parse_node(child)

                # Initialize case_state and if_state
                if child_name != 'CASE':
                    case_state = False
                if child_name not in ('IF', 'ELIF'):
                    if_state = False

            if function is not None:
                code = function(''.join(self.context['LATEX']), **options)
                self.context['LATEX'] = backup
                self.write(code)


    def parse_options(self, node):
        u'Parse a tag options, following the syntax {key1=val1,...}.'
        options = node.options
        args = []
        kw = {}
        if options is not None:
            options_list = options.split(',')
            for option in options_list:
                if '=' in option:
                    key, val = option.split('=')
                    kw[key.strip()] = val.strip()
                else:
                    args.append(option.strip())
        return args, kw


    def write(self, text, parse=False):
        u"""Append a piece of LaTeX text to context['LATEX'].

        :param text: a block of text, which may contain pTyX code.
        :type text: string
        :param parse: indicate text have to be parsed.
        :type parse: bool

        .. note:: Param `parse` defaults to False, since in most cases text is already
                  parsed at this state.
                  As an exception, when called from inside a #PYTHON [...] #END
                  code block, write() may be applied to unparsed text.
        """
        # Parsing at this stage is quite expansive yet unnecessary most of the time,
        # so some basic testing is done before.
        if parse and '#' in text:
            if param['debug']:
                print('Parsing %s...' % repr(text))
            self.parse(text)
        else:
            self.context['LATEX'].append(text)



    def read(self):
        return ''.join(self.context['LATEX'])

    def parse_IF_tag(self, node):
        test = eval(node.arg(0), self.context)
        if test:
            self.parse_children(node.children[1:])
        return test

    parse_ELIF_tag = parse_IF_tag

    def parse_ELSE_tag(self, node):
        self.parse_children(node.children)

    def parse_IFNUM_tag(self, node):
        if eval(node.arg(0), self.context) == self.NUM:
            self.parse_children(node.children[1:])

    def parse_CASE_tag(self, node):
        test = eval(node.arg(0), self.context) == self.NUM
        if test:
            self.parse_children(node.children[1:])
        return test

    def parse_PYTHON_tag(self, node):
        assert len(node.children == 1)
        python_code = node.children[0]
        assert isinstance(python_code, basestring)
        self._exec_python_code(python_code, self.context)

    #Remove comments before generating tree ?
    def parse_COMMENT_tag(self, node):
        pass

    def parse_ASSERT_tag(self, node):
        code = node.arg(0)
        test = eval(code, self.context)
        if not test:
            print "Error in assertion (NUM=%s):" % self.NUM
            print "***"
            print code
            print "***"
            assert test

    def parse_EVAL_tag(self, node):
        args, kw = self.parse_options(node)
        for arg in args:
            if arg.isdigit():
                self.flags['round'] = int(arg)
            elif arg == 'float':
                self.flags['float'] = True
            else:
                raise ValueError, ('Unknown flag: ' + repr(arg))
        # XXX: support options round, float, (sympy, python,) pick and rand
        code = node.arg(0)
        assert isinstance(code, basestring), type(code)
        self.write(self._eval_python_expr(code))
        self.flags.clear()

    def parse_NEW_MACRO_tag(self, node):
        name = node.arg(0)
        self.macros[name] = node.children[1:]

    def parse_MACRO_tag(self, node):
        name = node.arg(0)
        if name not in self.macros:
            raise NameError, ('Error: MACRO "%s" undefined.' % name)
        self.parse_children(self.macros[name])

    def parse_SHUFFLE_tag(self, node):
        children = random.shuffle(node.children)
        self.parse_children(children)

    def parse_ITEM_tag(self, node):
        self.parse_children(node.children)

    def parse_SEED_tag(self, node):
        if self.NUM == 0:
            random.seed(int(node.arg(0)))

    #~ def parse_PICK_tag(self, node):
        #~ assert len(node.children) == 1
        #~ varname, values = node.children[0].split('=')
        #~ values = values.split(',')
        #~ self.context[varname.strip] = values[self.NUM%len(values)]

    def parse_PICK_tag(self, node):
        self.flags['pick'] = True
        self.parse_EVAL_tag(self, node)

    def parse_RAND_tag(self, node):
        self.flags['rand'] = True
        self.parse_EVAL_tag(self, node)

    def parse_ROOT_tag(self, node):
        self.parse_children(node.children)

    def parse_TABVAL_tag(self, node):
        from wxgeometrie import tabval
        options = self.parse_options(node.options)
        self.parse_children(node.children, function=tabval, **options)

    def parse_TABVAR_tag(self, node):
        from wxgeometrie import tabvar
        options = self.parse_options(node.options)
        self.parse_children(node.children, function=tabvar, **options)

    def parse_TABSIGN_tag(self, node):
        from wxgeometrie import tabsign
        options = self.parse_options(node.options)
        self.parse_children(node.children, function=tabsign, **options)

    def parse_TEST_tag(self, node):
        if eval(node.arg(0), self.context):
            self.parse_children(node.children[1:])

    def parse_ADD_tag(self, node):
        self.flags['+'] = True

    def parse_SUB_tag(self, node):
        self.flags['-'] = True

    def parse_MUL_tag(self, node):
        self.flags['*'] = True

    def parse_EQUAL_tag(self, node):
        self.flags['='] = True
        self.write('#=')

    def parse_SIGN_tag(self, node):
        last_value = self.context['_']
        if last_value > 0:
            self.write('>0')
        elif last_value < 0:
            self.write('<0')

    def parse_SYMPY_tag(self, node):
        raise NotImplementedError

    def parse_GEO_tag(self, node):
        raise NotImplementedError

    def parse_DEBUG_tag(self, node):
        raise NotImplementedError

    def _exec(self, code, context):
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

    def _exec_python_code(self, code, context):
        code = code.replace('\r', '')
        code = code.rstrip().lstrip('\n')
        # Indentation test
        initial_indent = len(code) - len(code.lstrip(' '))
        if initial_indent:
            # remove initial indentation
            code = '\n'.join(line[initial_indent:] for line in code.split('\n'))
        self._exec(code, context)
        return code


    def _eval_python_expr(self, code):
        flags = self.flags
        context = self.context
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
                result = self._eval_python_expr(subcode)
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
                _ = context[varname] = result = self._apply_flag(result)
            else:
                key = eval(varname[i+1:-1], context)
                varname = varname[:i]
                _ = context[varname][key] = result = self._apply_flag(result)
            context['_']  = _

        if not display_result:
            return ''
        if sympy_code:
            latex = print_sympy_expr(result, **flags)
        else:
            latex = str(result)

        def neg(latex):
            return latex.lstrip()[0] == '-'

        if flags.get('+'):
            if not neg(latex):
                latex = '+' + latex
        elif flags.get('*'):
            if neg(latex):
                latex = r'\left(' + latex + r'\right)'
            latex = r'\times ' + latex
        elif flags.get('-'):
            if neg(latex):
                latex = r'\left(' + latex + r'\right)'
            latex = '-' + latex
        elif flags.get('='):
            if flags.get('result_is_exact'):
                symb = ' = '
            else:
                symb = r' \approx '
            # Search backward for temporary `#=` marker in list, and replace
            # by appropriate symbol.
            textlist = context['LATEX']
            for i, elt in enumerate(reversed(textlist)):
                if elt == '#=':
                    textlist[len(textlist) - i - 1] = symb
                    break
            else:
                print("Debug warning: `#=` couldn't be found when scanning context !")
        return latex


    def _apply_flag(self, result):
        '''Apply [num] and [rand] special parameters to result.

        Note that both parameters require that result is iterable, otherwise, nothing occures.
        If result is iterable, an element of result is returned, choosed according to current flag.'''
        flags = self.flags
        context = self.context
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
                print ''.join(self.context['LATEX'])[-100:]
                print "-----"
                raise
            flags['result_is_exact'] = (result == round_result)
            result = round_result
        else:
            context.result_is_exact = True
        return result




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
