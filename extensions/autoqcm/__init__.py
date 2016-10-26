"""
AutoQCM

This extension enables computer corrected tests.

An example:

    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    ======= Mathematics ===========

    * 1+1 =
    - 1
    + 2
    - 3
    - 4

    - an other answer

    ======= Litterature ==========

    * "to be or not to be", but who actually wrote that ?
    + W. Shakespeare
    - I. Newton
    - W. Churchill
    - Queen Victoria
    - Some bloody idiot

    * Jean de la Fontaine was a famous french
    - pop singer
    - dancer
    + writer
    - detective
    - cheese maker

    > his son is also famous for
    - dancing french cancan
    - conquering Honolulu
    - walking for the first time on the moon
    - having breakfast at Tiffany

    + none of the above is correct

    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


One may include some PTYX code of course.

#NEW INT(2,10) a, b, c, d WITH a*b - c*d != 0


    """

from .generate import generate_tex
from latexgenerator import Node
import randfunc

class AutoQCMTags(object):
    def _parse_SHUFFLE_QUESTIONS_tag(self, node):
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

    def _parse_SHUFFLE_ANSWERS_tag(self, node):
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

    def _parse_SHUFFLE_QCM_tag(self, node):
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

    def _parse_ITEM_tag(self, node):
        self._parse_children(node.children)


def main(text, compiler):
    code = generate_tex(text)
    syntax = compiler.syntax_tree_generator.tags['SHUFFLE']
    # For efficiency, update only for last tag.
    compiler.add_new_tag('SHUFFLE_QUESTIONS', syntax, AutoQCMTags._parse_SHUFFLE_QUESTIONS_tag, 'autoqcm', update=False)
    compiler.add_new_tag('SHUFFLE_ANSWERS', syntax, AutoQCMTags._parse_SHUFFLE_ANSWERS_tag, 'autoqcm', update=False)
    compiler.add_new_tag('SHUFFLE_QCM', syntax, AutoQCMTags._parse_SHUFFLE_QCM_tag, 'autoqcm')
    return code


