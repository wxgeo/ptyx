from __future__ import division # 1/2 == .5 (par defaut, 1/2 == 0)

import re
from math import ceil, floor, isnan, isinf

from config import param, sympy, wxgeometrie, custom_latex
if sympy is not None:
    from sympy import preorder_traversal, Symbol

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





def _float_me_if_you_can(expr):
    try:
        return float(expr)
    except:
        return expr

def numbers_to_floats(expr, integers=False, ndigits=None):
    u"""Convert all numbers (except integers) to floats inside a sympy expression."""
    if not sympy or not isinstance(expr, sympy.Basic):
        if isinstance(expr, (long, int)) and not integers:
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
