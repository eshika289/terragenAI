import json
import os
from pathlib import Path
import uuid

from ...paths import ensure_dir, get_state_dir

class SessionService():
    def __init__(self):
        self.session_file = get_state_dir() / f"session_{uuid.uuid4()}.json"


    def load_session(self) -> list[dict]:
        if self.session_file.exists():
            with open(self.session_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_session(self, session: list[dict]) -> None:
        ensure_dir(self.session_file.parent)
        with open(self.session_file, "w", encoding="utf-8") as f:
            json.dump(session, f)


    def add_message(self, session: list[dict], role: str, content: str) -> None:
        session.append({"role": role, "content": content})
        self.save_session(session)

    def clear_session(self):
        ensure_dir(self.session_file.parent)
        if self.session_file.exists():
            os.remove(self.session_file)

