import json
import os
from pathlib import Path

from .paths import ensure_dir, get_state_dir


def get_history_file() -> Path:
    configured = os.getenv("TERRAGENAI_HISTORY_FILE")
    if configured:
        return Path(configured).expanduser()
    return get_state_dir() / "history.json"


def load_history() -> list[dict]:
    history_file = get_history_file()
    if history_file.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history: list[dict]) -> None:
    history_file = get_history_file()
    ensure_dir(history_file.parent)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f)


def add_message(history: list[dict], role: str, content: str) -> None:
    history.append({"role": role, "content": content})
    save_history(history)
