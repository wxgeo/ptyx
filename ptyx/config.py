from ptyx.internal_types import ParamDict

try:
    from ptyx.custom_config import param as custom_param
except ImportError:
    custom_param = {}


# <default_configuration>
param: ParamDict = {
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
