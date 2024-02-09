#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 23 15:09:44 2021

@author: Nicolas Pourcelot
"""

import re
from typing import Tuple, Optional, List, Dict, Union, TypeVar, Iterable, Set, Any

from ptyx.errors import PtyxSyntaxError, PythonExpressionError
from ptyx.utilities import find_closing_bracket, term_color

Tag = str
TagSyntax = Tuple[int, int, Optional[List[str]]]
NodeChild = Union[str, "Node"]
S = TypeVar("S")
T = TypeVar("T", bound=NodeChild)


class Node:
    """A node.

    `name` is either the tag name, if the node corresponds
    to a tag's content, or the argument number, if the node corresponds
    to a tag's argument."""

    def __init__(self, name: Union[str, int]):
        self.parent: Optional[Node] = None
        self.name = name
        self.options: Optional[str] = None
        self.children: List[NodeChild] = []

    def __repr__(self):
        return f"<Node {self.name} at {hex(id(self))}>"

    def add_child(self, child: T) -> Optional[T]:
        if not child:
            return None
        self.children.append(child)
        if isinstance(child, Node):
            child.parent = self
        return child

    # @property
    # def content(self):
    #   if len(self.children) != 1:
    #       raise ValueError, "Ambiguous: node has several subnodes."
    #   return self.children[0]

    def arg(self, i: int) -> Any:
        """Return argument number `i` content, which may be a Node, or some text (str)."""
        child = self.children[i]
        if getattr(child, "name", None) != i:
            raise ValueError(f"Incorrect argument number for node {child!r}.")
        assert isinstance(child, Node), repr(child)
        children_number = len(child.children)
        if children_number > 1:
            raise PtyxSyntaxError(
                f"Don't use pTyX code inside {self.name} argument number {i + 1}.\n"
                "------------------\n"
                f"{child.display()}\n"
                "------------------\n"
            )
        if children_number == 0:
            if self.name == "EVAL":
                # EVAL isn't a real tag name: if a variable `#myvar` is found
                # somewhere, it is parsed as an `#EVAL` tag with `myvar` as argument.
                # So, a lonely `#` is parsed as an `#EVAL` with no argument at all.
                raise PtyxSyntaxError("Error! There is a lonely '#' somewhere !")
            print("Warning: %s argument number %s is empty." % (self.name, i + 1))
            return ""

        return child.children[0]

    def display(self, color=True, indent=0, raw=False) -> str:
        texts = ["%s+ Node %s" % (indent * " ", self._format(self.name, color))]
        for child in self.children:
            if isinstance(child, Node):
                texts.append(child.display(color, indent + 2, raw=raw))
            else:
                assert isinstance(child, str)
                text = repr(child)
                if not raw:
                    if len(text) > 30:
                        text = text[:25] + " [...]'"
                if color:
                    text = term_color(text, "green")
                texts.append("%s  - text: %s" % (indent * " ", text))
        return "\n".join(texts)

    def as_text(self, skipped_children: Iterable[int] = ()) -> str:
        content = []
        for i, child in enumerate(self.children):
            if i in skipped_children:
                continue
            if isinstance(child, Node):
                content.append(child.as_text())
            else:
                assert isinstance(child, str)
                content.append(child)
        return "".join(content)

    @staticmethod
    def _format(val: object, color: bool) -> str:
        if not color:
            return str(val)
        if isinstance(val, str):
            return term_color(val, "yellow")
        if isinstance(val, int):
            return term_color(str(val), "blue")
        return str(val)

    def eval_arg(self, i: int, context: dict[str, Any]) -> Any:
        """Raw evaluation of argument number `i` in context.

        This argument must contain valid python code.

        If an exception occurs, a `PythonExpressionError` is raised, with some information.
        """
        python_code = self.arg(i)
        try:
            return eval(python_code, context)
        except Exception as e:
            raise PythonExpressionError(python_code=python_code, ptyx_tag=str(self.name)) from e


