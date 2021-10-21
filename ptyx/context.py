import random, math

import numpy

import ptyx.randfunc as randfunc
from ptyx.printers import sympy2latex
from ptyx.config import sympy

if sympy is not None:
    from sympy import sympify, SympifyError
else:
    SympifyError = None
    sympy = None
    print("I couldn't find sympy...  doing my best without it.")

class SpecialDict(dict):
    auto_sympify = False
    op_mode = None

    def __setitem__(self, key, value):
        if self.auto_sympify:
            try:
                value = sympify(value)
            except SympifyError:
                print('Warning: sympy error. Switching to standard evaluation mode.')
        dict.__setitem__(self, key, value)

    def copy(self):
        return SpecialDict(dict.copy(self))


global_context = SpecialDict()

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
global_context['ceil'] = (global_context['ceiling'] if sympy is not None
                          else math.ceil)
global_context['float'] = float
global_context['int'] = int
global_context['str'] = str

randfuncs = ('randpoint', 'srandpoint', 'randint', 'randbool',
             'srandint', 'randsign', 'randfrac',
             'srandfrac', 'randfloat', 'srandfloat', 'randchoice',
             'srandchoice', 'randmatrix', 'randpop', 'shuffle', 'many',
             'distinct', '_print_state')
for fname in randfuncs:
    global_context[fname] = getattr(randfunc, fname)
# If a document is compiled several times (to produce different versions of the same document),
# NUM is the compilation number (starting from 0).
global_context['NUM'] = 0
global_context['latex'] = sympy2latex

