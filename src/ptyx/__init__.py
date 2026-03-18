from importlib import metadata

# Import ptyx.config first, to set up ptyx !
from ptyx.config import param

__version__ = metadata.version(__package__)
__all__ = ("param", "__version__")
