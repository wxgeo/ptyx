"""
Geophyx

Geophar binding for pTyX.

This extension enables to use geophar drawing inside pTyX files.

To load it, use `#LOAD{geoptyx}`.

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

# mypy: ignore-errors

import random

from ptyx.extensions import CompilerExtension
from wxgeometrie.modules.tablatex import tabval, tabvar, tabsign
from wxgeometrie.mathlib.parsers import traduire_formule
from wxgeometrie.mathlib.interprete import Interprete
from wxgeometrie.geolib import Feuille

import sympy
from ptyx.latex_generator import LatexGenerator


# ------------------
#    CUSTOM TAGS
# ------------------


class GeophyxLatexGenerator(LatexGenerator):
    def _parse_CALC_tag(self, node):
        args, kw = self._parse_options(node)
        assert len(args) <= 1 and len(kw) == 0
        name = args[0] if args else "RESULT"

        fonctions = [
            key for key, val in self.context.items() if isinstance(val, (type(sympy.sqrt), type(sympy.cos)))
        ]

        def eval_and_store(txt, name):
            formule = traduire_formule(txt, fonctions=fonctions)
            print("Formule interpretation:", txt, " → ", formule)
            self.context[name] = self._eval_python_expr(formule)
            return txt

        self._parse_children(node.children[0].children, function=eval_and_store, name=name)

    def _parse_GCALC_tag(self, node):
        state = random.getstate()
        args, kw = self._parse_options(node)
        for key in kw:
            kw[key] = eval(kw[key])

        def _eval2latex(code):
            print("code::" + repr(code))
            return Interprete(**kw).evaluer(code.strip())[1]

        self._parse_children(node.children, function=_eval2latex, **kw)
        random.setstate(state)

    def _parse_GEO_tag(self, node):
        state = random.getstate()
        args, kw = self._parse_options(node)
        scale = kw.pop("scale", None)
        for key in kw:
            kw[key] = eval(kw[key])

        def _eval2latex(code):
            print("code::" + repr(code))
            feuille = Feuille(**kw)
            for commande in code.split("\n"):
                feuille.executer(commande)
            return feuille.exporter("tikz", echelle=scale)

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


def extend_compiler() -> CompilerExtension:
    """Function called by the compiler when loading this extension, to add ability to parse new tags."""
    tags = {
        "CALC": (1, 0, None),
        "GCALC": (0, 0, ["@END_GCALC", "@END"]),
        "GEO": (0, 0, ["@END_GEO", "@END"]),
        "TABSIGN": (0, 0, ["@END_TABSIGN", "@END"]),
        "TABVAL": (0, 0, ["@END_TABVAL", "@END"]),
        "TABVAR": (0, 0, ["@END_TABVAR", "@END"]),
    }
    return {"latex_generator": GeophyxLatexGenerator, "tags": tags}


def main(code, compiler):
    # Code is left untouched, this extension only adds new commands.
    return code
