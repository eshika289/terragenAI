from __future__ import annotations

import json
import os
from pathlib import Path

from .paths import ensure_dir, get_config_dir


def get_config_file() -> Path:
    configured = os.getenv("TERRAGENAI_CONFIG_FILE")
    if configured:
        return Path(configured).expanduser()
    return get_config_dir() / ".terragenairc"


def load_config() -> dict:
    config_file = get_config_file()
    if not config_file.exists():
        return {}
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    config_file = get_config_file()
    ensure_dir(config_file.parent)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
