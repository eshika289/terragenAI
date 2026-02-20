from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib

__all__ = ["__version__"]

pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
if pyproject_path.exists():
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        __version__ = data["project"]["version"]
    except Exception:
        __version__ = "0.0.0+dev"
else:
    try:
        __version__ = version("terragenai")
    except PackageNotFoundError:
        __version__ = "0.0.0+dev"
