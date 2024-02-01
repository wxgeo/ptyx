"""
A variant of sympy latex printer, based on wxgeometrie one.
"""
from ptyx.internal_types import EvalFlags


# TODO: Clean-up unused wxgeometrie code !
# TODO: This module needs lot's of cleaning and refactoring.

# try:
#     import sympy
#     from sympy import Basic, Symbol, Integer, Float, I, Mul
#     from sympy.core.core import BasicMeta
#     from sympy.printing.latex import LatexPrinter
# except ImportError:
#     print("Warning: `sympy` library not found !")
#     sympy = None  # type: ignore

import sympy
from sympy import Basic, Symbol, Integer, Float, I, Mul
from sympy.printing.latex import LatexPrinter

from ptyx.config import param


class CustomLatexPrinter(LatexPrinter):
    def __init__(self, settings):
        defaults = {
            "decimales": 18,
            "mat_str": "pmatrix",
            "mat_delim": "",
            "mode": "inline",
            "fold_frac_powers": False,
            "fold_short_frac": False,
        }
        self._default_settings.update(defaults)
        LatexPrinter.__init__(self, settings)

    def _print(self, expr, *args, **kwargs):
        """Change sympy printing algorithm.
        Instead of first searching if the object has a ._latex() method,
        we start by searching if a _print_ObjectClass() exist in the printer.

        This makes it easier to customize sympy objects latex printing.

        So, tries the following concepts to print an expression:
            1. Take the best fitting method defined in the printer.
            2. Let the object print itself if it knows how.
            3. As fall-back use the emptyPrinter method for the printer.
        """
        self._print_level += 1
        try:
            # See if the class of expr is known, or if one of its super
            # classes is known, and use that print function
            for cls in type(expr).__mro__:
                printmethod = "_print_" + cls.__name__
                if hasattr(self, printmethod):
                    return getattr(self, printmethod)(expr, *args, **kwargs)

            # If the printer defines a name for a printing method
            # (Printer.printmethod) and the object knows for itself how it
            # should be printed, use that method.
            if self.printmethod and hasattr(expr, self.printmethod):
                return getattr(expr, self.printmethod)(self, *args, **kwargs)

            # Avoid new (strange) behaviour of sympy 1.7+
            if isinstance(expr, str):
                return expr
            # Unknown object, fall back to the emptyPrinter.
            return self.emptyPrinter(expr)
        finally:
            self._print_level -= 1

    def _print_exp(self, expr, exp=None):
        tex = r"\mathrm{e}^{%s}" % self._print(expr.args[0])
        return self._do_exponent(tex, exp)

    def _print_Exp1(self, expr, exp=None):
        return r"\mathrm{e}"

    def _print_Abs(self, *args, **kw):
        res = LatexPrinter._print_Abs(self, *args, **kw)
        return res.replace(r"\lvert", r"|").replace(r"\rvert", r"|")

    def _print_Pi(self, *args, **kw):
        return r"\pi"

    def _print_ImaginaryUnit(self, expr):
        return r"\mathrm{i}"

    def _print_Function(self, expr, exp=None):
        func = expr.func.__name__

        if hasattr(self, "_print_" + func):
            return getattr(self, "_print_" + func)(expr, exp)

        else:
            if exp is not None:
                name = r"\mathrm{%s}^{%s}" % (func, exp)
            else:
                name = r"\mathrm{%s}" % func
            if len(expr.args) == 1 and isinstance(expr.args[0], (Symbol, Integer)):
                return name + "(" + str(self._print(expr.args[0])) + ")"
            else:
                args = [str(self._print(arg)) for arg in expr.args]
                return name + r"\left(%s\right)" % ",".join(args)

    #    def _print_Float(self, expr):
    #        s = LatexPrinter._print_Float(self, expr)
    #        if s.startswith(r'1.0 \times '):  # sympy 0.7.3
    #            return s[11:]
    #        elif s.startswith(r'1.0 \cdot '):  # sympy 0.7.5
    #            return s[10:]
    #        elif r'\times' not in s:
    #            # Ne pas supprimer un zéro de la puissance !
    #            s = s.rstrip('0').rstrip('.')
    #        return s

    def _print_Infinity(self, expr):
        return r"+\infty"

    def _print_Order(self, expr):
        return r"\mathcal{O}\left(%s\right)" % self._print(expr.args[0])

    def _print_Mul(self, expr):
        args = expr.args
        if args[-1] is I:
            if len(args) == 2 and args[0] == -1:
                return LatexPrinter._print_Mul(self, expr)
            return "%s %s" % (self._print(Mul(*args[:-1])), self._print(I))
        return LatexPrinter._print_Mul(self, expr)
        # return ' '.join(self._print(arg) for arg in expr.args)

    def _print_set(self, expr):
        if expr:
            return r"\left\{%s\right\}" % r"\,;\,".join(self._print(val) for val in expr)
        return r"\emptyset"

    def _print_tuple(self, expr):
        return r"\left(%s\right)" % r",\,".join(self._print(item) for item in expr)

    def _print_log(self, expr, exp=None):
        if len(expr.args) == 1 and isinstance(expr.args[0], (Symbol, Integer)):
            tex = r"\ln(%s)" % self._print(expr.args[0])
        else:
            tex = r"\ln\left(%s\right)" % self._print(expr.args[0])
        return self._do_exponent(tex, exp)

    def _print_function(self, expr):
        return r"\mathrm{Fonction}\, " + expr.__name__

    def doprint(self, expr):
        tex = LatexPrinter.doprint(self, expr)
        return tex.replace(r"\operatorname{", r"\mathrm{")


def custom_latex(expr, **settings):
    """Convert expression to LaTeX code."""
    if sympy is None:
        return str(expr)
    return CustomLatexPrinter(settings).doprint(expr)


def sympy2latex(expr, flags: EvalFlags = None, **sympy_flags) -> str:
    """Convert a sympy expression to LaTeX code."""
    if flags is None:
        flags = EvalFlags()

    if flags.format_as_str:
        latex = str(expr)
    elif isinstance(expr, float) or (sympy and isinstance(expr, Float)) or flags.keep_dot_as_decimal_mark:
        # -0.06000000000000001 means probably -0.06 ; that's because
        # floating point arithmetic is not based on decimal numbers, and
        # so some decimal numbers do not have exact internal representation.
        # Python str() handles this better than sympy.latex().
        # Keep 'only' 14 digits (precision rarely  exceed 16 or 17 digits with raw floats,
        # and then decreased with successive operations...)
        latex = format(float(expr), ".14g")
        if latex == "-0":
            latex = "0"
    else:
        sympy_flags = {"mode": "plain"} | sympy_flags
        latex = custom_latex(expr, **sympy_flags)

    if isinstance(expr, float) or (sympy and isinstance(expr, Basic)):
        # In french, german... a comma is used as floating point.
        # However, if `float` flag is set, floating point is left unchanged
        # (useful for Tikz for example).
        if not flags.keep_dot_as_decimal_mark:
            # It would be much better to subclass sympy LaTeX printer
            latex = latex.replace(".", param["floating_point"])

    # TODO: subclass sympy LaTeX printer (cf. mathlib in wxgeometrie)
    latex = latex.replace(r"\operatorname{log}", r"\operatorname{ln}")
    return latex