class SyntaxTreeGenerator:
    # For each tag, indicate:
    #   1. The number of arguments that contain python code.
    #      Those arguments will not be parsed.
    #   2. The number of parsed arguments.
    #      Those arguments may contain inner pTyX code, which needs parsing.
    #   3. If the tag opens a block, a list of all the tags closing the block,
    #      else `None`.
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
    # in {val=="}"}, the bracket closing the tag is the second `}`, not the first one !

    tags: Dict[Tag, TagSyntax] = {
        "ANS": (0, 0, ["@END", "@END_ANS"]),
        "ANSWER": (0, 1, None),
        "APART": (0, 0, ["@END", "@END_APART"]),
        "ASK": (0, 0, ["@END", "@END_ASK"]),
        "ASK_ONLY": (0, 0, ["@END", "@END_ASK_ONLY"]),
        "ASSERT": (1, 0, None),
        # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
        "CASE": (1, 0, ["CASE", "ELSE", "END", "END_CASE"]),
        "COMMENT": (0, 0, ["@END", "@END_COMMENT"]),
        # CONDITIONAL_BLOCK isn't a real tag, but is used to enclose
        # a #CASE{...}...#CASE{...}...#END block, or an #IF{...}...#ELIF{...}...#END block.
        "CONDITIONAL_BLOCK": (0, 0, ["@END", "@END_IF"]),
        "DEBUG": (0, 0, None),
        "EVAL": (1, 0, None),
        # ENUM indicates the start of an enumeration.
        # It does nothing by itself, but is used by some extensions.
        "ENUM": (0, 0, ["@END", "@END_ENUM"]),
        # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
        "IF": (1, 0, ["ELIF", "ELSE", "END", "END_IF"]),
        # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
        "ELIF": (1, 0, ["ELIF", "ELSE", "END", "END_IF"]),
        # Do *NOT* consume #END tag, which must be used to end #CONDITIONAL_BLOCK.
        "ELSE": (0, 0, ["END", "END_IF"]),
        "IMPORT": (1, 0, None),
        "LOAD": (0, 1, None),
        "FREEZE_RANDOM_STATE": (0, 0, []),
        "IFNUM": (1, 1, None),
        "INCLUDE": (0, 1, None),
        "CALL": (0, 1, None),
        "MACRO": (0, 1, ["@END", "@END_MACRO"]),
        "PICK": (0, 0, ["@END", "@END_PICK"]),
        "PRINT": (0, 1, None),
        "PRINT_EVAL": (0, 1, None),
        "PTYX_VERSION": (0, 1, None),
        "PYTHON": (0, 0, ["@END_PYTHON"]),
        "QUESTION": (0, 1, None),
        # ROOT isn't a real tag, and is never closed.
        "ROOT": (0, 0, []),
        "SEED": (0, 1, None),
        "SHUFFLE": (0, 0, ["@END", "@END_SHUFFLE"]),
        # Do *NOT* consume #END tag, which must be used to end #SHUFFLE block.
        "ITEM": (0, 0, ["ITEM", "END", "END_SHUFFLE", "END_PICK"]),
        "SIGN": (0, 0, None),
        "TEST": (1, 2, None),
        "VERBATIM": (0, 0, ["@END", "@END_VERBATIM"]),
        "-": (0, 0, None),
        "+": (0, 0, None),
        "*": (0, 0, None),
        "=": (0, 0, None),
        "?": (0, 0, None),
        # "#": (0, 0, None),
    }

    # NOTE: Should all tags starting with END_TAG automatically close TAG ?
    # (Should this be a syntax feature ?
    # It sounds nice, but how should we deal with the `@` then ?).

    def __init__(self) -> None:
        # Add ability to update the set of closing tags for instances of
        # SyntaxTreeGenerator.
        # It is used by extensions to define new closing tags,
        # by calling `Compiler.add_new_tag()`.
        self._found_tags: Set[Tag] = set()
        self.reset()

    def reset(self) -> None:
        """Full reset."""
        self.tags = dict(self.tags)
        self.update_tags()
        self.syntax_tree: Node | None = None

    @staticmethod
    def only_closing(tag: str) -> bool:
        """Return `True` if tag is only a closing tag, `False` else."""
        return tag == "END" or tag.startswith("END_")

    def update_tags(self) -> None:
        """Automatically add closing tags, then generate sorted list."""
        missing = set()
        for name, syntax in self.tags.items():
            closing_tags = syntax[2]
            if closing_tags is None:
                continue
            for tag in closing_tags:
                tag = tag.lstrip("@")
                if tag not in self.tags:
                    missing.add(tag)

        for name in missing:
            self.tags[name] = (0, 0, None)

        # Tags sorted by length (longer first).
        # This is used for matching tests.
        self.sorted_tags = sorted(self.tags, key=len, reverse=True)

    @staticmethod
    def remove_comments(text: str) -> str:
        # If the comment is at the end of a line, don't remove the end of line.
        # However, if the full line is a comment, remove the end of line (\n).
        text = re.sub("( # .+)|(^# .+\n)", "", text, flags=re.MULTILINE)
        return text

    def generate_tree(self, text: str) -> Node:
        """Pre-parse pTyX code and generate a syntax tree.

        :param text: some pTyX code.
        :type text: string

        .. note:: To access generated syntax tree, use `.syntax_tree` attribute.
        """
        # Now, we will parse Ptyx code to generate a syntax tree.
        self._found_tags = set()
        self.syntax_tree = Node("ROOT")
        # Remove all comments from text.
        text = self.remove_comments(text)
        self._generate_tree(self.syntax_tree, text)
        self.syntax_tree.tags = self._found_tags  # type: ignore
        return self.syntax_tree

    def _generate_tree(self, node, text):
        """Parse `text`, then add corresponding content to `node`."""
        position = 0
        update_last_position = True
        node._closing_tags = []

        while True:
            # --------------
            # Find next tag.
            # --------------
            # A tag starts with '#'.

            # last_position should not be updated if false positives
            # were encountered (ie. #1, #2 in \newcommand{}...).
            if update_last_position:
                last_position = position
            else:
                update_last_position = True
            position = tag_position = text.find("#", position)
            if position == -1:
                # No tag anymore.
                break
            position += 1
            # Is this a known tag ?
            for tag in self.sorted_tags:
                if text[position:].startswith(tag):
                    # Mmm, this begins like a known tag...
                    # In fact, it will really match a known tag if one of the following occurs:
                    # - next character is not alphanumeric ('#IF{' for example).
                    # - tag is not alphanumeric ('#*' tag for example).
                    if not tag[-1].replace("_", "a").isalnum():
                        # Tag is not alphanumeric, so no confusion with a variable name can occur.
                        # -> yes, a known tag found !
                        position += len(tag)
                        break
                    if position + len(tag) == len(text):
                        # There is no next character (last text character reached).
                        # -> yes, a known tag found !
                        position += len(tag)
                        break
                    next_character = text[position + len(tag)]
                    if not (next_character == "_" or next_character.isalnum()):
                        # Next character is not alphanumeric
                        # -> yes, a known tag found !
                        position += len(tag)
                        break
                    # -> sorry, try again.
            else:
                if (
                    position >= len(text)
                    or text[position].isdigit()
                    or text[position] == " "
                    or text[position] == "#"
                ):
                    # This not a tag: LaTeX uses #1, #2, #3 as \newcommand{} parameters.
                    # This may also be a simple \# .
                    # Pretend nothing happened.
                    position += 1
                    update_last_position = False
                    continue
                else:
                    # This is not a known tag name.
                    # Default tag name is EVAL.
                    # Notably:
                    # - any variable (like #a)
                    # - any expression (like #{a+7})
                    # will result in an #EVAL tag.
                    tag = "EVAL"

            # ------------------------
            # Deal with new found tag.
            # ------------------------
            # Syntax tree maintains a record of all tags found during parsing.
            # (This tags set can be later accessed through its .tags attribute.)
            self._found_tags.add(tag)

            # Add text found before this tag to the syntax tree.
            # --------------------------------------------------

            remove_trailing_newline = self.tags[tag][2] is not None or self.only_closing(tag)
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
                i = max(text.rfind("\n", None, tag_position), 0)
                if text[i:tag_position].isspace():
                    node.add_child(text[last_position:i].replace("##", "#"))
                else:
                    node.add_child(text[last_position:tag_position].replace("##", "#"))
            else:
                node.add_child(text[last_position:tag_position].replace("##", "#"))

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
            # Note that for #IF blocks, there is no such difficulty,
            # because an #IF tag always opens a new CONDITIONAL_BLOCK.
            if (tag == "CASE" and node.name != "CASE") or tag == "IF":
                node = node.add_child(Node("CONDITIONAL_BLOCK"))
                node._closing_tags = self.tags["CONDITIONAL_BLOCK"][2]

            # Detect if this tag is actually closing a node.
            # ----------------------------------------------
            while tag in node._closing_tags:
                # Close node, but don't consume tag.
                node = node.parent
            if "@" + tag in node._closing_tags:
                # Close node and consume tag.
                node = node.parent
                continue

            # Special case : don't pre-parse #PYTHON ... #END content.
            # ----------------------------------------------------
            if tag == "PYTHON":
                end = text.find("#END_PYTHON", position)
                if end == -1:
                    raise PtyxSyntaxError("#PYTHON tag must be close with a #END_PYTHON tag.")
                # Create and enter new node.
                node = node.add_child(Node(tag))
                # Some specific parsing is done however:
                # a line starting with `%` will be interpreted as a comment.
                # This makes the code a bit more readable, since `%` is already used
                # for comments in LateX code.
                # TODO: this was useful when editing pTyX code in a LaTeX editor.
                #       Is this still the case, now that there exist a custom pTyX editor?
                _text = text[position:end]
                _text = re.sub(r"^\s*%", "#", _text, flags=re.MULTILINE)
                node.add_child(_text)
                node = node.parent
                position = end + 11  # the length of the string "#END_PYTHON"

            # General case
            # ------------
            # Exclude #END and all closing tags, since they're not true tags.
            # (Their only purpose is to close a block, #END doesn't correspond to any command).
            elif not self.only_closing(tag):
                # Create and enter new node.
                # ~~~~~~~~~~~~~~~~~~~~~~~~~~
                node = node.add_child(Node(tag))
                # Detect command optional argument.
                # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                try:
                    # - Tolerate spaces before bracket.
                    tmp_pos = position
                    while text[tmp_pos].isspace():
                        tmp_pos += 1
                        if text[tmp_pos] == "[":
                            position = tmp_pos
                    # - Handle optional argument.
                    if text[position] == "[":
                        position += 1
                        end = find_closing_bracket(text, position, brackets="[]")
                        node.options = text[position:end]
                        position = end + 1
                except IndexError:
                    # Don't raise error, since argument is optional.
                    pass

                # Detect command arguments.
                # ~~~~~~~~~~~~~~~~~~~~~~~~~
                # Each argument becomes a node with its number as name.
                try:
                    code_args_number, raw_args_number, closing_tags = self.tags[node.name]
                except ValueError:
                    raise RuntimeError(
                        f"Tag {node.name} is not correctly defined."
                        " This is a problem in pTyX itself, and not in your document."
                        " Please report it."
                    )
                for arg_num in range(code_args_number + raw_args_number):
                    try:
                        # - Tolerate spaces before bracket.
                        while text[position].isspace():
                            position += 1
                        # - Handle argument.
                        if text[position] == "{":
                            position += 1
                            # Detect inner strings for arguments containing code,
                            # but not for arguments containing raw text.
                            end = find_closing_bracket(
                                text,
                                position,
                                brackets="{}",
                                detect_strings=(arg_num < code_args_number),
                            )
                            new_pos = end + 1
                        else:
                            end = position
                            while end < len(text) and (text[end].isalnum() or text[end] == "_"):
                                end += 1
                            new_pos = end
                    except IndexError:
                        raise PtyxSyntaxError("Missing argument for tag %s !" % tag)
                    # Each argument of a command is a node itself.
                    # Nodes corresponding to arguments have no name,
                    # but are numbered instead.
                    arg = node.add_child(Node(arg_num))
                    if arg_num < code_args_number or tag == "PRINT":
                        # Add raw text, do not parse it.
                        arg.add_child(text[position:end].replace("##", "#"))
                    else:
                        # Parse argument as pTyX code.
                        # Note: DON'T replace ## by #, since otherwise it would be done recursively!
                        self._generate_tree(arg, text[position:end])
                    position = new_pos

                # if remove_trailing_newline:
                #   # Remove new line and spaces *after* #IF, #ELSE, ... tags.
                #   # This is more convenient, since two successive \n
                #   # induce a new paragraph in LaTeX.
                #   # So, something like this
                #   #   [some text here]
                #   #   #IF{delta>0}
                #   #   #IF{a>0}
                #   #   [some text there]
                #   #   #END
                #   #   #END
                #   # would automatically result in two paragraphs else.
                #   try:
                #       i = text.index('\n', position) + 1
                #       if text[position:i].isspace():
                #           position = i
                #   except ValueError:
                #       pass

                # Close node if needed.
                # ~~~~~~~~~~~~~~~~~~~~~~~
                if closing_tags is None:
                    # Close node (tag is self-closing).
                    node = node.parent
                else:
                    # Store node closing tags for fast access later.
                    node._closing_tags = closing_tags

        node.add_child(text[last_position:].replace("##", "#"))
