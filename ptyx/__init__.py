from importlib import metadata

# Import ptyx.config first, to set up ptyx !
from ptyx.config import param

__version__ = metadata.version(__package__)
__all__ = ("param", "__version__")

# TODO: remove the following.
# Release date isn't useful, and release number should be enough to indicate API change.

# API major version number changes only when backward compatibility is broken.
# API minor version number changes when functionalities are added.
__api__ = "5.2"
__release_date__ = (9, 2, 2022)
