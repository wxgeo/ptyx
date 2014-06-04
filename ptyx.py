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


__version__ = "2.0"
__release_date__ = (31, 10, 2013)


print 'Ptyx ' + __version__ + ' ' + '/'.join(str(d) for d in __release_date__)

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


import optparse, re, random, os, tempfile, sys, codecs, csv, shutil, subprocess
from functools import partial
from math import ceil, floor, isnan, isinf
from fractions import gcd

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('cp850')(sys.stdout)
else:
    sys.stdout = codecs.getwriter('utf8')(sys.stdout)

def execute(string, quiet=False):
    out = subprocess.Popen(string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    output = out.read()
    sys.stdout.write(output)
    out.close()
    if not quiet:
        print "Command '%s' executed." %string
    return output

for pathname in ('sympy_path', 'wxgeometrie_path'):
    path = param[pathname]
    if path is not None:
        path = os.path.normpath(os.path.expanduser(path))
        sys.path.insert(0, path)
        param[pathname] = path

try:
    import sympy
    from sympy.core.sympify import SympifyError
    from sympy import S, preorder_traversal, Symbol
except ImportError:
    print("** ERROR: sympy not found ! **")
    sympy = None
    param['sympy_is_default'] = False

try:
    import wxgeometrie
    try:
        #~ from wxgeometrie.modules import tablatex
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




def randint(a=None, b=None, exclude=()):
    if b is None:
        b = (9 if a is None else a)
        a = 2
    while True:
        val = random.randint(a, b)
        if val not in exclude:
            break
    if param['sympy_is_default']:
        val = S(val)
    return val

def srandint(a=None, b=None, exclude=()):
    while True:
        val = (-1)**randint(0, 1)*randint(a, b)
        if val not in exclude:
            return val

def randbool():
    return bool(randint(0, 1))

def randpoint(a=None, b=None, exclude=()):
    while True:
        x = randint(a, b)
        y = randint(a, b)
        if (x, y) not in exclude:
            return (x, y)

def srandpoint(a=None, b=None, exclude=()):
    while True:
        x = srandint(a, b)
        y = srandint(a, b)
        if (x, y) not in exclude:
            return (x, y)

def randfrac(a=None, b=None, exclude=(), not_decimal=False, d=None):
    '''Return a random fraction which is never an integer.

    Use `d` to specify denominator value; `d` must be an integer or a tuple
    of integers.
    '''
    if b is None:
        b = (9 if a is None else a)
        a = 2
    if (d is None and a in (-1, 0, 1) and b in (-1, 0, 1)) or a == b:
        # This would lead to infinite loop.
        raise ValueError, ('(%s, %s) are not valid parameters.' % (a, b))
    while True:
        if d is None:
            d = randint(a, b)
            if d in (0, 1):
                continue
            n = randint(a, b)
        else:
            n = randint(a, b)
            if hasattr(d, '__iter__'):
                d = random.choice(list(d))
            if gcd(d, n) not in (-1, 1):
                # XXX this may lead to infinite loop if wrong arguments are passed
                continue
        val = S(n)/S(d)
        # XXX: Improve following test.
        if not_decimal and (val*10**1000).is_integer:
            # XXX this may lead to infinite loop if wrong arguments are passed
            continue
        if not val.is_integer and val not in exclude:
            return val

def srandfrac(a=None, b=None, exclude=(), not_decimal=False, d=None):
    while True:
        val = (-1)**randint(0, 1)*randfrac(a, b, not_decimal=not_decimal, d=d)
        if val not in exclude:
            return val


def randchoice(*items, **kw):
    """Select randomly an item.
    """
    if len(items) == 1 and hasattr(items[0], '__iter__'):
        items = items[0]
    if kw.get('signed'):
        items = list(items) + [-1*item for item in items]
    if 'exclude' in kw:
        items = [val for val in items if val not in kw['exclude']]
    val = random.choice(items)
    if isinstance(val, (int, long, float, complex)):
        val = S(val)
    return val

def srandchoice(*items, **kw):
    kw['signed'] = True
    return randchoice(*items, **kw)

def round(val, ndigits=0):
    u"""Round using round-away-from-zero strategy for halfway cases.

    Python 3+ implements round-half-even, and Python 2.7 has a random behaviour
    from end user point of view (in fact, result depends on internal
    representation in floating point arithmetic).
    """
    val = float(val)
    if isnan(val) or isinf(val):
        return val
    s = repr(val).rstrip('0')
    if 'e' in s:
        # XXX: implement round-away-from-zero in this case too.
        return __builtins__.round(val, ndigits)
    sep = s.find('.')
    pos = sep + ndigits
    if ndigits <= 0:
        pos -= 1
    # Skip dot if needed to reach next digit.
    next_pos = (pos + 1 if pos + 1 != sep else pos + 2)
    if next_pos < 0 or next_pos == 0 and s[next_pos] == '-':
        return 0.
    if len(s) <= next_pos:
        # No need to round (no digit after).
        return val
    power = 10**ndigits
    if s[next_pos] in '01234':
        return (floor(val*power)/power if val > 0 else ceil(val*power)/power)
    else:
        return (ceil(val*power)/power if val > 0 else floor(val*power)/power)


global_context = SpecialDict()

#~ math_list = ('cos', 'sin', 'tan', 'ln', 'exp', 'diff', 'limit',
             #~ 'integrate', 'E', 'pi', 'I', 'oo', 'gcd', 'lcm', 'floor',
             #~ 'ceiling',)

if sympy is not None:
    global_context['sympy'] = sympy
    global_context['sympify'] = global_context['SY'] = sympy.sympify
    #~ for name in math_list:
        #~ global_context[name] = getattr(sympy, name)
    exec('from sympy import *', global_context)
    exec('var("x y")', global_context)
    #~ global_context['x'] = sympy.Symbol('x')

if numpy is not None:
    global_context['numpy'] = numpy

global_context['sign'] = lambda x: ('+' if x > 0 else '-')
global_context['round'] = round
global_context['min'] = min
global_context['max'] = max
global_context['rand'] = global_context['random'] = random.random
global_context['ceil'] = global_context['ceiling']

global_context['randpoint'] = randpoint
global_context['srandpoint'] = srandpoint
global_context['randint'] = randint
global_context['randbool'] = randbool
global_context['randsignint'] = srandint
global_context['srandint'] = srandint
global_context['randfrac'] = randfrac
global_context['srandfrac'] = srandfrac
global_context['randchoice'] = randchoice
global_context['srandchoice'] = srandchoice
# If a document is compiled several times (to produce different versions of the same document),
# NUM is the compilation number (starting from 0).
global_context['NUM'] = 0




def find_closing_bracket(text, start = 0, brackets = '{}', detect_strings=True):
    """Find the closing bracket, starting from position `start`.

    Note that start have to be a position *after* the opening bracket.

    >>> from ptyx import find_closing_bracket
    >>> find_closing_bracket('{{hello} world !}', start=1)
    16

    By default, inner strings are handled, so that in "{'}'}", second } will be
    reported as closing bracket, since '}' is seen as an inner string.
    To disable the detection of inner strings, use `detect_strings=False`.

    >>> find_closing_bracket("{'}'}", start=1)
    4
    >>> find_closing_bracket("{'}'}", start=1, detect_strings=False)
    2
    """
    text_beginning = text[start:start + 30]
    # for debugging
    index = 0
    balance = 1
    # None if we're not presently in a string
    # Else, string_type may be ', ''', ", or """
    string_type = None

    open_bracket = brackets[0]
    close_bracket = brackets[1]

    # ', ", { and } are matched.
    # Note that if brackets == '[]', bracket ] must appear first in
    # regular expression ('[]"\'[]' is valid, but '[["\']]' is not).
    reg_str = '[%s"\'%s]' if detect_strings else '[%s%s]'
    reg = re.compile(reg_str % (close_bracket, open_bracket))

    if start:
        text = text[start:]
    while balance:
        m = re.search(reg, text)
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
                if text[i:].startswith(3*result):
                    string_type = 3*result
                    i += 2
                else:
                    string_type = result
            elif string_type == result:
                string_type = None
            elif string_type == 3*result:
                if text[i:].startswith(3*result):
                    string_type = None
                    i += 2

        i += 1 # counting the current caracter as already scanned text
        index += i
        text = text[i:]

    else:
        return start + index - 1 # last caracter is the searched bracket :-)

    raise ValueError, 'ERROR: unbalanced brackets (%s) while scanning %s...' %(balance, repr(text_beginning))



#~ def tree_to_expr(tree):
    #~ u"""Convert a tree of sympy atoms to a sympy expression."""
    #~ if isinstance(tree, list):
        #~ # node
        #~ func = tree[0]
        #~ args = tree[1:]
        #~ return func(*(tree_to_expr(arg) for arg in args))
    #~ else:
        #~ # leaf
        #~ return tree



#~ def expr_to_tree(expr):
    #~ u"""Convert a sympy expression to a tree.
#~
    #~ If `expr` has no argument, it's a leaf, so it will be returned untouched.
    #~ """
    #~ args = expr.args
    #~ if args:
        #~ # node
        #~ return [expr.func] + [expr_to_tree(arg) for arg in args]
    #~ else:
        #~ # leaf
        #~ return expr
#~
#~
#~ def _convert_inner_rationals_to_floats(tree, integers, ndigits=None):
    #~ u"""Convert **in place** rationals to floats inside a sympy tree."""
    #~ if isinstance(tree, list):
        #~ for i, node in enumerate(tree):
            #~ if isinstance(node, sympy.Integer) and not integers:
                #~ continue
            #~ elif isinstance(node, sympy.Rational):
                #~ if ndigits is not None:
                    #~ f = sympy.Float(repr(round(node, ndigits)))
                #~ else:
                    #~ f = sympy.Float(node)
                #~ tree[i] = f
            #~ else:
                #~ _convert_inner_rationals_to_floats(node, integers=integers, ndigits=ndigits)
#~
#~ def rationals_to_floats(expr, integers=False, ndigits=None):
    #~ u"""Recursively convert rationals to floats inside a sympy expression."""
    #~ tree = expr_to_tree(expr)
    #~ _convert_inner_rationals_to_floats(tree, integers=integers, ndigits=ndigits)
    #~ return tree_to_expr(tree)

def _float_me_if_you_can(expr):
    try:
        return float(expr)
    except:
        return expr

def numbers_to_floats(expr, integers=False, ndigits=None):
    u"""Convert all numbers (except integers) to floats inside a sympy expression."""
    if not sympy or not isinstance(expr, sympy.Basic):
        if isinstance(expr, (long, int)) and not integer:
            return expr
        elif ndigits is not None:
            return round(expr, ndigits)
        else:
            return float(expr)
    for sub in preorder_traversal(expr):
        sub = sympy.sympify(sub)
        if not sub.has(Symbol) and (integers or not sub.is_Integer):
            new = sub.evalf()
            if ndigits is not None:
                new = round(new, ndigits)
            expr = expr.subs(sub, new)
    return expr


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
#TEST{bool}{...}{...}
#+, #-,  #*, #=, #? (special operators)
#varname or #[option,int]varname
## options : sympy, python, float
## int : round






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
        children_number = len(child.children)
        if children_number > 1:
            raise ValueError, ("Don't use pTyX code inside %s argument number %s." % (self.name, i + 1))
        elif children_number == 0:
            raise ValueError, ("%s argument number %s should not be empty !" % (self.name, i + 1))

        return child.children[0]


    def display(self, color=True, indent=0):
        texts = ['%s+ Node %s' % (indent*' ', self._format(self.name, color))]
        for child in self.children:
            if isinstance(child, Node):
                texts.append(child.display(color, indent + 2))
            else:
                lines = child.split('\n')
                text = lines[0]
                if len(lines) > 1:
                    text += ' [...]'
                text = repr(text)
                if color:
                    text = self.green(text)
                texts.append('%s  - text: %s' % (indent*' ', text))
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
    def green(self, s):
        return '\033[0;32m' + s + '\033[0m'
#~
    #~ def green2(self, s):
        #~ return '\033[1;32m' + s + '\033[0m'
#~
    def yellow(self, s):
        return '\033[0;33m' + s + '\033[0m'
#~
    #~ def white(self, s):
        #~ return '\033[1;37m' + s + '\033[0m'





class SyntaxTreeGenerator(object):
    # For each tag, indicate:
    #   1. The number of arguments containing code.
    #      Those arguments will be interpreted as python code.
    #   2. The number of raw arguments.
    #      Those arguments contain raw text.
    #   3. If the tag opens a block, a list of all the tags closing the block.
    #
    # Notice that by default, the tag closing the block will not be consumed.
    # This means that the same tag will be parsed again to open or close another block.
    # To consume the closing tag, prefix the tag name with the '@' symbol.
    # This is usually the wished behaviour for #END tag.
    #
    # Distinction between code arguments and raw arguments must be done because
    # in raw arguments, there should be no detection of inner strings:
    # in {$f'(x)$}, the ' must not be interpreted as an opening string, so closing
    # bracket is the one following the $.
    # By contrast, in code arguments, inner strings should be detected:
    # in {val=='}'}, the bracket closing the tag is the second }, not the first one !

    tags = {'ASSERT':       (1, 0, None),
            'CALC':         (1, 0, None),
            # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
            'CASE':         (1, 0, ['CASE', 'ELSE', 'END']),
            'COMMENT':      (0, 0, ['@END']),
            # CONDITIONAL_BLOCK isn't a real tag, but is used to enclose
            # a #CASE{...}...#CASE{...}...#END block, or an #IF{...}...#ELIF{...}...#END block.
            'CONDITIONAL_BLOCK':    (0, 0, ['@END']),
            'DEBUG':        (0, 0, None),
            'EVAL':         (1, 0, None),
            'GEO':          (0, 0, ['@END']),
            # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
            'IF':           (1, 0, ['ELIF', 'ELSE', 'END']),
            # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
            'ELIF':         (1, 0, ['ELIF', 'ELSE', 'END']),
            # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
            'ELSE':         (0, 0, ['END']),
            'END':          (0, 0, None),
            'FREEZE_RANDOM_STATE': (0, 0, []),
            'GCALC':        (0, 0, ['@END']),
            'IFNUM':        (1, 1, None),
            'MACRO':        (0, 1, None),
            'NEW_MACRO':    (0, 1, ['@END']),
            'PICK':         (1, 0, None),
            'PYTHON':       (0, 0, ['@END']),
            'RAND':         (1, 0, None),
            # ROOT isn't a real tag, and is never closed.
            'ROOT':         (0, 0, []),
            'SEED':         (1, 0, None),
            'SHUFFLE':      (0, 0, ['@END']),
            # Do *NOT* consume #END tag, which must be used to end #SHUFFLE block.
            'ITEM':         (0, 0, ['ITEM', 'END']),
            'SIGN':         (0, 0, None),
            'SYMPY':        (0, 0, ['@END']),
            'TABSIGN':      (0, 0, ['@END']),
            'TABVAL':       (0, 0, ['@END']),
            'TABVAR':       (0, 0, ['@END']),
            'TEST':         (1, 2, None),
            '-':            (0, 0, None),
            '+':            (0, 0, None),
            '*':            (0, 0, None),
            '=':            (0, 0, None),
            '?':            (0, 0, None),
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
        return self.syntax_tree

    def _parse(self, node, text):
        position = 0
        update_last_position = True
        node._closing_tags = []

        while True:
            # --------------
            # Find next tag.
            # --------------
            # A tag starts with '#'.

            # last_position should not be updated if false positives
            # were encoutered (ie. #1, #2 in \newcommand{}...).
            if update_last_position:
                last_position = position
            else:
                update_last_position = True
            position = tag_position = text.find('#', position)
            if position == -1:
                # No tag anymore.
                break
            position += 1
            # Is this a known tag ?
            for tag in self.sorted_tags:
                if text[position:].startswith(tag):
                    # Mmmh, this begins like a known tag...
                    # Infact, it will really match a known tag if one of the following occures:
                    # - next character is not alphanumeric ('#IF{' for example).
                    # - tag is not alphanumeric ('#*' tag for example).
                    if not tag[-1].replace('_', 'a').isalnum():
                        # Tag is not alphanumeric, so no confusion with a variable name can occure.
                        # -> yes, a known tag found !
                        position += len(tag)
                        break
                    if position + len(tag) == len(text):
                        # There is no next character (last text character reached).
                        # -> yes, a known tag found !
                        position += len(tag)
                        break
                    next_character = text[position + len(tag)]
                    if not(next_character == '_' or next_character.isalnum()):
                        # Next character is not alphanumeric
                        # -> yes, a known tag found !
                        position += len(tag)
                        break
                    # -> sorry, try again.
            else:
                if text[position].isdigit():
                    # This not a tag: LaTeX uses #1, #2, #3 as \newcommand{} parameters.
                    # Pretend nothing happened.
                    update_last_position = False
                    continue
                else:
                    # This is not a known tag name.
                    # Default tag name is EVAL.
                    tag = 'EVAL'

            # ------------------------
            # Deal with new found tag.
            # ------------------------

            # Add text found before this tag to the syntax tree.
            # --------------------------------------------------
            if text[tag_position - 1] == '\n' and (self.tags[tag][2] is not None or tag == 'END'):
                # Remove new line before #IF, #ELSE, ... tags.
                node.add_child(text[last_position:tag_position - 1])
            else:
                node.add_child(text[last_position:tag_position])

            # Enclose "CASE ... CASE ... ELSE ... END" or "IF ... ELIF ... ELSE ... END"
            # inside a CONDITIONAL_BLOCK node.
            # --------------------------------------------------------------------------
            #
            # The most subtle part while parsing pTyX code is to distinguish
            # between "#CASE{0}...#CASE{1}...#ELSE...#END"
            # and "#CASE{0}...#END#CASE{1}...#ELSE...#END".
            # This distinction is needed because, in case NUM==0, the ELSE clause
            # must be executed in the 2nde version, and not in the 1st one.
            #
            # This is one of the reasons why CASE nodes are enclosed inside a CONDITIONAL_BLOCK.
            # So, first version must result in only one CONDITIONAL_BLOCK,
            # while 2nd version must result in 2 CONDITIONAL_BLOCKs.
            #
            # The rule is actually quite simple: a #CASE tag must open a new CONDITIONAL_BLOCK
            # only if previous opened node wasn't a #CASE node.
            #
            # Note that for #IF blocks, there is no such subtility,
            # because an #IF tag always opens a new CONDITIONAL_BLOCK.
            if (tag == 'CASE' and node.name != 'CASE') or tag == 'IF':
                node = node.add_child(Node('CONDITIONAL_BLOCK'))
                node._closing_tags = self.tags['CONDITIONAL_BLOCK'][2]

            # Detect if this tag is actually closing a node.
            # ----------------------------------------------
            while tag in node._closing_tags:
                # Close node, but don't consume tag.
                node = node.parent
            if '@' + tag in node._closing_tags:
                # Close node and consume tag.
                node = node.parent
                continue


            # Special case : don't parse #PYTHON ... #END content.
            # ----------------------------------------------------
            if tag == 'PYTHON':
                end = text.index('#END', position)
                # Create and enter new node.
                node = node.add_child(Node(tag))
                node.add_child(text[position:end])
                node = node.parent
                position = end + 4

            # General case
            # ------------
            # Exclude #END, since it's not a true tag.
            # (It's only purpose is to close a block, #END doesn't correspond to any command).
            elif tag != 'END':
                # Create and enter new node.
                # ~~~~~~~~~~~~~~~~~~~~~~~~~~
                node = node.add_child(Node(tag))
                # Detect command optional argument.
                # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                # XXX: tolerate \n and spaces before bracket.
                if text[position] == '[':
                    position += 1
                    end = find_closing_bracket(text, position, brackets='[]')
                    node.options = text[position:end]
                    position = end + 1
                # Detect command arguments.
                # ~~~~~~~~~~~~~~~~~~~~~~~~~
                # Each argument become a node with its number as name.
                code_args_number, raw_args_number, closing_tags = self.tags[node.name]
                for i in range(code_args_number + raw_args_number):
                    if text[position] == '{':
                        position += 1
                        # Detect inner strings for arguments containing code,
                        # but not for arguments containing raw text.
                        end = find_closing_bracket(text, position, brackets='{}',
                                            detect_strings=(i<code_args_number))
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
                # Close node if needed.
                # ~~~~~~~~~~~~~~~~~~~~~~~
                if closing_tags is None:
                    # Close node (tag is self-closing).
                    node = node.parent
                else:
                    # Store node closing tags for fast access later.
                    node._closing_tags = closing_tags

        node.add_child(text[last_position:])




# XXX: Currently, ptyx files are opened as string, not as unicode.
# Pro:
# - Ptyx doesn't have to be encoding aware (no need to specify encoding before proceeding).
# Contra:
# - Python variables defined in a ptyx file must not contain unicode context.
# - This will break in Python 3+.
# TODO: Use unicode instead. Autodetect encoding on Linux (`file --mime-encoding FILENAME`).



class LatexGenerator(object):
    u"""Convert text containing ptyx tags to plain LaTeX."""

    convert_tags = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '=': 'EQUAL', '?': 'SIGN'}

    re_varname = re.compile('[A-Za-z_][A-Za-z0-9_]*([[].+[]])?$')

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
        u"""Convert text containing ptyx tags to plain LaTeX.

        :param text: a pTyX file content, to be converted to plain LaTeX.
        :type text: str
        """
        self.parser.parse(text)
        self.parse_node(self.parser.syntax_tree)

    @property
    def NUM(self):
        return self.context['NUM']


    def parse_node(self, node):
        u"""Parse a node in a pTyX syntax tree.

        Return True if block content was recursively parsed, and False else.

        In particular, when parsing an IF block, True will be returned if and
        only if the block condition was satisfied.
        """
        tag = self.convert_tags.get(node.name, node.name)
        try:
            method = getattr(self, '_parse_%s_tag' % tag)
        except AttributeError:
            print("Error: method '_parse_%s_tag' not found" % tag)
            raise
        return method(node)

    def _parse_children(self, children, function=None, **options):
        if function is not None:
            # Store generated text in a temporary location, instead of self.context['LATEX'].
            # Function `function` will then be applied to this text,
            # before text is appended to self.context['LATEX'].
            backup = self.context['LATEX']
            self.context['LATEX'] = []

        for child in children:
            if isinstance(child, basestring):
                self.write(child)
            else:
                # All remaining children should be nodes now.
                assert isinstance(child, Node)
                # Nodes are either numbered, or have a name.
                # Numbered nodes correspond to command arguments. Those should
                # have been processed before, and not be passed to _parse_children().
                assert isinstance(child.name, basestring)

                self.parse_node(child)

        if function is not None:
            code = function(''.join(self.context['LATEX']), **options)
            self.context['LATEX'] = backup
            self.write(code)


    def _parse_options(self, node):
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
        text = str(text)
        if text.strip():
            for flag in '+-*':
                if self.flags.get(flag):
                    text = (r'\times ' if flag == '*' else flag) + text
                    self.flags[flag] = False
        if parse and '#' in text:
            if param['debug']:
                print('Parsing %s...' % repr(text))
            self.parse(text)
        else:
            self.context['LATEX'].append(text)

    def read(self):
        return ''.join(self.context['LATEX'])


    def _parse_IF_tag(self, node):
        test = eval(node.arg(0), self.context)
        if test:
            self._parse_children(node.children[1:])
        return test

    _parse_ELIF_tag = _parse_IF_tag

    def _parse_CONDITIONAL_BLOCK_tag(self, node):
        for child in node.children:
            assert isinstance(child, Node)
            if self.parse_node(child):
                # If an IF or ELIF node was processed, all successive ELIF
                # or ELSE nodes must be skipped.
                # (The same for CASE).
                break

    def _parse_ELSE_tag(self, node):
        self._parse_children(node.children)

    def _parse_IFNUM_tag(self, node):
        if eval(node.arg(0), self.context) == self.NUM:
            self._parse_children(node.children[1].children)

    def _parse_CASE_tag(self, node):
        test = eval(node.arg(0), self.context) == self.NUM
        if test:
            self._parse_children(node.children[1:])
        return test

    def _parse_PYTHON_tag(self, node):
        assert len(node.children) == 1
        python_code = node.children[0]
        assert isinstance(python_code, basestring)
        self._exec_python_code(python_code, self.context)

    #Remove comments before generating tree ?
    def _parse_COMMENT_tag(self, node):
        pass

    def _parse_CALC_tag(self, node):
        args, kw = self._parse_options(node)
        assert len(args) <= 1 and len(kw) == 0
        name = (args[0] if args else 'RESULT')
        from wxgeometrie.mathlib.parsers import traduire_formule
        fonctions = [key for key, val in self.context.items() if isinstance(val, (type(sympy.sqrt), type(sympy.cos)))]
        def eval_and_store(txt, name):
            self.context[name] = self._eval_python_expr(traduire_formule(txt, fonctions=fonctions))
            return txt
        self._parse_children(node.children[0].children, function=eval_and_store, name=name)

    def _parse_ASSERT_tag(self, node):
        code = node.arg(0)
        test = eval(code, self.context)
        if not test:
            print "Error in assertion (NUM=%s):" % self.NUM
            print "***"
            print code
            print "***"
            assert test

    def _parse_EVAL_tag(self, node):
        args, kw = self._parse_options(node)
        for arg in args:
            if arg.isdigit():
                self.flags['round'] = int(arg)
            elif arg == '.':
                self.flags['.'] = True
            elif arg == 'floats':
                self.flags['floats'] = True
            elif arg == 'str':
                self.flags['str'] = True
            else:
                raise ValueError, ('Unknown flag: ' + repr(arg))
        # XXX: support options round, float, (sympy, python,) pick and rand
        code = node.arg(0)
        assert isinstance(code, basestring), type(code)
        txt = self._eval_and_format_python_expr(code)
        # Tags must be cleared *before* calling .write(txt), since .write(txt)
        # add '+', '-' and '\times ' before txt if corresponding flags are set,
        # and ._eval_and_format_python_expr() has already do this.
        self.flags.clear()
        self.write(txt)

    def _parse_NEW_MACRO_tag(self, node):
        name = node.arg(0)
        self.macros[name] = node.children[1:]

    def _parse_MACRO_tag(self, node):
        name = node.arg(0)
        if name not in self.macros:
            raise NameError, ('Error: MACRO "%s" undefined.' % name)
        self._parse_children(self.macros[name])

    def _parse_SHUFFLE_tag(self, node):
        children = node.children[:]
        random.shuffle(children)
        self._parse_children(children)

    def _parse_ITEM_tag(self, node):
        self._parse_children(node.children)

    def _parse_SEED_tag(self, node):
        value = int(node.arg(0))
        # Keep track of seed value. This is used to generate a .seed file.
        self.context['SEED'] = value
        random.seed(value + self.NUM)

    #~ def parse_PICK_tag(self, node):
        #~ assert len(node.children) == 1
        #~ varname, values = node.children[0].split('=')
        #~ values = values.split(',')
        #~ self.context[varname.strip] = values[self.NUM%len(values)]

    def _parse_PICK_tag(self, node):
        self.flags['pick'] = True
        self._parse_EVAL_tag(node)

    def _parse_RAND_tag(self, node):
        self.flags['rand'] = True
        self._parse_EVAL_tag(node)

    def _parse_ROOT_tag(self, node):
        self._parse_children(node.children)

    def _parse_FREEZE_RANDOM_STATE_tag(self, node):
        state = random.getstate()
        self._parse_children(node.children)
        random.setstate(state)

    def _parse_TABVAL_tag(self, node):
        from wxgeometrie.modules.tablatex import tabval
        args, kw = self._parse_options(node)
        for key in kw:
            kw[key] = eval(kw[key])
        self._parse_children(node.children, function=tabval, **kw)

    def _parse_TABVAR_tag(self, node):
        from wxgeometrie.modules.tablatex import tabvar
        state = random.getstate()
        args, kw = self._parse_options(node)
        for key in kw:
            kw[key] = eval(kw[key])
        self._parse_children(node.children, function=tabvar, **kw)
        random.setstate(state)

    def _parse_TABSIGN_tag(self, node):
        from wxgeometrie.modules.tablatex import tabsign
        state = random.getstate()
        args, kw = self._parse_options(node)
        for key in kw:
            kw[key] = eval(kw[key])
        self._parse_children(node.children, function=tabsign, **kw)
        random.setstate(state)

    def _parse_GCALC_tag(self, node):
        if not wxgeometrie:
            raise ImportError, 'Library wxgeometrie not found !'
        from wxgeometrie.mathlib.interprete import Interprete
        state = random.getstate()
        args, kw = self._parse_options(node)
        for key in kw:
            kw[key] = eval(kw[key])
        def _eval2latex(code):
            print('code::' + repr(code))
            return Interprete(**kw).evaluer(code.strip())[1]
        self._parse_children(node.children, function=_eval2latex, **kw)
        random.setstate(state)


    def _parse_TEST_tag(self, node):
        try:
            if eval(node.arg(0), self.context):
                self._parse_children(node.children[1].children)
            else:
                self._parse_children(node.children[2].children)
        except:
            print(node.display(color=False))
            raise

    def _parse_ADD_tag(self, node):
        # a '+' will be displayed at the beginning of the next result if positive ;
        # if result is negative, nothing will be done, and if null, no result at all will be displayed.
        self.flags['+'] = True

    def _parse_SUB_tag(self, node):
        # a '-' will be displayed at the beginning of the next result, and the result
        # will be embedded in parenthesis if negative.
        self.flags['-'] = True

    def _parse_MUL_tag(self, node):
        # a '\times' will be displayed at the beginning of the next result, and the result
        # will be embedded in parenthesis if negative.
        self.flags['*'] = True

    def _parse_EQUAL_tag(self, node):
        # Display '=' or '\approx' when a rounded result is requested :
        # if rounded is equal to exact one, '=' is displayed.
        # Else, '\approx' is displayed instead.
        self.flags['='] = True
        # All other operations (#+, #-, #*) occur just before number, but between `=` and
        # the result, some formating instructions may occure (like '\fbox{' for example).
        # So, `#=` is used as a temporary marker, and will be replaced by '=' or '\approx' later.
        self.write('#=')

    def _parse_SIGN_tag(self, node):
        # '>0' or '<0' will be displayed after the next result, depending on it's sign.
        # (If result is zero, this won't do anything.)
        last_value = self.context['_']
        if last_value > 0:
            self.write('>0')
        elif last_value < 0:
            self.write('<0')

    def _parse_SYMPY_tag(self, node):
        raise NotImplementedError

    def _parse_GEO_tag(self, node):
        raise NotImplementedError

    def _parse_DEBUG_tag(self, node):
        while True:
            command = raw_input('Debug point. Enter command, or quit (q! + ENTER):')
            if command == 'q!':
                break
            else:
                print(eval(command, self.context))

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

        if sympy_code and sympy is None:
            raise ImportError, 'sympy library not found.'

        varname = ''
        i = code.find('=')
        if 0 < i < len(code) - 1 and code[i + 1] != '=':
            varname = code[:i].strip()
            if re.match(self.re_varname, varname):
                # This is (probably) a variable name (or a list or dict item reference).
                code = code[i + 1:]
            else:
                # This is not a variable name.
                varname = ''
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
                print("Warning: sympy can't parse %s. "
                      "Switching to standard evaluation mode." % repr(code))
            except Exception:
                #~ print sorted(context.keys())
                print("Uncatched error when evaluating %s" % repr(code))
                raise
        if not sympy_code:
            result = eval(code, context)
        result = context['_']  = self._apply_flag(result)
        i = varname.find('[')
        # for example, varname == 'mylist[i]' or 'mylist[2]'
        if i == -1:
            context[varname] = result
        else:
            key = eval(varname[i+1:-1], context)
            varname = varname[:i].strip()
            context[varname][key] = result
        return result



    def _eval_and_format_python_expr(self, code):
        flags = self.flags
        context = self.context
        if not code:
            return ''
        sympy_code = flags.get('sympy', param['sympy_is_default'])

        for subcode in code.split(';'):
            result = self._eval_python_expr(subcode)
            # Note that only last result will be displayed.
            # In particular, if code ends with ';', last result will be ''.
            # So, '#{a=5}' and '#{a=5;}' will both affect 5 to a,
            # but the second will not display '5' on final document.

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
            if neg(latex) or getattr(result, 'is_Add', False):
                latex = r'\left(' + latex + r'\right)'
            latex = r'\times ' + latex
        elif flags.get('-'):
            if neg(latex) or getattr(result, 'is_Add', False):
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
        '''Apply special parameters like [num], [rand], [floats] or [round] to result.

        Note that [num] and [rand] parameters require that result is iterable, otherwise, nothing occures.
        If result is iterable, an element of result is returned, choosed according to current flag.'''
        flags = self.flags
        context = self.context
        if  hasattr(result, '__iter__'):
            if flags.get('rand', False):
                result = random.choice(result)
            elif flags.get('pick', False):
                result = result[self.NUM%len(result)]

        if 'round' in flags:
            try:
                if sympy:
                    round_result = numbers_to_floats(result, ndigits=flags['round'])
                else:
                    round_result = round(result, flags['round'])
            except ValueError:
                print "** ERROR while rounding value: **"
                print result
                print "-----"
                print ''.join(self.context['LATEX'])[-100:]
                print "-----"
                raise
            if sympy and isinstance(result, sympy.Basic):
                flags['result_is_exact'] = (
                    {_float_me_if_you_can(elt) for elt in result.atoms()} ==
                    {_float_me_if_you_can(elt) for elt in round_result.atoms()})
            else:
                flags['result_is_exact'] = (result == round_result)
            result = round_result
        elif 'floats' in self.flags:
            result = numbers_to_floats(result)
        else:
            context.result_is_exact = True
        return result




def print_sympy_expr(expr, **flags):
    if flags.get('str'):
        latex = str(expr)
    elif isinstance(expr, float) or (sympy and isinstance(expr, sympy.Float)) \
            or flags.get('.'):
        # -0.06000000000000001 means probably -0.06 ; that's because
        # floating point arithmetic is not based on decimal numbers, and
        # so some decimal numbers do not have exact internal representation.
        # Python str() handles this better than sympy.latex()
        latex = str(float(expr))

        # Strip unused trailing 0.
        latex = latex.rstrip('0').rstrip('.')
    elif wxgeometrie is not None:
        latex = custom_latex(expr, mode='plain')
    elif sympy and expr is sympy.oo:
        latex = r'+\infty'
    else:
        latex = sympy.latex(expr)
    if isinstance(expr, float) or (sympy and isinstance(expr, sympy.Basic)):
        # In french, german... a comma is used as floating point.
        # However, if `float` flag is set, floating point is left unchanged
        # (useful for Tikz for example).
        if not flags.get('.'):
            # It would be much better to subclass sympy LaTeX printer
            latex = latex.replace('.', param['floating_point'])

    #TODO: subclass sympy LaTeX printer (cf. mathlib in wxgeometrie)
    latex = latex.replace(r'\operatorname{log}', r'\operatorname{ln}')
    return latex


global_context['latex'] = print_sympy_expr

if sympy is not None:
    sympy.Basic.__str__ = print_sympy_expr


latex_generator = LatexGenerator()




def make_file(syntax_tree, output_name, make_tex_file=False,
                 make_pdf_file=True, options=None):
    remove = getattr(options, 'remove', False)
    quiet = getattr(options, 'quiet', False)

    dir_name = os.path.split(output_name)[0]
    extra = (('-output-directory "%s"' % dir_name) if dir_name else '')
    try:
        latex_generator.parse_node(syntax_tree)
    except Exception:
        print('\n*** Error occured while parsing. ***')
        print('This is current parser state for debugging purpose:')
        print(80*'-')
        print('... ' + ''.join(latex_generator.context['LATEX'][-10:]))
        print(80*'-')
        print('')
        raise
    latex = latex_generator.read()

    def compile_latex_file(filename):
        if quiet:
            command = param['quiet_tex_command']
        else:
            command = param['tex_command']
        command += ' %s "%s"' % (extra, filename)
        log = execute(command)
        # Run command twice if references were found.
        if 'Rerun to get cross-references right.' in log:
            log = execute(command)

    if make_tex_file:
        with open(output_name + '.tex', 'w') as texfile:
            texfile.write(latex)
            if make_pdf_file:
                texfile.flush()
                compile_latex_file(texfile.name)
                if remove:
                    for extension in ('aux', 'log', 'out'):
                        name = '%s.%s' % (output_name, extension)
                        if os.path.isfile(name):
                            os.remove(name)
    else:
        try:
            texfile = tempfile.NamedTemporaryFile(suffix='.tex')
            texfile.write(latex)
            if make_pdf_file:
                tmp_name  = os.path.split(texfile.name)[1][:-4] # without .tex extension
                tmp_names = {}
                output_names = {}
                for extension in ('pdf', 'log', 'aux', 'out'):
                    tmp_names[extension] = '%s.%s' % (tmp_name, extension)
                    output_names[extension] = '%s.%s' % (output_name, extension)
                texfile.flush()
                compile_latex_file(texfile.name)
                os.rename(tmp_names['pdf'], output_names['pdf'])
                for extension in ('log', 'aux', 'out'):
                    if os.path.isfile(tmp_names[extension]):
                        if remove:
                            os.remove(tmp_names[extension])
                        else:
                            os.rename(tmp_names[extension], output_names[extension])
        finally:
            texfile.close()





if __name__ == '__main__':

    # Options parsing
    parser = optparse.OptionParser(prog = "Ptyx",
            usage = "usage: %prog [options] filename",
            version = "%prog " + __version__)
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
    parser.add_option("--reorder-pages",
            help = "Reorder pages for printing.\n\
            Currently, only 'brochure' and 'brochure-reversed' mode are supported.\
            The pdftk command must be installed.\
            Ex: ptyx --reorder-pages=brochure-reversed -f pdf myfile.ptyx.")
    parser.add_option("--names",
            help = "Name of a CSV file containing a column of names \
                   (and optionnaly a second column with fornames). \n \
                   The names will be used to generate the #NAME tag \
                   replacement value.\n \
                   Additionnaly, if `-n` option is not specified, \
                   default value will be the number of names in the CSV file.")

    # Limit seeds, to be able to retrieve seed manually if needed.
    seed_value = random.randint(0, 100000)
    random.seed(seed_value)

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
            print('Names extracted from CSV file:')
            print(names)
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

        with open(input_name, 'rU') as input_file:
            text = input_file.read()
        syntax_tree = latex_generator.parser.parse(text)

        filenames = []
        for num in xrange(start, start + total):
            latex_generator.clear()
            latex_generator.context['NUM'] = num
            if names:
                name = names[num]
                filename = '%s-%s' % (output_name, name)
            else:
                name = ''
                filename = ('%s-%s' % (output_name, num) if total > 1 else output_name)
            latex_generator.context['NAME'] = name
            #~ filename = filename.replace(' ', '\ ')
            filenames.append(filename)

            # Output is redirected to a .log file
            sys.stdout = sys.stderr = CustomOutput((filename + '-python.log')
                                                  if not options.remove else '')
            make_file(syntax_tree, filename, make_tex_file=make_tex, \
                        make_pdf_file=('pdf' in formats), options=options
                        )

        # Keep track of the seed used.
        if 'SEED' in latex_generator.context:
            seed_value = latex_generator.context['SEED']
        else:
            print(('Warning: #SEED not found, using default seed value %s.\n'
                               'A .seed file have been generated.') % seed_value)
        seed_file_name = os.path.join(os.path.dirname(output_name), '.seed')
        with open(seed_file_name, 'w') as seed_file:
            seed_file.write(str(seed_value))

        # Join different versions in a single pdf, and compress if asked to.
        if options.compress or (options.cat and total > 1):
            # pdftk and ghostscript must be installed.
            if not ('pdf' in formats):
                print("Warning: --cat or --compress option meaningless if pdf output isn't selected.")
            else:
                filenames = [filename + '.pdf' for filename in filenames]
                pdf_name = output_name + '.pdf'
                if total > 1:
                    files = ' '.join('"%s"' % filename for filename in filenames)
                    print('Pdftk output:')
                    print(execute('pdftk %s output "%s"' % (files, pdf_name)))
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
                    temp_dir = tempfile.mkdtemp()
                    pdf_with_seed = os.path.join(temp_dir, 'with_seed.pdf')
                    execute('pdftk "%s" attach_files "%s" output "%s"' % (pdf_name, seed_file_name, pdf_with_seed))
                    shutil.copyfile(pdf_with_seed, pdf_name)
        if options.reorder_pages:
            # Use pdftk to detect how many pages has the pdf document.
            n = int(execute('pdftk %s dump_data output | grep -i NumberOfPages:' % pdf_name).strip().split()[-1])
            mode = options.reorder_pages
            if mode == 'brochure':
                if n%4:
                    raise RuntimeError, ('Page number is %s, but must be a multiple of 4.' % n)
                order = []
                for i in range(int(n/4)):
                    order.extend([2*i + 1, 2*i + 2, n - 2*i - 1, n - 2*i])
            elif mode == 'brochure-reversed':
                if n%4:
                    raise RuntimeError, ('Page number is %s, but must be a multiple of 4.' % n)
                order = n*[0]
                for i in range(int(n/4)):
                    order[2*i] = 4*i + 1
                    order[2*i + 1] = 4*i + 2
                    order[n - 2*i - 2] = 4*i + 3
                    order[n - 2*i - 1] = 4*i + 4
            else:
                raise NameError, ('Unknown mode %s for option --reorder-pages !' % mode)
            # monfichier.pdf -> monfichier-brochure.pdf
            new_name = '%s-%s.pdf' % (pdf_name[:pdf_name.index('.')], mode)
            execute('pdftk %s cat %s output %s' % (pdf_name, ' '.join(str(i) for i in order), new_name))

