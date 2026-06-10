"""graph-skill — self-contained interactive HTML visualization generator.

The skill turns *normalized config* (data assets + axis meta + graph-type + background
params) into a *single self-contained .html* rendered by a fixed, version-controlled JS
engine. It is engine-family based: `xy-core` (Canvas 2D) is the first family; future
families (e.g. `cad-viewer` for 3D CAD) sit on the same builder/catalog/validate machinery.

See docs/SKILL-PLAN.md for the full architecture.
"""

from importlib.metadata import PackageNotFoundError, version

try:  # single source of truth — never hardcode __version__
    __version__ = version("graph-skill")
except PackageNotFoundError:  # running from source without install
    __version__ = "0.1.0+src"

__all__ = ["__version__"]
