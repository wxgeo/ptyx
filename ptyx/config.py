# mypy: ignore-errors

import os
import sys
import importlib.util

import psutil

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


SYMPY_AVAILABLE = importlib.util.find_spec("sympy") is not None
NUMPY_AVAILABLE = importlib.util.find_spec("numpy") is not None

if not SYMPY_AVAILABLE:
    print("** ERROR: sympy not found ! **")
    param["sympy_is_default"] = False

if not NUMPY_AVAILABLE:
    print("WARNING: numpy not found.")

try:
    CPU_PHYSICAL_CORES = psutil.cpu_count(logical=False)
except ImportError:
    CPU_PHYSICAL_CORES = (os.cpu_count() or 1) // 2
if not CPU_PHYSICAL_CORES:
    CPU_PHYSICAL_CORES = 1
