from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib

__all__ = ["__version__"]

try:
    __version__ = version("terragenai")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
