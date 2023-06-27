from importlib import metadata

# Import ptyx.config first, to set up ptyx !
from ptyx.config import param

__version__ = metadata.version(__package__)
# __version__ = "23.3.0"
__all__ = ("param", "__version__")
