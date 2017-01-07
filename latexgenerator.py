from __future__ import division, unicode_literals, absolute_import, print_function

import re
from functools import partial
from os.path import dirname, basename, join #, realpath
import random
from importlib import import_module

from context import global_context, SympifyError
from config import param, sympy, wxgeometrie
import randfunc
from utilities import print_sympy_expr, find_closing_bracket, \
                      numbers_to_floats, _float_me_if_you_can, term_color

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


def wxgeometrie_needed(f):
    def g(*args, **kw):
        if not wxgeometrie:
            raise ImportError('Library wxgeometrie not found !')
        f(*args, **kw)
    return g



class Node(object):
    """A node.

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
        "Return argument number i content."
        child = self.children[i]
        if child.name != i:
            raise ValueError('Incorrect argument number.')
        children_number = len(child.children)
        if children_number > 1:
            raise ValueError("Don't use pTyX code inside %s argument number %s." % (self.name, i + 1))
        elif children_number == 0:
            if self.name is 'EVAL':
                # EVAL isn't a real tag name: if a variable `#myvar` is found
                # somewhere, it is parsed as an `#EVAL` tag with `myvar` as argument.
                # So, a lonely `#` is parsed as an `#EVAL` with no argument at all.
                raise ValueError("Error! There is a lonely '#' somewhere !")
            raise ValueError("%s argument number %s should not be empty !" % (self.name, i + 1))

        return child.children[0]


    def display(self, color=True, indent=0, raw=False):
        texts = ['%s+ Node %s' % (indent*' ', self._format(self.name, color))]
        for child in self.children:
            if isinstance(child, Node):
                texts.append(child.display(color, indent + 2, raw=raw))
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

    def _format(self, val, color):
        if not color:
            return str(val)
        if isinstance(val, str):
            return term_color(val, 'yellow')
        elif isinstance(val, int):
            return term_color(str(val), 'blue')
        return val






class SyntaxTreeGenerator(object):
    # For each tag, indicate:
    #   1. The number of interpreted arguments (arguments that contain code).
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

    tags = {'ANS':          (0, 0, ['@END']),
            'ANSWER':       (0, 1, None),
            'API_VERSION':  (0, 1, None),
            'ASK':          (0, 0, ['@END']),
            'ASK_ONLY':     (0, 0, ['@END']),
            'ASSERT':       (1, 0, None),
            'CALC':         (1, 0, None),
            # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
            'CASE':         (1, 0, ['CASE', 'ELSE', 'END']),
            'COMMENT':      (0, 0, ['@END']),
            # CONDITIONAL_BLOCK isn't a real tag, but is used to enclose
            # a #CASE{...}...#CASE{...}...#END block, or an #IF{...}...#ELIF{...}...#END block.
            'CONDITIONAL_BLOCK':    (0, 0, ['@END']),
            'DEBUG':        (0, 0, None),
            'EVAL':         (1, 0, None),
            # ENUM indicates the start of an enumeration.
            # It does nothing by itself, but is used by some extensions.
            'ENUM':         (0, 0, ['@END']),
            'GEO':          (0, 0, ['@END']),
            # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
            'IF':           (1, 0, ['ELIF', 'ELSE', 'END']),
            # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
            'ELIF':         (1, 0, ['ELIF', 'ELSE', 'END']),
            # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
            'ELSE':         (0, 0, ['END']),
            'END':          (0, 0, None),
            'IMPORT':       (1, 0, None),
            'LOAD':         (1, 0, None),
            'FREEZE_RANDOM_STATE': (0, 0, []),
            'GCALC':        (0, 0, ['@END']),
            'IFNUM':        (1, 1, None),
            'MACRO':        (0, 1, None),
            'NEW_MACRO':    (0, 1, ['@END']),
            'PICK':         (1, 0, None),
            'PYTHON':       (0, 0, ['@END']),
            'QUESTION':     (0, 1, None),
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
            '#':            (0, 0, None),
            }
    # Tags sorted by length (longer first).
    # This is used for matching tests.
    sorted_tags = sorted(tags, key=len,reverse=True)

    _found_tags = frozenset()


    def preparse(self, text):
        """Pre-parse pTyX code and generate a syntax tree.

        :param text: some pTyX code.
        :type text: string

        .. note:: To access generated syntax tree, use `.syntax_tree` attribute.
        """
        # Now, we will parse Ptyx code to generate a syntax tree.
        self._found_tags = set()
        self.syntax_tree = Node('ROOT')
        self._preparse(self.syntax_tree, text)
        self.syntax_tree.tags = self._found_tags
        return self.syntax_tree


    def _preparse(self, node, text):
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
                if text[position].isdigit() or text[position] == ' ':
                    # This not a tag: LaTeX uses #1, #2, #3 as \newcommand{} parameters.
                    # Pretend nothing happened.
                    update_last_position = False
                    continue
                else:
                    # This is not a known tag name.
                    # Default tag name is EVAL.
                    # Notably:
                    # - any variable (like #a)
                    # - any expression (like #{a+7})
                    # will result in an #EVAL tag.
                    tag = 'EVAL'

            # ------------------------
            # Deal with new found tag.
            # ------------------------
            # Syntax tree maintains a record of all tags found during parsing.
            # (This tags set can be later accessed through its .tags attribute.)
            self._found_tags.add(tag)

            # Add text found before this tag to the syntax tree.
            # --------------------------------------------------

            remove_trailing_newline = (self.tags[tag][2] is not None or tag == 'END')
            if remove_trailing_newline:
                # Remove new line and spaces *before* #IF, #ELSE, ... tags.
                # This is more convenient, since two successive \n
                # induce a new paragraph in LaTeX.
                # So, something like this
                #   [some text here]
                #   #IF{delta>0}
                #   [some text there]
                #   #END
                # would automatically result in two paragraphs else.
                i = max(text.rfind('\n', None, tag_position), 0)
                if text[i:tag_position].isspace():
                    node.add_child(text[last_position:i])
                else:
                    node.add_child(text[last_position:tag_position])
            else:
                node.add_child(text[last_position:tag_position])

            # Enclose "CASE ... CASE ... ELSE ... END" or "IF ... ELIF ... ELSE ... END"
            # inside a CONDITIONAL_BLOCK node.
            # --------------------------------------------------------------------------
            #
            # The most subtle part while parsing pTyX code is to distinguish
            # between "#CASE{0}...#CASE{1}...#ELSE...#END"
            # and "#CASE{0}...#END#CASE{1}...#ELSE...#END".
            # This distinction is important because, if NUM==0, the ELSE clause
            # must be executed in the 2nde version, but not in the 1st one.
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


            # Special case : don't pre-parse #PYTHON ... #END content.
            # ----------------------------------------------------
            if tag == 'PYTHON':
                end = text.index('#END', position)
                # Create and enter new node.
                node = node.add_child(Node(tag))
                # Some specific parsing is done however:
                # a line starting with `%` will be interpreted as a comment.
                # This makes code a bit more readable, since `%` is already used
                # for comments in LateX code.
                _text = text[position:end]
                _text = re.sub(r'^\s*%', '#', _text, flags=re.MULTILINE)
                node.add_child(_text)
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
                    self._preparse(arg, text[position:end])
                    position = new_pos

                #~ if remove_trailing_newline:
                    #~ # Remove new line and spaces *after* #IF, #ELSE, ... tags.
                    #~ # This is more convenient, since two successive \n
                    #~ # induce a new paragraph in LaTeX.
                    #~ # So, something like this
                    #~ #   [some text here]
                    #~ #   #IF{delta>0}
                    #~ #   #IF{a>0}
                    #~ #   [some text there]
                    #~ #   #END
                    #~ #   #END
                    #~ # would automatically result in two paragraphs else.
                    #~ try:
                        #~ i = text.index('\n', position) + 1
                        #~ if text[position:i].isspace():
                            #~ position = i
                    #~ except ValueError:
                        #~ pass

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
    """Convert text containing ptyx tags to plain LaTeX."""

    convert_tags = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '=': 'EQUAL', '?': 'SIGN', '#': 'SHARP'}

    re_varname = re.compile('[A-Za-z_][A-Za-z0-9_]*([[].+[]])?$')

    def __init__(self):
        self.clear()
        self._tags_defined_by_extensions = {}
        # This syntax tree generator will be used to scan code at runtime.
        self.preparser = SyntaxTreeGenerator()

    def clear(self):
        self.macros = {}
        self.context = global_context.copy()
        self.context['LATEX'] = []
        self.backups = []
        # When write() is called from inside a #PYTHON ... #END code block,
        # its argument may contain pTyX code needing parsing.
        self.context['write'] = partial(self.write, parse=True)
        # Internal flags
        self.flags = {}


    @property
    def NUM(self):
        return self.context['NUM']


    def parse_node(self, node):
        """Parse a node in a pTyX syntax tree.

        Return True if block content was recursively parsed, and False else.

        In particular, when parsing an IF block, True will be returned if and
        only if the block condition was satisfied.
        """
        tag = self.convert_tags.get(node.name, node.name)
        try:
            method = getattr(self, '_parse_%s_tag' % tag)
        except AttributeError:
            # Extensions can define their own tags.
            tags_dict = self._tags_defined_by_extensions
            if tag in tags_dict:
                return tags_dict[tag][0](self, node)
            print("Error: method '_parse_%s_tag' not found" % tag)
            raise
        return method(node)

    def _parse_children(self, children, function=None, **options):
        if function is not None:
            # Store generated text in a temporary location, instead of self.context['LATEX'].
            # Function `function` will then be applied to this text,
            # before text is appended to self.context['LATEX'].
            # Backups may need to be read when parsing #= special tag,
            # so store them in `self.backups`.
            self.backups.append(self.context['LATEX'])
            self.context['LATEX'] = []

        for child in children:
            if isinstance(child, str):
                self.write(child)
            else:
                # All remaining children should be nodes now.
                assert isinstance(child, Node)
                # Nodes are either numbered, or have a name.
                # Numbered nodes correspond to command arguments. Those should
                # have been processed before, and not be passed to _parse_children().
                assert isinstance(child.name, str)

                self.parse_node(child)

        if function is not None:
            code = function(''.join(self.context['LATEX']), **options)
            self.context['LATEX'] = self.backups.pop()
            self.write(code)


    def _parse_options(self, node):
        'Parse a tag options, following the syntax {key1=val1,...}.'
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
        """Append a piece of LaTeX text to context['LATEX'].

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
            self.parse_node(self.preparser.preparse(text))
        else:
            self.context['LATEX'].append(text)

    def read(self):
        return ''.join(self.context['LATEX'])

    def _parse_API_VERSION(self, node):
        def v(version):
            return version.split('.')
        version = v(node.children[0].children)
        from ptyx import __version__, __api__
        if v(__version__) < version:
            print("Warning: pTyX engine is too old (v%s required)." % version)
        if version < v(__api__):
            print("Warning: pTyX file uses an old API. You may have to update your pTyX file code before compiling it.")
        #TODO: display a short list of API changes which broke compatibility.
        self.context['API_VERSION'] = version

    def _parse_ASK_tag(self, node):
        self._parse_children(node.children, function=self.context.get('format_ask'))

    def _parse_ASK_ONLY_tag(self, node):
        if not self.context.get('WITH_ANSWERS'):
            self._parse_children(node.children,
                    function=self.context.get('format_ask_only'))
        else:
            print('Skipping ASK_ONLY section...')

    def _parse_ANS_tag(self, node):
        if self.context.get('WITH_ANSWERS'):
            self._parse_children(node.children,
                    function=self.context.get('format_ans'))

    def _parse_ANSWER_tag(self, node):
        if self.context.get('WITH_ANSWERS'):
            self._parse_children(node.children[0].children,
                    function=self.context.get('format_answer'))

    def _parse_QUESTION_tag(self, node):
        if not self.context.get('WITH_ANSWERS'):
            self._parse_children(node.children[0].children)

    def _parse_END_ANY_ASK_OR_ANS_tag(self, node):
        pass

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

    def _parse_IMPORT_tag(self, node):
        exec('from %s import *' % node.arg(0), self.context)

    def _parse_LOAD_tag(self, node):
        # LOAD tag is used to load extensions **before** syntax tree is built.
        pass

    def _parse_PYTHON_tag(self, node):
        assert len(node.children) == 1
        python_code = node.children[0]
        print("--------------------------------")
        print("Executing following python code:")
        print(python_code)
        print("--------------------------------")
        assert isinstance(python_code, str)
        self._exec_python_code(python_code, self.context)

    #Remove comments before generating tree ?
    def _parse_COMMENT_tag(self, node):
        pass

    @wxgeometrie_needed
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
            print("Error in assertion (NUM=%s):" % self.NUM)
            print("***")
            print(code)
            print("***")
            assert test

    def _parse_EVAL_tag(self, node):
        args, kw = self._parse_options(node)
        if self.context.get('ALL_FLOATS'):
            self.flags['floats'] = True
        for arg in args:
            if arg.isdigit():
                self.flags['round'] = int(arg)
            elif arg == '.':
                self.flags['.'] = True
            elif arg in ('floats', 'float'):
                self.flags['floats'] = True

            elif arg == 'str':
                self.flags['str'] = True
            else:
                raise ValueError('Unknown flag: ' + repr(arg))
        # XXX: support options round, float, (sympy, python,) pick and rand
        code = node.arg(0)
        assert isinstance(code, str), type(code)
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
            raise NameError('Error: MACRO "%s" undefined.' % name)
        self._parse_children(self.macros[name])

    def _parse_ENUM_tag(self, node):
        # This tag does nothing by itself, but is used by some extensions.
        self._parse_children(node.children)

    def _parse_SHUFFLE_tag(self, node):
        # Shuffles all the #ITEM sections inside a #SHUFFLE block.
        # Note that they may be some text or nodes before first #ITEM,
        # if so they should be left unmodified at first position.
        if node.children:
            for i, child in enumerate(node.children):
                if isinstance(child, Node) and child.name == 'ITEM':
                    break
            items = node.children[i:]
            assert all(isinstance(item, Node) and item.name == 'ITEM' for item in items)
            randfunc.shuffle(items)
            self._parse_children(node.children[:i] + items)
            #~ print('\n------------')
            #~ print('SHUFFLE: %s elements, excluding first %s.' % len(children), i)
            #~ print('state hash is %s' % hash(random.getstate()))
            #~ print('------------\n')

    def _parse_ITEM_tag(self, node):
        self._parse_children(node.children)

    def _parse_SEED_tag(self, node):
        # SEED tag is managed independently (it avoids user including it inadvertently inside
        # a conditional block or a #ASK_ONLY/#END block, which may result in an (apparently)
        # very strange behaviour of compiler !)
        pass

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

    @wxgeometrie_needed
    def _parse_TABVAL_tag(self, node):
        from wxgeometrie.modules.tablatex import tabval
        args, kw = self._parse_options(node)
        for key in kw:
            kw[key] = eval(kw[key])
        self._parse_children(node.children, function=tabval, **kw)

    @wxgeometrie_needed
    def _parse_TABVAR_tag(self, node):
        from wxgeometrie.modules.tablatex import tabvar
        state = random.getstate()
        args, kw = self._parse_options(node)
        for key in kw:
            kw[key] = eval(kw[key])
        self._parse_children(node.children, function=tabvar, **kw)
        random.setstate(state)

    @wxgeometrie_needed
    def _parse_TABSIGN_tag(self, node):
        from wxgeometrie.modules.tablatex import tabsign
        state = random.getstate()
        args, kw = self._parse_options(node)
        for key in kw:
            kw[key] = eval(kw[key])
        self._parse_children(node.children, function=tabsign, **kw)
        random.setstate(state)

    @wxgeometrie_needed
    def _parse_GCALC_tag(self, node):
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

    def _parse_SHARP_tag(self, node):
        # 2 sharps ## -> 1 sharp #
        self.write('#')

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

    @wxgeometrie_needed
    def _parse_GEO_tag(self, node):
        from wxgeometrie.geolib import Feuille
        state = random.getstate()
        args, kw = self._parse_options(node)
        scale = kw.pop('scale', None)
        for key in kw:
            kw[key] = eval(kw[key])
        def _eval2latex(code):
            print('code::' + repr(code))
            feuille = Feuille(**kw)
            for commande in code.split('\n'):
                feuille.executer(commande)
            return feuille.exporter('tikz', echelle=scale)
        self._parse_children(node.children, function=_eval2latex, **kw)
        random.setstate(state)

    def _parse_DEBUG_tag(self, node):
        while True:
            msg = 'Debug point. Enter command, or quit (q! + ENTER):'
            sep = len(msg)*"="
            print(sep)
            print(msg)
            print(sep)
            command = input('[In]: ')
            print('[Out]: ')
            if command == 'q!':
                break
            else:
                try:
                    exec(command)
                except Exception as e:
                    print('*** ERROR ***')
                    print(e)


    def _exec(self, code, context):
        """exec is encapsulated in this function so as to avoid problems
        with free variables in nested functions."""
        try:
            exec(code, context)
        except:
            print("** ERROR found in the following code: **")
            print(code)
            print("-----")
            print(repr(code))
            print("-----")
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
            raise ImportError('sympy library not found.')

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
                if isinstance(result, str):
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
        context['LAST'] = result
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
            return latex.lstrip().startswith('-')

        if flags.get('+'):
            if result == 0:
                latex = ''
            elif not neg(latex):
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
            for textlist in self.backups + [context['LATEX']]:
                for i, elt in enumerate(reversed(textlist)):
                    if elt == '#=':
                        textlist[len(textlist) - i - 1] = symb
                        return latex
            print("Debug warning: `#=` couldn't be found when scanning context !")
            print("There is most probably a bug in pTyX, entering debuging...")
            self._parse_DEBUG_tag(None)
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
                print("** ERROR while rounding value: **")
                print(result)
                print("-----")
                print(''.join(self.context['LATEX'])[-100:])
                print("-----")
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


