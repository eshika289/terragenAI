from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = ".terragenai"


def _expand(path_value: str) -> Path:
    return Path(path_value).expanduser().resolve()


def get_config_dir() -> Path:
    override = os.getenv("TERRAGENAI_HOME")
    if override:
        return _expand(override)

    if sys.platform == "darwin":
        return Path.home() / APP_DIR_NAME

    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / APP_DIR_NAME
        return Path.home() / "AppData" / "Roaming" / APP_DIR_NAME

    xdg_config = os.getenv("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "terragenai"
    return Path.home() / ".config" / "terragenai"


def get_state_dir() -> Path:
    override = os.getenv("TERRAGENAI_HOME")
    if override:
        return _expand(override)

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME

    if os.name == "nt":
        localappdata = os.getenv("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / APP_DIR_NAME
        return Path.home() / "AppData" / "Local" / APP_DIR_NAME

    xdg_state = os.getenv("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state) / "terragenai"
    return Path.home() / ".local" / "session" / "terragenai"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
