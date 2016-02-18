#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
from __future__ import division # 1/2 == .5 (par defaut, 1/2 == 0)


# --------------------------------------
#                  PTYX
#              main script
# --------------------------------------
#    PTYX
#    Python LaTeX preprocessor
#    Copyright (C) 2009-2016  Nicolas Pourcelot
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


__version__ = "3.0"
__release_date__ = (16, 2, 2016)



import optparse, re, random, os, tempfile, sys, codecs, csv, shutil
from math import ceil, floor, isnan, isinf
from os.path import realpath, join, dirname
import sys

from config import param, sympy, numpy, custom_latex
import randfunc
import utilities
from compilation import join_files, make_files
from latexgenerator import LatexGenerator, SyntaxTreeGenerator, latex_generator
from context import global_context

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('cp850')(sys.stdout)
else:
    sys.stdout = codecs.getwriter('utf8')(sys.stdout)



def pth(path):
        path = os.path.expanduser(path)
        path = os.path.normpath(path)
        return os.path.realpath(path)


#~ def is_negative_number(value):
    #~ is_python_num = isinstance(value, (float, int, long))
    #~ is_sympy_num = sympy and isinstance(value, sympy.Basic) and value.is_number
    #~ return (is_sympy_num or is_python_num) and value < 0




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
global_context['float'] = float
global_context['int'] = int
global_context['str'] = str

global_context['randpoint'] = randfunc.randpoint
global_context['srandpoint'] = randfunc.srandpoint
global_context['randint'] = randfunc.randint
global_context['randbool'] = randfunc.randbool
global_context['randsignint'] = randfunc.srandint
global_context['srandint'] = randfunc.srandint
global_context['randsign'] = randfunc.randsign
global_context['randfrac'] = randfunc.randfrac
global_context['srandfrac'] = randfunc.srandfrac
global_context['randchoice'] = randfunc.randchoice
global_context['srandchoice'] = randfunc.srandchoice
# If a document is compiled several times (to produce different versions of the same document),
# NUM is the compilation number (starting from 0).
global_context['NUM'] = 0





global_context['latex'] = utilities.print_sympy_expr

#if sympy is not None:
#    sympy.Basic.__str__ = print_sympy_expr








class EnumNode(object):
    def __init__(self, node_type=''):
        self.items = []
        self.node_type = node_type
        self.options = []

    def __repr__(self):
        return '<Node %s : %s item(s)>' % (self.node_type, len(self.items))


def enumerate_shuffle_tree(text, start=0):
    tags = (r'\begin{enumerate}', r'\end{enumerate}', r'\begin{itemize}', r'\end{itemize}', r'\item')
    tree = []
    stack = [tree]
    pos = 0
    tag = ''

    def find(s, tags, pos=0):
        results = ((s.find(tag, pos), tag) for tag in tags)
        try:
            return min((pos, tag) for (pos, tag) in results if pos != -1)
        except ValueError:
            return (None, None)

    while tag is not None:
        tag_pos, tag = find(text, tags, pos)

        if not stack:
            #TODO: print line number.
            raise RuntimeError(r'There is more \end{enumerate} (or itemize) than \begin{enumerate} !')

        stack[-1].append(text[pos:tag_pos])

        if tag is not None:
            pos = tag_pos + len(tag)

            if tag.startswith(r'\begin'):
                # node_type: enumerate or itemize
                node = EnumNode(tag[7:-1])
                m = re.match(r'\s*\[([^]]+)\]', text[pos:])
                if m is not None:
                    pos += len(m.group())
                    node.options = [s.strip() for s in m.groups()[0].split(',')]
                stack[-1].append(node)
                stack.append(node.items)
            elif tag == r'\item':
                node = EnumNode('item')
                # If it's not the first item of the enumeration,
                # close last item block.
                if getattr(stack[-2][-1], 'node_type', None) == 'item':
                    del stack[-1]
                stack[-1].append(node)
                stack.append(node.items)
            else:
                # Close enumeration block.
                del stack[-2:]

    if stack[-1] is not tree:
        #TODO: print line number.
        raise RuntimeError(r'Warning: Some \begin{enumerate} or \begin{itemize} was never closed !')

    return tree


def display_enumerate_tree(tree, color=True, indent=0, raw=False):
    "Return enumerate tree in a human readable form for debugging purpose."

    def blue(s):
        return '\033[0;36m' + s + '\033[0m'

    #~ def blue2(self, s):
        #~ return '\033[1;36m' + s + '\033[0m'
#~
    #~ def red(self, s):
        #~ return '\033[0;31m' + s + '\033[0m'
#~
    def green(s):
        return '\033[0;32m' + s + '\033[0m'
#~
    #~ def green2(self, s):
        #~ return '\033[1;32m' + s + '\033[0m'
#~
    def yellow(s):
        return '\033[0;33m' + s + '\033[0m'

    texts = []
    for child in tree:
        if isinstance(child, EnumNode):
            node_name = "Node " + child.node_type
            if color:
                node_name = yellow(node_name)
            texts.append('%s  + %s [%s]' % (indent*' ', node_name, ",".join(child.options)))
            texts.append(display_enumerate_tree(child.items, color, indent + 2, raw=raw))
        else:
            if raw:
                text = repr(child)
            else:
                lines = child.split('\n')
                text = lines[0]
                if len(lines) > 1:
                    text += ' [...]'
                text = repr(text)
            if color:
                text = green(text)
            texts.append('%s  - text: %s' % (indent*' ', text))
    return '\n'.join(texts)



