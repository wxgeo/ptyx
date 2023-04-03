import random
import re
import traceback
from importlib import import_module, metadata
from os.path import dirname, basename, join
from pathlib import Path
from types import ModuleType
from typing import Optional, Union, Callable, Iterable, Dict, Tuple, List, TypedDict

import ptyx.randfunc as randfunc
from ptyx import __version__, __api__
from ptyx.config import param, SYMPY_AVAILABLE
from ptyx.context import GLOBAL_CONTEXT

# from ptyx.printers import sympy2latex
from ptyx.syntax_tree import Node, SyntaxTreeGenerator, Tag, TagSyntax
from ptyx.utilities import advanced_split, numbers_to_floats, _float_me_if_you_can, latex_verbatim


class State(TypedDict, total=False):
    syntax_tree: Node
    seed: Optional[int]
    input: str
    path: Optional[Path]
    loaded_extensions: dict[str, ModuleType]
    plain_ptyx_code: str
    after_include: Optional[str]


# =============================================================================
# #ASSERT{}
# #CASE{int}...#CASE{int}...#END
# #COMMENT...#END
# #DEBUG
# #IF{bool}...#ELIF{bool}...#ELSE...#END
# #IFNUM{int}{...}
# #MACRO{name}
# #NEW_MACRO{name}...#END
# #PICK[option,int]{list}
# #PYTHON...#END
# #RAND[option,int]{list}
# #SEED{int}
# #SHUFFLE #ITEM...#ITEM...#END
# #SIGN
# #SYMPY...#END
# #TEST{bool}{...}{...}
# #+, #-,  #*, #=, #? (special operators)
# #varname or #[option,int]varname
# ## options : sympy, python, float
# ## int : round
#
# =============================================================================


