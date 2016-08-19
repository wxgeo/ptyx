
import os, sys

# <default_configuration>
param = {
        'total': 1,
        'format': ['pdf', 'tex'],
        'tex_command': 'pdflatex -interaction=nonstopmode --shell-escape --enable-write18',
        'quiet_tex_command': 'pdflatex -interaction=batchmode --shell-escape --enable-write18',
        'sympy_is_default': True,
        'sympy_path': None,
        'wxgeometrie': None,
        'wxgeometrie_path': None,
        'debug': False,
        'floating_point': ',',
        'win_print_command': 'SumatraPDF.exe -print-dialog -silent -print-to-default ',
        }
# </default_configuration>

# <personnal_configuration>
param['sympy_path'] = '~/Dropbox/Programmation/wxgeometrie/wxgeometrie'
param['wxgeometrie_path'] = '~/Dropbox/Programmation/wxgeometrie'
# </personnal_configuration>

for pathname in ('sympy_path', 'wxgeometrie_path'):
    path = param[pathname]
    if path is not None:
        path = os.path.normpath(os.path.expanduser(path))
        sys.path.insert(0, path)
        param[pathname] = path

print("Loading sympy...")
try:
    import sympy
except ImportError:
    print("** ERROR: sympy not found ! **")
    sympy = None
    param['sympy_is_default'] = False
    import latexgenerator
    latexgenerator.sympy = sympy

print("Loading geophar...")

try:
    import wxgeometrie
    try:
        #~ from wxgeometrie.modules import tablatex
        from wxgeometrie.mathlib.printers import custom_latex
    except ImportError:
        print("WARNING: current geophar version is not compatible.")
        raise
except ImportError:
    print("WARNING: geophar not found.")
    wxgeometrie = None
    custom_latex = None

print("Loading numpy...")

try:
    import numpy
except ImportError:
    print("WARNING: numpy not found.")
    numpy = None