def tree2strlist(tree, shuffle=False, answer=False):
    str_list = []
    for item in tree:
        if isinstance(item, str):
            if answer:
                # '====' or any longer repetition of '=' begins an answer.
                i = item.find('====')
                if i != -1:
                    j = i + 1
                    n = len(item)
                    while j < n and item[j] == '=':
                        j += 1
                    item = item[:i] + '#ANS{}' + item[j:]
            str_list.append(item)
        else:
            if item.node_type == 'item':
                if shuffle:
                    str_list.append('#ITEM')
                str_list.append(r'\item')
                if answer:
                    str_list.append('#ASK')
                str_list.extend(tree2strlist(item.items, answer=answer))
                if answer:
                    str_list.append('#END')
            else:
                _shuffle_ = _answer_ = False
                if '_shuffle_' in item.options:
                    item.options.remove('_shuffle_')
                    _shuffle_ = True
                if '_answer_' in item.options:
                    item.options.remove('_answer_')
                    _answer_ = True
                str_list.append(r'\begin{%s}' % item.node_type)
                if item.options:
                    str_list.append('[%s]' % ','.join(item.options))
                if _shuffle_:
                    str_list.append('#SHUFFLE')
                str_list.extend(tree2strlist(item.items, shuffle=_shuffle_, answer=_answer_))
                if _shuffle_:
                    str_list.append('#END')
                str_list.append(r'\end{%s}' % item.node_type)
    return str_list




if __name__ == '__main__':

    print('Ptyx ' + __version__ + ' ' + '/'.join(str(d) for d in __release_date__))

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
    parser.add_option("-m", "--make-directory", action = "store_true",
            help = "Create a new directory to store all generated files.")
    parser.add_option("-a", "--auto-make-dir", action = "store_true",
            help = "Switch to --make-directory mode, except if .ptyx file \
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
    parser.add_option("--generate-batch-for-windows-printing", action = "store_true",
            help = "Generate a batch file for printing all pdf files using SumatraPDF.")

    # First, parse all arguments (filenames, options...)
    # --------------------------------------------------

    # Limit seeds, to be able to retrieve seed manually if needed.
    seed_value = random.randint(0, 100000)
    random.seed(seed_value)

    options, args = parser.parse_args()

    options.remove = options.remove or options.remove_all

    formats = options.format.split('+') if options.format else param['format']
    if options.debug:
        param['debug'] = True

    start = int(options.start)

    total = options.number

    if options.names:
        with open(pth(options.names)) as f:
            names = [' '.join(l) for l in csv.reader(f)]
            print('Names extracted from CSV file:')
            print(names)
        total = (int(total) if total else len(names))
    else:
        total = (int(total) if total else param['total'])
        names = []

    global_context['TOTAL'] = options.number = total

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

    # Time to act ! Let's compile all ptyx files...
    # ---------------------------------------------

    for input_name in arguments:
        input_name = pth(input_name)

        # Generate syntax tree
        with open(input_name, 'rU') as input_file:
            text = input_file.read()
        # Preparse text (option _shuffle_ in enumerate/itemize)
        if '_shuffle_' in text or '_answer_' in text:
            text = ''.join(tree2strlist(enumerate_shuffle_tree(text)))
            tmp_file_name = os.path.join(os.path.dirname(input_name), '.ptyx.tmp')
            with open(tmp_file_name, 'w') as tmp_ptyx_file:
                tmp_ptyx_file.write(text)
        syntax_tree = latex_generator.preparser.preparse(text)

        # Compile and generate output files (tex or pdf)
        filenames, output_name = make_files(input_name, syntax_tree, options, start, names, make_tex, formats)

        # Keep track of the seed used.
        if 'SEED' in latex_generator.context:
            seed_value = latex_generator.context['SEED']
        else:
            print(('Warning: #SEED not found, using default seed value %s.\n'
                               'A .seed file have been generated.') % seed_value)
        seed_file_name = os.path.join(os.path.dirname(output_name), '.seed')
        with open(seed_file_name, 'w') as seed_file:
            seed_file.write(str(seed_value))

        if options.generate_batch_for_windows_printing:
            bat_file_name = os.path.join(os.path.dirname(output_name), 'print.bat')
            with open(bat_file_name, 'w') as bat_file:
                bat_file.write(param['win_print_command'] + ' '.join('%s.pdf'
                                      % os.path.basename(f) for f in filenames))

        # Join different versions in a single pdf, and compress if asked to.
        join_files(output_name, filenames, formats, options)

        # Do the same for the version with the answers.

        if 'ANS' in syntax_tree.tags or 'ANSWER' in syntax_tree.tags:
            filenames, output_name = make_files(input_name, syntax_tree, options, start, names, make_tex, formats, correction=True)

            # Join different versions in a single pdf, and compress if asked to.
            join_files(output_name, filenames, formats, options)

            if options.generate_batch_for_windows_printing:
                bat_file_name = os.path.join(os.path.dirname(output_name), 'print_corr.bat')
                with open(bat_file_name, 'w') as bat_file:
                    bat_file.write(param['win_print_command'] + ' '.join('%s.pdf'
                                        % os.path.basename(f) for f in filenames))
