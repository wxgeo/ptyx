from os.path import dirname

from ptyx.latex_generator import Compiler


TEST_DIR = dirname(__file__)


def parse(code: str, **kw) -> str:
    """Convert pTyX code to plain LaTeX."""
    return Compiler().parse(code=code, **kw)
