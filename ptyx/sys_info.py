# mypy: ignore-errors

from importlib.util import find_spec
import os
import sys

import psutil

from ptyx.config import param


for path in param["import_paths"]:
    path = os.path.normpath(os.path.expanduser(path))
    sys.path.insert(0, path)


SYMPY_AVAILABLE = find_spec("sympy") is not None
NUMPY_AVAILABLE = find_spec("numpy") is not None

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
