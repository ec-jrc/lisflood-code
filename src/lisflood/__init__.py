import os

# Version is managed by setuptools_scm and written to _version.py at build time
# (see pyproject.toml [tool.setuptools_scm]). The file is not tracked in git.
try:
    from ._version import __version__
except ImportError:
    # Not built yet (e.g. running from a fresh git checkout). Derive the
    # version live from git; fall back to a sentinel if that also fails.
    try:
        from setuptools_scm import get_version
        __version__ = get_version(root=os.path.join(os.path.dirname(__file__), '../..'))
    except Exception:
        __version__ = '0.0.0'

__authors__ = "Ad de Roo, Emiliano Gelati, Peter Burek, Johan van der Knijff"
__date__ = "30/06/2026"
__copyright__ = "Copyright 2019-2026, European Commission - Joint Research Centre"
__maintainer__ = "Stefania Grimaldi, Timo Schaffhauser, Carlo Russo, Cinzia Mazzetti, Corentin Carton De Wiart"
__status__ = "Operation"
__institution__ = "European Commission DG Joint Research Centre (JRC) - E1, D2 Units"
