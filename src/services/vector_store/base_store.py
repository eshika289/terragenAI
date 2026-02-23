import json
import textwrap
from abc import ABC, abstractmethod


class VectorStoreService(ABC):

    @abstractmethod
    def create_index(self, force: bool = False):
        pass

    @abstractmethod
    def retrieve_modules(self, user_prompt: str, top_k: int = 5) -> list[dict]:
        pass

    # ======================================================
    # Embedding helpers
    # ======================================================
    def module_to_embedding_text(self, m: dict) -> str:
        module_name = m.get("module_name", "N/A")
        provider = m.get("provider", "N/A")
        source = m.get("source", "N/A")
        version = m.get("version", "N/A")
        vcs_link = m.get("vcs_link", "N/A")
        variables_json = json.dumps(
            m.get("variables", {}), indent=2, ensure_ascii=False
        )

        return textwrap.dedent(f"""
            Module name: {module_name}
            Provider: {provider}
            Source: {source}
            Version: {version}
            VCS Link: {vcs_link}
            Variables:
            {variables_json}
            """).strip()

    def modules_to_string(self, retrieved_modules: list[dict]) -> str:
        return json.dumps(
            [
                {
                    "source": m["source"],
                    "version": m["version"],
                    "module_name": m["module_name"],
                    "provider": m["provider"],
                    "variables": m["variables"],
                    "vcs_link": m.get("vcs_link", "N/A"),
                }
                for m in retrieved_modules
            ],
            indent=2,
        )
