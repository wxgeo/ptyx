#!/usr/bin/env python3

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

from __future__ import division, unicode_literals, absolute_import, print_function

__version__ = "4.2"
# API version number changes only when backward compatibility is broken.
__api__ = "4.2"
__release_date__ = (14, 12, 2016)



import argparse, re, random, os, sys, codecs, csv, math
#from math import ceil, floor, isnan, isinf


from config import param, sympy, numpy#, custom_latex
import randfunc
from utilities import print_sympy_expr, term_color
from compilation import join_files, make_files
from latexgenerator import compiler
from context import global_context

if sys.version_info.major == 2:
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
global_context['ceil'] = (global_context['ceiling'] if sympy is not None else math.ceil)
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
global_context['randfloat'] = randfunc.randfloat
global_context['srandfloat'] = randfunc.srandfloat
global_context['randchoice'] = randfunc.randchoice
global_context['srandchoice'] = randfunc.srandchoice
global_context['randpop'] = randfunc.randpop
global_context['shuffle'] = randfunc.shuffle
global_context['many'] = randfunc.many
global_context['distinct'] = randfunc.distinct
global_context['_print_state'] = randfunc._print_state
# If a document is compiled several times (to produce different versions of the same document),
# NUM is the compilation number (starting from 0).
global_context['NUM'] = 0
global_context['latex'] = print_sympy_expr

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

    texts = []
    for child in tree:
        if isinstance(child, EnumNode):
            node_name = "Node " + child.node_type
            if color:
                node_name = term_color(node_name, 'yellow')
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
                text = term_color(text, 'green')
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
    #~ print('Ptyx ' + __version__ + ' ' + '/'.join(str(d) for d in __release_date__))

    # Options parsing
    parser = argparse.ArgumentParser(prog='pTyX',
            description='Compile .ptyx files into .tex or .pdf files.',
            usage="usage: %(prog)s [options] filename")

    parser.add_argument("filenames", nargs='+')

    parser.add_argument("-n", "--number", type=int,
            help="Number of pdf files to generate. Default is %s.\n \
                   Ex: ptyx -n 5 my_file.ptyx" % param['total']
                   )
    parser.add_argument("-f", "--formats", default='+'.join(param['formats']),
            choices=['pdf', 'tex', 'pdf+tex', 'tex+pdf'],
            help="Output format. Default is %(default)s.\n"
                   "Ex: ptyx -f tex my_file.ptyx"
                   )
    parser.add_argument("-r", "--remove", action="store_true",
            help="Remove any generated .log and .aux file after compilation.\n \
                    Note that references in LaTeX code could be lost."
                    )
    parser.add_argument("-R", "--remove-all", action="store_true",
            help="Remove any generated .log and .aux file after compilation.\n \
                    If --cat option or --compress option is used, remove also \
                    all pdf files, except for the concatenated one."
                    )
    parser.add_argument("-m", "--make-directory", action="store_true",
            help="Create a new directory to store all generated files."
                    )
    parser.add_argument("-a", "--auto-make-dir", action="store_true",
            help="Switch to --make-directory mode, except if .ptyx file \
                   is already in a directory with the same name \
                   (e.g. myfile123/myfile123.ptyx)."
                   )
    parser.add_argument("-b", "--debug", action="store_true",
            help="Debug mode."
                    )
    parser.add_argument("-q", "--quiet", action="store_true",
            help="Suppress most of latex processor output."
                    )
    parser.add_argument("-s", "--start", default=1, type=int,
            help="Number of the first generated file \
                   (initial value of internal NUM counter). Default is %(default)s."
                   )
    parser.add_argument("-c", "--cat", action="store_true",
            help="Cat all generated pdf files inside a single one. \
                   The pdftk command must be installed."
                   )
    parser.add_argument("-C", "--compress", action="store_true",
            help="Like --cat, but compress final pdf file using pdf2ps and ps2pdf."
                    )
    parser.add_argument("--reorder-pages", choices=['brochure', 'brochure-reversed'],
            help="Reorder pages for printing.\n\
            Currently, only 'brochure' and 'brochure-reversed' mode are supported.\
            The pdftk command must be installed.\n\
            Ex: ptyx --reorder-pages=brochure-reversed -f pdf myfile.ptyx."
            )
    parser.add_argument("--names", metavar='CSV_FILE',
            help="Name of a CSV file containing a column of names \
                   (and optionnaly a second column with fornames). \n \
                   The names will be used to generate the #NAME tag \
                   replacement value.\n \
                   Additionnaly, if `-n` option is not specified, \
                   default value will be the number of names in the CSV file."
                   )
    parser.add_argument("--generate-batch-for-windows-printing", action="store_true",
            help="Generate a batch file for printing all pdf files using SumatraPDF."
            )
    parser.add_argument("--context", default='',
            help="Manually customize context (ie. internal namespace).\n \
                   Ex: ptyx --context \"a = 3; b = 2; t = 'hello'\""
                   )
    parser.add_argument("--version", action='version', version='%(prog)s ' +
                        '%s (%s/%s/%s)' % ((__version__,) + __release_date__))

    options = parser.parse_args()


    # First, parse all arguments (filenames, options...)
    # --------------------------------------------------

    if options.remove_all:
        options.remove = True

    options.formats = options.formats.split('+')

    if options.compress or options.cat:
        # pdftk and ghostscript must be installed.
        if 'pdf' not in options.formats:
            raise RuntimeError("--cat or --compress option invalid unless pdf output is selected.")

    if options.debug:
        param['debug'] = True

    if options.names:
        with open(pth(options.names)) as f:
            options.names = [' '.join(l) for l in csv.reader(f)]
            print('Names extracted from CSV file:')
            print(options.names)
    else:
        options.names = []

    if options.number is None:
        options.number = len(options.names) or param['total']

    ctxt = options.context
    options.context = {}
    for keyval in ctxt.split(';'):
        if keyval.strip():
            key, val = keyval.split('=')
            # TODO:
            # - test if key is a valid variable name.
            # - replace eval() by (basic) type detection and appropriate conversion (using int(), float(), etc.)
            options.context[key.strip()] = eval(val)


    # Time to act ! Let's compile all ptyx files...
    # ---------------------------------------------

    for input_name in options.filenames:
        # Read pTyX file.
        input_name = pth(input_name)
        compiler.read_file(input_name)
        compiler.call_extensions()

        # Preparse text (option _shuffle_ in enumerate/itemize)
        # This is mainly for compatibility with old versions, extensions should
        # be used instead now (extensions are handled directly by SyntaxTreeGenerator).
        text = compiler.state['plain_ptyx_code']
        if '_shuffle_' in text or '_answer_' in text:
            print("Warning: deprecated option _shuffle_ or _answer__ is used !")
            text = ''.join(tree2strlist(enumerate_shuffle_tree(text)))
            tmp_file_name = os.path.join(os.path.dirname(input_name), '.ptyx.tmp')
            with open(tmp_file_name, 'w') as tmp_ptyx_file:
                tmp_ptyx_file.write(text)
            compiler.state['plain_ptyx_code'] = text

        # Generate syntax tree
        compiler.generate_syntax_tree()

        # Read seed used for random numbers generation.
        seed_value = compiler.read_seed()
        # Compile and generate output files (tex or pdf)
        filenames, output_name = make_files(input_name, **vars(options))

        # Keep track of the seed used.
        seed_value = compiler.state['seed']
        seed_file_name = os.path.join(os.path.dirname(output_name), '.seed')
        with open(seed_file_name, 'w') as seed_file:
            seed_file.write(str(seed_value))

        if options.generate_batch_for_windows_printing:
            bat_file_name = os.path.join(os.path.dirname(output_name), 'print.bat')
            with open(bat_file_name, 'w') as bat_file:
                bat_file.write(param['win_print_command'] + ' '.join('%s.pdf'
                                      % os.path.basename(f) for f in filenames))

        # Join different versions in a single pdf, and compress if asked to.
        opt = dict(vars(options))
        opt['filenames'] = filenames
        #opt['seed_file_name'] = seed_file_name
        join_files(output_name, **opt)

        # Do the same for the version with the answers.

        tags = compiler.state['syntax_tree'].tags
        if 'ANS' in tags or 'ANSWER' in tags:
            filenames, output_name = make_files(input_name, correction=True, **vars(options))

            # Join different versions in a single pdf, and compress if asked to.
            opt['filenames'] = filenames
            join_files(output_name, **opt)

            if options.generate_batch_for_windows_printing:
                bat_file_name = os.path.join(os.path.dirname(output_name), 'print_corr.bat')
                with open(bat_file_name, 'w') as bat_file:
                    bat_file.write(param['win_print_command'] + ' '.join('%s.pdf'
                                        % os.path.basename(f) for f in filenames))
        compiler.close()