class Compiler(object):
    def __init__(self):
        self.syntax_tree_generator = SyntaxTreeGenerator()
        self.latex_generator = LatexGenerator()
        self.state = {}

    def read_file(self, path):
        "Set the path of the file to be compiled."
        self.state['path'] = path
        with open(path, 'rU') as input_file:
            raw_text = self.state['raw_text'] = input_file.read()
        return raw_text

    def call_extensions(self, code=None):
        # First, we search if some extensions must be load.
        # This must be done at the very begining, since extensions may
        # define their own specialized language, to be converted to
        # valid pTyX code (and then to LaTeX).
        if code is not None:
            self.state['raw_text'] = code
        else:
            code = self.state['raw_text']
        names = []
        pos = 0
        while True:
            i = code.find("#LOAD{", pos)
            if i == -1:
                break
            pos = code.find('}', i)
            if pos == -1:
                raise RuntimeError("#LOAD tag has no closing bracket !")
            names.append(code[i + 6:pos])
        extensions = {}
        for name in names:
            extensions[name] = import_module('extensions.%s' % name)
            # execute `main()` function of extension.
            code = extensions[name].main(code, self)
        if extensions:
            # Save pTyX code generated by extensions (this is used for debuging,
            # but if needed extensions can also save some data this way using #COMMENT tag).
            # If input file was /path/to/file/myfile.ptyx,
            # plain pTyX code is saved in /path/to/file/.myfile.ptyx.plain-ptyx
            path = self.state['path']
            filename = join(dirname(path), '.%s.plain-ptyx' % basename(path))
            with open(filename, 'w') as f:
                f.write(code)
        self.state['extensions_loaded'] = extensions
        self.state['plain_ptyx_code'] = code
        return code

    def read_seed(self, code=None):
        if code is not None:
            self.state['raw_text'] = code
        else:
            code = self.state['raw_text']
        pos = 0
        while True:
            i = code.find("#SEED{", pos)
            if i == -1:
                break
            pos = code.find('}', i)
            if pos == -1:
                raise RuntimeError("#SEED tag has no closing bracket !")
            value = int(code[i + 6:pos].strip())
        else:
            print('Warning: #SEED not found, using hash of ptyx file path (if any) as seed.')
            value = hash(self.state.get('path'))
        self.state['seed'] = value
        return value

    def generate_syntax_tree(self, code=None):
        if code is not None:
            self.state['plain_ptyx_code'] = code
        else:
            code = self.state['plain_ptyx_code']
        tree = self.state['syntax_tree'] = self.syntax_tree_generator.preparse(code)
        return tree

    def generate_latex(self, tree=None, **context):
        if tree is not None:
            self.state['syntax_tree'] = tree
        else:
            tree = self.state['syntax_tree']
        gen = self.latex_generator
        gen.clear()
        gen.context.update(context)
        randfunc.set_seed(self.state['seed'] + gen.context['NUM'])
        try:
            gen.parse_node(tree)
        except Exception:
            print('\n*** Error occured while parsing. ***')
            print('This is current parser state for debugging purpose:')
            print(80*'-')
            print('... ' + ''.join(gen.context['LATEX'][-10:]))
            print(80*'-')
            print('')
            raise
        self.latex = gen.read()
        if 'API_VERSION' not in gen.context:
            print('Warning: no API version specified. This may be an old pTyX file.')
        return self.latex

    def close(self):
        for name, module in self.state['extensions_loaded'].items():
            if hasattr(module, 'close'):
                module.close(self)

    def add_new_tag(self, name, syntax, handler, extension_name, update=True):
        """Add abbility for extensions to extend syntax, adding new tags.

        Using `extension_name`, the compiler also checks that two different
        extensions loaded simultaneously do not define define the same tag.
        * if tag is already define by the same extension, nothing is done.
        * if it is defined by an other extension, an error is raised.
        """
        tags_dict = self.latex_generator._tags_defined_by_extensions
        if name in tags_dict:
            if tags_dict[name][1] == extension_name:
                print(("Warning: Tag %s already defined by same extension (%s),"
                       " doing nothing.") % (name, extension_name))
                return
            else:
                raise NameError(("Extension %s tries to define tag %s, which was"
                                 "already defined by extension %s.")
                                 % (extension_name, name, tags_dict[name][1]))
        tags_dict[name] = (handler, extension_name)
        stg = self.syntax_tree_generator
        stg.tags[name] = syntax
        if update:
            stg.sorted_tags = sorted(stg.tags, key=len,reverse=True)

    def parse(self, code, **context):
        """Convert ptyx code to plain LaTeX in one shot.

        :param text: a pTyX file content, to be converted to plain LaTeX.
        :type text: str

        This is mainly used fo testing.
        """
        self.call_extensions(code)
        self.generate_syntax_tree()
        self.read_seed(code)
        latex = self.generate_latex(**context)
        self.close()
        return latex



compiler = Compiler()

parse = compiler.parse

