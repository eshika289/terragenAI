import os
import sys
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from ...models.module_registry import ModuleRegistry
from ...paths import get_config_dir
from ..llm.openai import OpenAIService
from .base_store import VectorStoreService


class FaissService(VectorStoreService):
    def __init__(self, modules_inventory, config_dir: Optional[Path] = None):

        self.registry = ModuleRegistry()
        config_root = Path(config_dir) if config_dir else Path(get_config_dir())
        base_dir = config_root / self.registry.TF_ORG
        base_dir.mkdir(parents=True, exist_ok=True)
        self.vector_dir = str(base_dir / "vector_store")
        Path(self.vector_dir).mkdir(parents=True, exist_ok=True)

        self.index_path = str(Path(self.vector_dir) / "faiss.index")

        self.llm = OpenAIService()
        self.faiss_index = None
        self.module_texts = None
        self.module_sources = None
        self.modules_inventory = modules_inventory
        self.module_lookup: dict[str, dict] = {
            m["source"]: m for m in self.modules_inventory
        }

    def create_index(self, force=False):

        if os.path.exists(self.index_path) and not force:

            print("skipping creating faiss index, already found and no --force")

            self.faiss_index = faiss.read_index(self.index_path)

            self.module_texts = []
            self.module_sources = []

            for m in self.modules_inventory:
                text = self.module_to_embedding_text(m)
                self.module_texts.append(text)
                self.module_sources.append(m["source"])

            return self.faiss_index

        # -------- RAG: rebuild embeddings --------
        self.module_texts = []
        self.module_sources = []
        embeddings = []

        for m in self.modules_inventory:
            text = self.module_to_embedding_text(m)
            emb = self.llm.create_embedding(text)

            self.module_texts.append(text)
            self.module_sources.append(m["source"])
            embeddings.append(np.array(emb, dtype="float32"))

        if embeddings:
            self.faiss_index = faiss.IndexFlatL2(len(emb))
            self.faiss_index.add(np.stack(embeddings))

        faiss.write_index(self.faiss_index, self.index_path)

        return self.faiss_index

    def retrieve_modules(self, user_prompt: str, top_k: int = 5) -> list[dict]:
        """
        Retrieve top-K relevant modules using FAISS similarity search.
        """

        if not self.faiss_index or not self.module_texts:
            print("self.faiss_index or self.module_texts not found")
            return []

        query_embedding = self.llm.create_embedding(user_prompt)

        query_vector = np.array(query_embedding, dtype="float32").reshape(1, -1)

        if not query_embedding:
            print("WARNING: Skipping similarity search (dry run)", file=sys.stderr)
            return None
        _, indices = self.faiss_index.search(query_vector, top_k)

        results = []
        for idx in indices[0]:
            if idx < len(self.module_sources):
                source = self.module_sources[idx]
                results.append(self.module_lookup[source])

        return self.modules_to_string(results)
