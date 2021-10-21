"""
Geophyx

Geophar binding for pTyX.

This extension enables to use geophar drawing inside pTyX files.

To load it, use `#LOAD{geophyx}`.

It adds the following commands to pTyX:

    - #CALC{expr} will calculate expression, using a user friendly syntax.
      Example: #CALC{2x²-x(7x-3)}

    - #GEO
      A = Point(2, 5)
      B = Point(0, 1)
      C = Point(2, 7)
      ABC = Triangle(A, B, C)
      #END_GEO

    - #TABVAL
      code (see Geophar doc.)
      #END_TABVAL

    -


"""

import random
from functools import partial

from wxgeometrie.modules.tablatex import tabval, tabvar, tabsign
from wxgeometrie.mathlib.parsers import traduire_formule
from wxgeometrie.mathlib.interprete import Interprete
from wxgeometrie.geolib import Feuille

from ptyx.config import sympy


# ------------------
#    CUSTOM TAGS
# ------------------

def _parse_CALC_tag(self, node):
    args, kw = self._parse_options(node)
    assert len(args) <= 1 and len(kw) == 0
    name = (args[0] if args else 'RESULT')

    fonctions = [key for key, val in self.context.items()
                 if isinstance(val, (type(sympy.sqrt), type(sympy.cos)))]

    def eval_and_store(txt, name):
        formule = traduire_formule(txt, fonctions=fonctions)
        print('Formule interpretation:', txt, ' → ', formule)
        self.context[name] = self._eval_python_expr(formule)
        return txt

    self._parse_children(node.children[0].children, function=eval_and_store,
                         name=name)


def _parse_GCALC_tag(self, node):
    state = random.getstate()
    args, kw = self._parse_options(node)
    for key in kw:
        kw[key] = eval(kw[key])
    def _eval2latex(code):
        print('code::' + repr(code))
        return Interprete(**kw).evaluer(code.strip())[1]
    self._parse_children(node.children, function=_eval2latex, **kw)
    random.setstate(state)


def _parse_GEO_tag(self, node):
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


def _parse_TABVAL_tag(self, node):
    state = random.getstate()
    args, kw = self._parse_options(node)
    for key in kw:
        kw[key] = eval(kw[key])
    self._parse_children(node.children, function=tabval, **kw)
    random.setstate(state)


def _parse_TABVAR_tag(self, node):
    state = random.getstate()
    args, kw = self._parse_options(node)
    for key in kw:
        kw[key] = eval(kw[key])
    self._parse_children(node.children, function=tabvar, **kw)
    random.setstate(state)


def _parse_TABSIGN_tag(self, node):
    state = random.getstate()
    args, kw = self._parse_options(node)
    for key in kw:
        kw[key] = eval(kw[key])
    self._parse_children(node.children, function=tabsign, **kw)
    random.setstate(state)



def main(code, compiler):
    # Register custom tags and corresponding handlers for this extension.
    new_tag = partial(compiler.add_new_tag, extension_name='autoqcm')

    # Note for closing tags:
    # The arobase before '@END' means closing tag #END must be consumed, unlike 'END'.

    # Tags used to structure MCQ
    new_tag('CALC', (1, 0, None), _parse_CALC_tag)
    new_tag('GCALC', (0, 0, ['@END_GCALC', '@END']), _parse_GCALC_tag)
    new_tag('GEO', (0, 0, ['@END_GEO', '@END']), _parse_GEO_tag)
    new_tag('TABSIGN', (0, 0, ['@END_TABSIGN', '@END']), _parse_TABSIGN_tag)
    new_tag('TABVAL', (0, 0, ['@END_TABVAL', '@END']), _parse_TABVAL_tag)
    new_tag('TABVAR', (0, 0, ['@END_TABVAR', '@END']), _parse_TABVAR_tag)

    # For efficiency, update only once, after last tag is added.
    compiler.update_tags_info()
    # Code is left untouched, this extension only adds new commands.
    return code


