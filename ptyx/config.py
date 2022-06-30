# mypy: ignore-errors

import os
import sys

try:
    from ptyx.custom_config import param as custom_param
except ImportError:
    custom_param = {}

# <default_configuration>
param = {
    "total": 1,
    "formats": ["pdf", "tex", "tex+pdf", "pdf+tex"],
    "default_formats": "pdf",
    "tex_command": "pdflatex -interaction=nonstopmode --shell-escape --enable-write18",
    "quiet_tex_command": "pdflatex -interaction=batchmode --shell-escape --enable-write18",
    "sympy_is_default": True,
    "import_paths": [],
    "debug": False,
    "floating_point": ",",
    "win_print_command": "SumatraPDF.exe -print-dialog -silent -print-to-default ",
}
# </default_configuration>

# Update parameters using `custom_config.py` param, if any.
param.update(custom_param)


for path in param["import_paths"]:
    path = os.path.normpath(os.path.expanduser(path))
    sys.path.insert(0, path)

# print("Loading sympy...")
try:
    import sympy
except ImportError:
    print("** ERROR: sympy not found ! **")
    sympy = None
    param["sympy_is_default"] = False


# print("Loading numpy...")

try:
    import numpy
except ImportError:
    print("WARNING: numpy not found.")
    numpy = None