# noinspection PyPep8Naming,PyMethodMayBeStatic
class LatexGenerator:
    """Convert text containing ptyx tags to plain LaTeX."""

    convert_tags = {
        "+": "ADD",
        "-": "SUB",
        "*": "MUL",
        "=": "EQUAL",
        "?": "SIGN",
        "#": "SHARP",
    }

    # noinspection RegExpRedundantEscape
    re_varname = re.compile(r"[A-Za-z_]\w*(\[.+\])?$")

    def __init__(self, compiler=None):
        self.clear()
        # Some pTyX code may be generated dynamically inside a #PYTHON code
        # block for example. So, LatexGenerator need his own STG (Syntax Tree Generator)
        # to be able to scan code at runtime.
        # (Every run implies generating a syntax tree again for each
        # of these pieces of embedded pTyX code.)
        self.parser = SyntaxTreeGenerator()
        # Access to compiler is needed by some extensions.
        self.compiler = compiler
        # Add ability to share values between compilations (needed by some
        # extensions).
        self.cache = {}

    def clear(self):
        self.macros = {}
        self.context = GLOBAL_CONTEXT.copy()
        self.context["PTYX_LATEX"] = []
        self.backups = []
        # When write() is called from inside a #PYTHON ... #END code block,
        # its argument may contain pTyX code needing parsing.
        # Write argument used to be parsed by default, but this was rarely needed
        # and led to very surprising behaviour sometimes from user perspective.
        # Now, one should use write(..., parse=True) if needed, which is much saner.
        self.context["write"] = self.write
        # Internal flags
        self.flags = {}

    def reset(self):
        """To overwrite."""
        self.clear()

    def set_new_context(self, context: Optional[Dict] = None):
        """Set a new context of evaluation for code, except for PTYX_LATEX value."""
        if context is None:
            context = GLOBAL_CONTEXT
        # Use deepcopy instead ?
        context = context.copy()
        # Copy internal parameters to new context.
        for key in self.context:
            if key.startswith("PTYX_"):
                context[key] = self.context[key]
        self.context = context

    @property
    def NUM(self):
        return self.context["PTYX_NUM"]

    @property
    def WITH_ANSWERS(self):
        return self.context.get("PTYX_WITH_ANSWERS")

    def _open_temp_context(self):
        # Store generated text in a temporary location, instead of self.context['LATEX'].
        # Function `function` will then be applied to this text,
        # before text is appended to self.context['LATEX'].
        # Backups may need to be read when parsing #= special tag,
        # so store them in `self.backups`.
        self.backups.append(self.context["PTYX_LATEX"])
        self.context["PTYX_LATEX"] = []

    def _apply_func_and_close_temp_context(self, function, **options):
        code = "".join(self.context["PTYX_LATEX"])
        if callable(function):
            function = [function]
        for f in function:
            code = f(code, **options)
        self.context["PTYX_LATEX"] = self.backups.pop()
        self.write(code)

    def parse_node(
        self,
        node: Node,
        function: Optional[Union[Callable, Iterable[Callable]]] = None,
        **options,
    ):
        """Parse a node in a pTyX syntax tree.

        Return True if block content was recursively parsed, and False else.

        In particular, when parsing an IF block, True will be returned if and
        only if the block condition was satisfied.
        """
        if function is not None:
            self._open_temp_context()
        name = node.name
        assert isinstance(name, str), repr(node)
        tag = self.convert_tags.get(name, name)
        try:
            method = getattr(self, f"_parse_{tag}_tag")
            return method(node)
        except AttributeError:
            print(f"Error: method '_parse_{tag}_tag' not found.")
            raise
        except Exception:
            print(f"Error when calling method '_parse_{tag}_tag'.")
            raise
        finally:
            if function is not None:
                self._apply_func_and_close_temp_context(function, **options)

    def _parse_children(
        self,
        children: Iterable[Union[str, Node]],
        function: Optional[Union[Callable, Iterable[Callable]]] = None,
        **options,
    ):
        """Parse all children nodes.

        Resulting LaTeX code will be appended to `self.context['PTYX_LATEX']`.

        If `function` is not None, apply `function` to resulting LaTeX
        code before appending it to `self.context['PTYX_LATEX']`.
        (So, `function` signature must be: function(str, **options) -> str).

        Note that `function` can also be a list of functions.
        In that case, the first function of the list is also the first
        to be applied.
        """

        if function is not None:
            self._open_temp_context()

        for child in children:
            if isinstance(child, str):
                self.write(child)
            else:
                # All remaining children should be nodes now.
                assert isinstance(child, Node)
                # Nodes are either numbered, or have a name.
                # Numbered nodes correspond to command arguments. Those should
                # have been processed before, and not be passed to _parse_children().
                assert isinstance(child.name, str), (
                    f"Argument {child.name!r} should have been processed "
                    "and removed before calling _parse_children() !"
                )

                self.parse_node(child)

        if function is not None:
            self._apply_func_and_close_temp_context(function, **options)

    @staticmethod
    def _parse_options(node: Node):
        """Parse a tag options, following the syntax {key1=val1,...}."""
        options = node.options
        args = []
        kw = {}
        if options is not None:
            options_list = options.split(",")
            for option in options_list:
                if "=" in option:
                    key, val = option.split("=")
                    kw[key.strip()] = val.strip()
                else:
                    args.append(option.strip())
        return args, kw

    def write(self, text: str, parse: bool = False, verbatim: bool = False):
        """Append a piece of LaTeX text to context['PTYX_LATEX'].

        :param text: a block of text, which may contain pTyX code.
        :type text: string
        :param parse: indicate text have to be parsed.
        :type parse: bool
        :param verbatim: emulate LaTeX verbatim mode (escape LaTeX characters, keep indentation...)
        :type verbatim: bool

        .. note:: Param `parse` defaults to False, since in most cases text is already
                  parsed at this state.
                  As an exception, when called from inside a #PYTHON [...] #END
                  code block, write() may be applied to unparsed text.
        """
        # Parsing at this stage is quite expansive yet unnecessary most of the time,
        # so some basic testing is done before.
        text = str(text)
        if text.strip():
            for flag in "+-*":
                if self.flags.get(flag):
                    text = (r"\times " if flag == "*" else flag) + text
                    self.flags[flag] = False
        if parse and "#" in text:
            if param["debug"]:
                print("Parsing %s..." % repr(text))
            self.parse_node(self.parser.generate_tree(text), function=(latex_verbatim if verbatim else None))
        else:
            if verbatim:
                text = latex_verbatim(text)
            self.context["PTYX_LATEX"].append(text)

    def read(self):
        return "".join(self.context["PTYX_LATEX"])

    def _parse_APART_tag(self, node: Node):
        """Interpret a piece of code in a sandbox, eliminating side effects."""
        # Backup local variables and reset context.
        context_backup = self.context
        self.set_new_context()
        # Interprete code
        self._parse_children(node.children)
        # Restore local variables and update generated LaTeX code.
        self.set_new_context(context_backup)

    def _parse_API_VERSION_tag(self, node: Node):
        def version_tuple(version: str):
            return version.split(".")

        assert isinstance(node.children[0], Node), repr(node)
        assert isinstance(node.children[0].children[0], str), repr(node)
        version = version_tuple(node.children[0].children[0])
        if version_tuple(__version__) < version:
            print("Warning: pTyX engine is too old (v%s required)." % version)
        if version < version_tuple(__api__):
            print(
                "Warning: pTyX file uses an old API. You may have to update "
                "your pTyX file code before compiling it."
            )
        # TODO: display a short list of API changes which broke compatibility.
        self.context["API_VERSION"] = version

    def _parse_ASK_tag(self, node: Node):
        self._parse_children(node.children, function=self.context.get("format_ask"))

    def _parse_ASK_ONLY_tag(self, node: Node):
        if not self.WITH_ANSWERS:
            self._parse_children(node.children, function=self.context.get("format_ask_only"))
        else:
            print("Skipping ASK_ONLY section...")

    def _parse_ANS_tag(self, node: Node):
        if self.WITH_ANSWERS:
            self._parse_children(node.children, function=self.context.get("format_ans"))

    def _parse_ANSWER_tag(self, node: Node):
        if self.WITH_ANSWERS:
            assert isinstance(node.children[0], Node), repr(node)
            self._parse_children(node.children[0].children, function=self.context.get("format_answer"))

    def _parse_QUESTION_tag(self, node: Node):
        if not self.WITH_ANSWERS:
            assert isinstance(node.children[0], Node), repr(node)
            self._parse_children(node.children[0].children)

    def _parse_IF_tag(self, node: Node):
        test = eval(node.arg(0), self.context)
        if test:
            self._parse_children(node.children[1:])
        return test

    _parse_ELIF_tag = _parse_IF_tag

    def _parse_CONDITIONAL_BLOCK_tag(self, node: Node):
        for child in node.children:
            assert isinstance(child, Node)
            if self.parse_node(child):
                # If an `IF` or `ELIF` node was processed, all successive `ELIF`
                # or `ELSE` nodes must be skipped.
                # (The same for `CASE`).
                break

    def _parse_ELSE_tag(self, node: Node):
        self._parse_children(node.children)

    def _parse_IFNUM_tag(self, node: Node):
        if eval(node.arg(0), self.context) == self.NUM:
            assert isinstance(node.children[1], Node), repr(node)
            self._parse_children(node.children[1].children)

    def _parse_CASE_tag(self, node: Node):
        test = eval(node.arg(0), self.context) == self.NUM
        if test:
            self._parse_children(node.children[1:])
        return test

    def _parse_IMPORT_tag(self, node: Node):
        exec("from %s import *" % node.arg(0), self.context)

    def _parse_LOAD_tag(self, node: Node):
        # LOAD tag is used to load extensions **before** syntax tree is built.
        pass

    def _parse_INCLUDE_tag(self, node: Node):
        # INCLUDE tag is used to insert code in isolated mode **before** syntax tree is built.
        pass

    @staticmethod
    def _format_python_code_snippet(python_code) -> List[str]:
        """Return a list of prettified lines of python code, ready to be printed."""
        msg = ["", "%s %s Executing following python code:" % (chr(9474), chr(9998))]
        lines = [""] + python_code.split("\n") + [""]
        zfill = len(str(len(lines)))
        msg.extend(
            "%s %s %s %s" % (chr(9474), str(i).zfill(zfill), chr(9474), line) for i, line in enumerate(lines)
        )
        n = max(len(s) for s in msg)
        msg.insert(1, chr(9581) + n * chr(9472))
        msg.insert(3, chr(9500) + n * chr(9472))
        msg.append(chr(9584) + n * chr(9472))
        assert isinstance(python_code, str)
        return msg

    def _parse_PYTHON_tag(self, node: Node):
        assert len(node.children) == 1
        python_code = node.children[0]
        assert isinstance(python_code, str), repr(python_code)
        self._exec_python_code(python_code, self.context)

    # Remove comments before generating tree ?
    def _parse_COMMENT_tag(self, node: Node):
        pass

    def _parse_ASSERT_tag(self, node: Node):
        code = node.arg(0)
        test = eval(code, self.context)
        if not test:
            print("Error in assertion (NUM=%s):" % self.NUM)
            print("***")
            print(code)
            print("***")
            assert test

    def _parse_EVAL_tag(self, node: Node):
        args, kw = self._parse_options(node)
        if self.context.get("ALL_FLOATS"):
            self.flags["floats"] = True
        for arg in args:
            if arg.isdigit():
                self.flags["round"] = int(arg)
            elif arg == ".":
                self.flags["."] = True
            elif arg in ("floats", "float"):
                self.flags["floats"] = True

            elif arg == "str":
                self.flags["str"] = True
            else:
                raise ValueError("Unknown flag: " + repr(arg))
        # XXX: support options round, float, (sympy, python,) select and rand
        code = node.arg(0)
        assert isinstance(code, str), type(code)
        try:
            txt = self._eval_and_format_python_expr(code)
        except Exception:
            print("ERROR: Can't evaluate this: " + repr(code))
            raise
        # Tags must be cleared *before* calling .write(txt), since .write(txt)
        # add '+', '-' and '\times ' before txt if corresponding flags are set,
        # and ._eval_and_format_python_expr() has already do this.
        self.flags.clear()
        self.write(txt)

    def _parse_MACRO_tag(self, node: Node):
        name = node.arg(0)
        self.macros[name] = node.children[1:]

    def _parse_CALL_tag(self, node: Node):
        """Calling a macro."""
        name = node.arg(0)
        if name not in self.macros:
            raise NameError(f"Error: MACRO {name!r} undefined.")
        self._parse_children(self.macros[name])

    def _parse_ENUM_tag(self, node: Node):
        # This tag does nothing by itself, but is used by some extensions.
        self._parse_children(node.children)

    def _parse_VERBATIM_tag(self, node: Node):
        self._parse_children(node.children, function=latex_verbatim)

    @staticmethod
    def _child_index(children, name):
        """Return the index of the first child of name `name` in `children` list.

        Argument `name` must be a `Node` name.

        A `ValueError` is raised if no such `Node` is found.
        """
        for i, child in enumerate(children):
            if isinstance(child, Node) and child.name == name:
                return i
        raise ValueError(f"No {name} Node found.")

    def _shuffle_and_parse_children(self, node: Node, children=None, target: str = "ITEM", **kw):
        # Shuffles all the #ITEM sections inside a #SHUFFLE block.
        # Note that they may be some text or nodes before first #ITEM,
        # if so they should be left unmodified at first position.
        # Nota: children may be only some children of given node.
        # This is used when some children were already processed before
        # (this is the case for arguments usually).
        if children is None:
            children = node.children
        if not children:
            return
        try:
            i = self._child_index(children, target)
        except ValueError:
            # `target` not found: nothing to shuffle.
            print(f"WARNING: Nothing to shuffle ({target!r} not found).")
            self._parse_children(children, **kw)
            return
        items = children[i:]
        # Now, we will shuffle only items which are nodes of name `target`.
        # So, we split items in groups, so that every group starts with
        # a Node named `target`.
        # For example, if target is `QUESTION`, and items are
        # ['QUESTION', 'OTHER', 'QUESTION', 'OTHER', 'ANOTHER'],
        # groups will be [['QUESTION', 'OTHER'],
        #                 ['QUESTION', 'OTHER', 'ANOTHER']]
        # Then, we will shuffle those groups. We may obtain for example :
        #                [['QUESTION', 'OTHER', 'ANOTHER'],
        #                 ['QUESTION', 'OTHER']]
        # Finally, we flatten `groups` list to obtain the following:
        # ['QUESTION', 'OTHER', 'ANOTHER', 'QUESTION', 'OTHER']
        # 1. Generate groups
        groups = []
        for item in items:
            if isinstance(item, Node) and item.name == target:
                groups.append([item])
            else:
                groups[-1].append(item)
        # 2. Shuffle groups
        randfunc.shuffle(groups)
        #        print(groups)
        #        input('-- pause --')
        # 3. Flatten `groups` list
        items = sum(groups, [])

        #        print(f'items: {items}')
        #        input('-- pause --')
        self._parse_children(children[:i] + items, **kw)
        # print('\n------------')
        # print('SHUFFLE: %s elements, excluding first %s.' % len(children), i)
        # print('state hash is %s' % hash(random.getstate()))
        # print('------------\n')

    def _parse_SHUFFLE_tag(self, node: Node):
        self._shuffle_and_parse_children(node)

    def _parse_ITEM_tag(self, node: Node):
        self._parse_children(node.children)

    def _parse_SEED_tag(self, node: Node):
        # SEED tag is a special tag which is managed independently, at first pass
        # (it avoids user including it inadvertently inside
        # a conditional block or a #ASK_ONLY/#END block, which may result in
        # what seems to be a very strange behaviour of the compiler !)
        pass

    def _pick_and_parse_children(self, node: Node, children: List = None, target: str = "ITEM", **kw):
        # Choose only one between all the #ITEM sections inside a #PICK block.
        # Note that they may be some text or nodes before first #ITEM,
        # if so they should be left unmodified at their original position.
        if children is None:
            children = node.children
        if not children:
            return
        i = self._child_index(children, target)
        items = children[i:]
        for item in items:
            if not (isinstance(item, Node) and item.name == target):
                log = [
                    "This is current structure:",
                    node.display(),
                    rf"\n{item!r} is not an {target!r} node !",
                ]
                raise RuntimeError("\n".join(log))
        item = randfunc.randchoice(items)
        self._parse_children(children[:i] + [item], **kw)
        # print('\n------------')
        # print('SHUFFLE: %s elements, excluding first %s.' % len(children), i)
        # print('state hash is %s' % hash(random.getstate()))
        # print('------------\n')

    def _parse_PICK_tag(self, node: Node) -> None:
        self._pick_and_parse_children(node)

    # TODO: Refactor _parse_PICK_tag/_parse_SHUFFLE_tag

    def _parse_ROOT_tag(self, node: Node) -> None:
        self._parse_children(node.children)

    def _parse_FREEZE_RANDOM_STATE_tag(self, node: Node) -> None:
        state = random.getstate()
        self._parse_children(node.children)
        random.setstate(state)

    def _parse_TEST_tag(self, node: Node) -> None:
        try:
            if eval(node.arg(0), self.context):
                assert isinstance(node.children[1], Node), repr(node)
                self._parse_children(node.children[1].children)
            else:
                assert isinstance(node.children[2], Node), repr(node)
                self._parse_children(node.children[2].children)
        except Exception:
            print(node.display(color=False))
            raise

    def _parse_SHARP_tag(self, node: Node) -> None:
        """2 sharps (##) will be converted to 1 sharp (#)"""
        self.write("#")

    def _parse_ADD_tag(self, node: Node) -> None:
        # a '+' will be displayed at the beginning of the next result if positive ;
        # if the result is negative, nothing will be done, and if null,
        # no result at all will be displayed.
        self.flags["+"] = True

    def _parse_SUB_tag(self, node: Node) -> None:
        # a '-' will be displayed at the beginning of the next result, and the result
        # will be embedded in parentheses if negative.
        self.flags["-"] = True

    def _parse_MUL_tag(self, node: Node) -> None:
        # a '\times' will be displayed at the beginning of the next result, and the result
        # will be embedded in parentheses if negative.
        self.flags["*"] = True

    def _parse_EQUAL_tag(self, node: Node) -> None:
        # Display '=' or '\approx' when a rounded result is requested :
        # if rounded is equal to exact one, '=' is displayed.
        # Else, '\approx' is displayed instead.
        self.flags["="] = True
        # All other operations (#+, #-, #*) occur just before number, but between `=` and
        # the result, some formatting instructions may occur (like '\fbox{' for example).
        # So, `#=` is used as a temporary marker, and will be replaced by '=' or '\approx' later.
        self.write("#=")

    def _parse_SIGN_tag(self, node: Node) -> None:
        # '>0' or '<0' will be displayed after the next result, depending on it's sign.
        # (If result is zero, this won't do anything.)
        last_value = self.context["_"]
        if last_value > 0:
            self.write(">0")
        elif last_value < 0:
            self.write("<0")

    def _parse_DEBUG_tag(self, node: Optional[Node]) -> None:
        while True:
            msg = "Debug point. Enter command, or quit (q! + ENTER):"
            sep = len(msg) * "="
            print(sep)
            print(msg)
            print(sep)
            command = input("[In]: ")
            print("[Out]: ")
            if command == "q!":
                break
            else:
                try:
                    exec(command, self.context)
                except Exception as e:
                    print("*** ERROR ***")
                    print(e)

    def _parse_PRINT_tag(self, node: Node) -> None:
        print(node.arg(0))

    @staticmethod
    def _exec(code, context):
        """exec is encapsulated in this function so as to avoid problems
        with free variables in nested functions."""
        exec(code, context)

    def _exec_python_code(self, code: str, context: dict):
        code = code.replace("\r", "")
        code = code.rstrip().lstrip("\n")
        msg = self._format_python_code_snippet(code)
        # Indentation test
        initial_indent = len(code) - len(code.lstrip(" "))
        if initial_indent:
            # remove initial indentation
            code = "\n".join(line[initial_indent:] for line in code.split("\n"))
        try:
            self._exec(code, context)
        except Exception as e:  # noqa
            for tb in traceback.extract_tb(e.__traceback__):
                if tb.name == "<module>" and isinstance(tb.lineno, int):
                    i = tb.lineno + 4
                    msg[i] = f"\u001b[33m{msg[i]}\u001b[0m"
                    break
            e.msg = "\n".join(msg)  # type: ignore
            raise

        return code

    def _eval_python_expr(self, code: str):
        flags = self.flags
        context = self.context
        if not code:
            return ""
        sympy_code = flags.get("sympy", param["sympy_is_default"])

        if sympy_code and not SYMPY_AVAILABLE:
            raise ImportError("sympy library not found.")

        varname = ""
        i = code.find("=")
        if 0 < i < len(code) - 1 and code[i + 1] != "=":
            varname = code[:i].strip()
            if re.match(self.re_varname, varname):
                # This is (probably) a variable name (or a list or dict item reference).
                code = code[i + 1 :]
            else:
                # This is not a variable name.
                varname = ""
        # Last value will be accessible through '_' variable
        if not varname:
            varname = "_"
        if " if " in code and " else " not in code:
            code += " else ''"
        if SYMPY_AVAILABLE and sympy_code:
            import sympy

            try:
                result = sympy.sympify(code, locals=context)
                if isinstance(result, str):
                    result = result.replace("**", "^")
            except (sympy.SympifyError, AttributeError):
                # sympy.sympify() can't parse attributes and methods inside
                # code for now (AttributeError is raised then).
                result = eval(code, context)
                print("Warning: sympy can't parse %s. " "Switching to standard evaluation mode." % repr(code))
            except Exception:
                # print sorted(context.keys())
                print("Uncatched error when evaluating %s" % repr(code))
                raise
        else:
            result = eval(code, context)
        result = context["_"] = self._apply_flag(result)
        i = varname.find("[")
        # for example, varname == 'mylist[i]' or 'mylist[2]'
        context["LAST"] = result
        if i == -1:
            context[varname] = result
        else:
            key = eval(varname[i + 1 : -1], context)
            varname = varname[:i].strip()
            context[varname][key] = result
        return result

    def _eval_and_format_python_expr(self, code: str) -> str:
        flags = self.flags
        context = self.context
        if not code:
            return ""
        sympy_code = flags.get("sympy", param["sympy_is_default"])

        display_result = True
        if code.endswith(";"):
            code = code.rstrip(";")
            display_result = False

        for subcode in advanced_split(code, ";", brackets=()):
            result = self._eval_python_expr(subcode)
        # Note that only last result will be displayed.
        # In particular, if code ends with ';', last result will be ''.
        # So, '#{a=5}' and '#{a=5;}' will both affect 5 to `a`,
        # but the second will not display '5' on final document.

        if not display_result:
            return ""

        if sympy_code and not flags.get("str"):
            from ptyx.printers import sympy2latex

            latex = sympy2latex(result, **flags)
        else:
            latex = str(result)

        def neg(latex):
            return latex.lstrip().startswith("-")

        if flags.get("+"):
            if result == 0:
                latex = ""
            elif not neg(latex):
                latex = "+" + latex
        elif flags.get("*"):
            if neg(latex) or getattr(result, "is_Add", False):
                latex = r"\left(" + latex + r"\right)"
            latex = r"\times " + latex
        elif flags.get("-"):
            if neg(latex) or getattr(result, "is_Add", False):
                latex = r"\left(" + latex + r"\right)"
            latex = "-" + latex
        elif flags.get("="):
            if flags.get("result_is_exact"):
                symb = " = "
            else:
                symb = r" \approx "
            # Search backward for temporary `#=` marker in list, and replace
            # by appropriate symbol.
            for textlist in self.backups + [context["PTYX_LATEX"]]:
                for i, elt in enumerate(reversed(textlist)):
                    if elt == "#=":
                        textlist[len(textlist) - i - 1] = symb
                        return latex
            print("Debug warning: `#=` couldn't be found when scanning context !")
            print("There is most probably a bug in pTyX, entering debugging...")
            self._parse_DEBUG_tag(None)
        return latex

    def _apply_flag(self, result):
        """Apply special parameters like [num], [rand], [floats] or [round] to result.

        Note that [num] and [rand] parameters require that result is iterable,
        otherwise, nothing occurs.
        If result is iterable, an element of result is returned, chosen according
        to current flag."""
        flags = self.flags
        if hasattr(result, "__iter__"):
            if flags.get("rand"):
                result = random.choice(result)
            elif flags.get("select"):
                result = result[self.NUM % len(result)]

        if "round" in flags:
            try:
                if SYMPY_AVAILABLE:
                    round_result = numbers_to_floats(result, ndigits=flags["round"])
                else:
                    round_result = round(result, flags["round"])
            except ValueError:
                print("** ERROR while rounding value: **")
                print(result)
                print("-----")
                print("".join(self.context["PTYX_LATEX"])[-100:])
                print("-----")
                raise
            if SYMPY_AVAILABLE:
                import sympy
            # noinspection PyUnboundLocalVariable
            if SYMPY_AVAILABLE and isinstance(result, sympy.Basic):
                flags["result_is_exact"] = {_float_me_if_you_can(elt) for elt in result.atoms()} == {
                    _float_me_if_you_can(elt) for elt in round_result.atoms()
                }
            else:
                flags["result_is_exact"] = result == round_result
            result = round_result
        elif "floats" in self.flags:
            result = numbers_to_floats(result)
        return result


