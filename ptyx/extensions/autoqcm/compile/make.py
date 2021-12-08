"""
Generate pdf file from raw autoqcm file.
"""

from pathlib import Path

from ptyx.compilation import make_files
from ptyx.latexgenerator import compiler


def make(pth: str = '.', num: int = 1) -> None:
    """Implement `autoqcm make` command.
    """
    pth = Path(pth).resolve()
    if pth.suffix != ".ptyx":
        ptyx_files = list(pth.glob("*.ptyx"))
    if len(ptyx_file) == 0:
        raise FileNotFoundError(f"No .ptyx file found in '{pth}'.")
    elif len(ptyx_file) > 1:
        raise FileNotFoundError(f"Several .ptyx file found in '{pth}', I don't know which to chose.")
    ptyx_file = ptyx_files[0]
    compiler.read_file(ptyx_file)
    compiler.preparse()
    #
    raise NotImplementedError