class Compiler:
    """Compiler is the main object of pTyX.

    Usage:

        >>> from ptyx.latex_generator import Compiler
        >>> c = Compiler()
        >>> c.parse('#{a=S(1)/2} + #{b=2} = #{a+b}')
        '\frac{1}{2} + 2 = \frac{5}{2}'

    The following methods are called successively to generate LaTeX code from
    a pTyX file:
        * .read_file(path) will read the content of the file.
        * ._include_subfiles() will parse #INCLUDE{filename} tags and
          include coresponding files content.
        * ._call_extensions() will search for extensions in this content,
          then call the extensions to convert content into plain pTyX code.
        * ._read_seed() will search for a #SEED tag, or give a default seed
          value, used to generate all pseudo-random content later.
        * .generate_syntax_tree() will convert this code into a syntax tree.
          This should be done only once ofr each document, even if multiple
          versions of this document are needed.
        * Finally, .get_latex() will generate and return the LaTeX code.

      Pseudo-random content will depend on the seed (see above), but also
      of the document number, given by `gen.context['PTYX_NUM']`.
      So, changing `gen.context['PTYX_NUM']` enables to generate different
      versions of the same document.
    """

    def __init__(self):
        self.syntax_tree_generator = SyntaxTreeGenerator()
        self.latex_generator = LatexGenerator(self)
        self.reset()

    def reset(self) -> None:
        self._state: State = {}
        # Make SyntaxTreeGenerator context free ?
        self.syntax_tree_generator.reset()
        self.latex_generator.reset()

    def read_code(self, code: str) -> None:
        """Feed compiler with given code."""
        self._state["path"] = None
        self._state["input"] = code

    def read_file(self, path: Union[Path, str]) -> None:
        """Feed compiler with given file code."""
        self._state["path"] = Path(path).expanduser().resolve()
        with open(path, "r") as input_file:
            self._state["input"] = input_file.read()

    @property
    def dir_path(self) -> Path:
        """Return input ptyx file directory, if any, or current working directory else."""
        file_path = self.file_path
        return Path.cwd() if file_path is None else file_path.parent

    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Interpret `path` relatively to input ptyx file."""
        if isinstance(path, str):
            path = Path(path.strip())
        path = path.expanduser()  # do NOT resolve yet !
        if not path.is_absolute():
            path = self.dir_path / path
        return path

    def _include_subfiles(self, code: str) -> str:
        """Parse all #INCLUDE tags, then include corresponding files content."""

        def include(match):
            path = self._resolve_path(match.group(1))
            with open(path) as file:
                return f"\n#APART\n{file.read()}#END_APART\n"

        # noinspection RegExpRedundantEscape
        return re.sub(r"#INCLUDE\{([^}]+)\}", include, code)

    def _call_extensions(self, code: str) -> tuple[str, dict[str, ModuleType]]:
        """Search for extensions (#LOAD{name} tags), then call them."""
        # First, we search if some extensions must be load.
        # This must be done at the very beginning, since extensions may
        # define their own specialized language, to be converted to
        # valid pTyX code (and then to LaTeX).
        names = []

        def collect(match):
            names.append(match.group(1))
            return ""

        # Use re.sub to find all extensions and remove #LOAD tags in one pass.
        # noinspection RegExpRedundantEscape
        code = re.sub(r"#LOAD\{\s*(\w+)\s*\}", collect, code)
        extensions: Dict[Tag, ModuleType] = {}
        tags_syntax: Dict[Tag, TagSyntax] = {}
        tags_source: Dict[Tag, str] = {}
        latex_generator_extensions = []
        for extension_name in names:
            try:
                extensions[extension_name] = import_module(f"ptyx.extensions.{extension_name}")
            except ImportError:
                # Try to find a matching registered plugin.
                for entry_point in metadata.entry_points(group="ptyx.extensions"):
                    if entry_point.name == extension_name:
                        extensions[extension_name] = import_module(entry_point.value)
                        break
                else:
                    traceback.print_exc()
                    raise ImportError(f"Extension {extension_name} not found.")
            # Test if extension defines new tags.
            ext_tags = getattr(extensions[extension_name], "__tags__", {})
            for tag, syntax in ext_tags.items():
                # Test for conflict between extensions.
                if tag in tags_source:
                    raise NameError(
                        f"Extension {extension_name} tries to define tag {tag}, "
                        f"which was already defined by extension {tags_source[tag]}."
                    )
                # Tag not already declared, everything seems OK.
                tags_source[tag] = extension_name
                tags_syntax[tag] = syntax
            # Extension may subclass LatexGenerator class, notably to handle new tags.
            subclass = getattr(extensions[extension_name], "__latex_generator_extension__", None)
            if subclass is not None:
                latex_generator_extensions.append(subclass)
        # Load new tags.
        self.add_new_tags(*tags_syntax.items())
        # Update LatexGenerator.
        if latex_generator_extensions:
            # TODO: Test for conflicting methods ?
            class CustomLatexGenerator(*reversed(latex_generator_extensions)):  # type: ignore
                pass

            self.latex_generator.__class__ = CustomLatexGenerator
        for name in names:
            # execute `main()` function of extension.
            if hasattr(extensions[name], "main"):
                code = extensions[name].main(code, self)
        return code, extensions

    def _read_seed(self, code: str) -> Tuple[str, Optional[int]]:
        """Extract seed value from code, searching for #SEED{num} tag.

        Return the code without the #SEED{...} tag, and the seed value (if any, `None` else).
        """
        counter = 0
        value = None

        def seed(match):
            nonlocal counter, value
            value = int(match.group(1))
            counter += 1
            return ""

        # noinspection RegExpRedundantEscape
        code = re.sub(r"#SEED\{\s*(\d+)\s*\}", seed, code)
        if counter == 0:
            path = self._state.get("path")
            print(f"Warning: #SEED not found, using hash of ptyx file path ({path!r}) as seed.")
            value = hash(path)
        elif counter > 1:
            print(f"Warning: multiple #SEED found, only last one will be used: {value}.")
        return code, value

    @staticmethod
    def _assert_no_comment(code: str) -> None:
        """AssertionError raised if comments remain."""
        comments = any((" # " in code, "\n# " in code, code.startswith("# ")))
        if comments:
            print(code)
        assert not comments, "There should be no remaining comment. Maybe a problem with an extension ?"

    def preparse(self) -> None:
        code = self._state.get("input")
        if code is None:
            raise RuntimeError("Compiler.read_code() or Compiler.read_file() must be run first.")
        remove_comments = self.syntax_tree_generator.remove_comments
        # Remove comments first, so one can comment a file inclusion for example.
        code = remove_comments(code)
        assert isinstance(code, str)
        self._assert_no_comment(code)
        code = remove_comments(self._include_subfiles(code))
        self._state["after_include"] = code
        assert isinstance(code, str)
        code, extensions = self._call_extensions(code)
        code, seed = self._read_seed(code)
        # Remove any comment that may have been generated by an extension.
        code = remove_comments(code)
        assert isinstance(code, str)
        self._state["plain_ptyx_code"] = code
        self._state["loaded_extensions"] = extensions
        # Set the seed used for pseudo-random numbers generation.
        # (The seed value is set in the ptyx file using special tag #SEED{}).
        self._state["seed"] = seed
        self._assert_no_comment(code)
        assert "#INCLUDE{" not in code
        assert "#LOAD{" not in code
        assert "#SEED{" not in code
        # Save pTyX code generated by extensions (this is used for debugging,
        # but if needed extensions can also save some data this way using #COMMENT tag).
        # If input file was /path/to/file/myfile.ptyx,
        # plain pTyX code is saved in /path/to/file/.myfile.ptyx.plain-ptyx
        if extensions:
            path = self._state.get("path")
            if path is not None:
                filename = join(dirname(path), ".%s.plain-ptyx" % basename(path))
                with open(filename, "w") as f:
                    f.write(code)

    def generate_syntax_tree(self) -> None:
        code = self._state.get("plain_ptyx_code")
        if code is None:
            raise RuntimeError("Compiler.preparse() must be run first.")
        self._state["syntax_tree"] = self.syntax_tree_generator.generate_tree(code)

    def get_latex(self, **context) -> str:
        """Compile pTyX code and return LaTeX code.

        `Compiler.generate_syntax_tree()` must be run first.
        """
        tree = self._state.get("syntax_tree")
        if tree is None:
            raise RuntimeError("`Compiler.generate_syntax_tree()` must be run first.")
        gen = self.latex_generator
        gen.clear()
        gen.context.update(context)
        seed = self._state["seed"] + gen.NUM
        randfunc.set_seed(seed)
        try:
            gen.parse_node(tree)
        except Exception as e:
            print("\n*** Error occurred while generating code. ***")
            print("This is current compiler state for debugging purpose:")
            print(80 * "-")
            print("... " + "".join(gen.context["PTYX_LATEX"][-10:]))
            print(80 * "-")
            print("")
            if hasattr(e, "msg"):
                print(e.msg)
            raise
        latex = gen.read()
        if "API_VERSION" not in gen.context:
            print("Warning: no API version specified. This may be an old pTyX file.")
        return latex

    def add_new_tags(self, *tags: Tuple[str, Tuple]) -> None:
        """Add ability for extensions to extend syntax, adding new tags."""
        for name, syntax in tags:
            self.syntax_tree_generator.tags[name] = syntax
            self.latex_generator.parser.tags[name] = syntax
        if tags:
            self.syntax_tree_generator.update_tags()
            self.latex_generator.parser.update_tags()

    # TODO: change the signature of parse, to force use of `code` as a keyword argument.
    # Note that this will involve rewriting a lot of tests in both ptyx and ptyx-mcq projects.
    #   parse(self, *, code: str = None, path: Union[Path, str] = None, **context)

    def parse(self, code: str = None, *, path: Union[Path, str] = None, **context) -> str:
        """Convert ptyx code to plain LaTeX in one shot.

        This is mainly used for testing (in unit tests or in interactive mode).

        One may provide either directly the pTyX code, or the path of a pTyX file to be read.

        If both `code` and `path` are provided, the compiler acts as if `code` was the content
        of the pTyX file located at `path`.
        """
        self.reset()
        if path is None and code is None:
            raise ValueError(
                "You must provide either the pTyX code or the path to a pTyX file:\n"
                'compiler.parse(code="...") or compiler.parse(path="/path/to/file.ptyx")'
            )
        if path is not None:
            self.read_file(path)
        if code is not None:
            self.read_code(code)
        self.preparse()
        self.generate_syntax_tree()
        latex = self.get_latex(**context)
        return latex

    @property
    def syntax_tree(self) -> Node:
        return self._state["syntax_tree"]

    @property
    def seed(self) -> Optional[int]:
        return self._state["seed"]

    @property
    def file_path(self) -> Optional[Path]:
        return self._state["path"]

    @property
    def plain_ptyx_code(self) -> Optional[str]:
        return self._state["plain_ptyx_code"]

    @property
    def loaded_extensions(self) -> List[str]:
        return list(self._state["loaded_extensions"].keys())


compiler = Compiler()

parse = compiler.parse
