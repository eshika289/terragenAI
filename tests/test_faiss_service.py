import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import faiss
import numpy as np
import pytest

from src.services.vector_store.faiss_store import FaissService


MOCK_EMBEDDING = [0.1] * 1536

SAMPLE_MODULES = [
    {
        "source": "app.terraform.io/my-org/vpc/aws",
        "module_name": "vpc",
        "provider": "aws",
        "version": "1.0.0",
        "vcs_link": "https://github.com/my-org/vpc",
        "variables": [{"name": "region", "required": True}],
    },
    {
        "source": "app.terraform.io/my-org/eks/aws",
        "module_name": "eks",
        "provider": "aws",
        "version": "2.0.0",
        "vcs_link": "https://github.com/my-org/eks",
        "variables": [{"name": "cluster_name", "required": True}],
    },
]


class FakeRegistry:
    TF_ORG = "my-org"


_SENTINEL = object()


def _build_service(tmp_path, monkeypatch, modules=_SENTINEL):
    monkeypatch.setattr(
        "src.services.vector_store.faiss_store.ModuleRegistry", lambda: FakeRegistry()
    )
    monkeypatch.setattr(
        "src.services.vector_store.faiss_store.get_config_dir", lambda: tmp_path
    )
    if modules is _SENTINEL:
        modules = SAMPLE_MODULES

    with patch("src.services.vector_store.faiss_store.OpenAIService") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.create_embedding.return_value = MOCK_EMBEDDING
        mock_llm_cls.return_value = mock_llm

        service = FaissService(modules, config_dir=tmp_path)
        service.llm = mock_llm
        return service


# ------------------------------
# __init__
# ------------------------------

def test_init_creates_directories(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert Path(service.vector_dir).exists()


def test_init_sets_index_path(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert service.index_path.endswith("faiss.index")


def test_init_builds_module_lookup(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert "app.terraform.io/my-org/vpc/aws" in service.module_lookup
    assert "app.terraform.io/my-org/eks/aws" in service.module_lookup


def test_init_faiss_index_is_none(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert service.faiss_index is None


def test_init_empty_modules_inventory(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch, modules=[])
    assert service.module_lookup == {}
    assert service.modules_inventory == []


# ------------------------------
# create_index
# ------------------------------

def test_create_index_builds_faiss_index(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()
    assert service.faiss_index is not None


def test_create_index_populates_module_texts_and_sources(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()
    assert len(service.module_texts) == len(SAMPLE_MODULES)
    assert len(service.module_sources) == len(SAMPLE_MODULES)


def test_create_index_writes_index_to_disk(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()
    assert Path(service.index_path).exists()


def test_create_index_calls_embedding_per_module(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()
    assert service.llm.create_embedding.call_count == len(SAMPLE_MODULES)


def test_create_index_skips_rebuild_when_index_exists(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()
    call_count_after_first = service.llm.create_embedding.call_count

    service.llm.create_embedding.reset_mock()
    service.create_index()

    assert service.llm.create_embedding.call_count == 0


def test_create_index_rebuilds_when_force(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()

    service.llm.create_embedding.reset_mock()
    service.create_index(force=True)

    assert service.llm.create_embedding.call_count == len(SAMPLE_MODULES)


def test_create_index_loads_existing_index_from_disk(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()

    # Reset and reload from disk
    service.faiss_index = None
    service.create_index()

    assert service.faiss_index is not None
    assert len(service.module_sources) == len(SAMPLE_MODULES)


def test_create_index_no_modules_does_not_create_index(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch, modules=[])
    service.create_index()
    assert service.faiss_index is None


# ------------------------------
# retrieve_modules
# ------------------------------

def test_retrieve_modules_returns_empty_when_index_not_initialised(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    result = service.retrieve_modules("create a vpc")
    assert result == []


def test_retrieve_modules_returns_empty_when_module_texts_missing(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.faiss_index = MagicMock()
    service.module_texts = None
    result = service.retrieve_modules("create a vpc")
    assert result == []


def test_retrieve_modules_returns_none_when_embedding_is_empty(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()
    service.llm.create_embedding.return_value = []

    result = service.retrieve_modules("create a vpc")
    assert result is None


def test_retrieve_modules_returns_string(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()

    result = service.retrieve_modules("create a vpc")
    assert isinstance(result, str)


def test_retrieve_modules_returns_valid_json(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()

    result = service.retrieve_modules("create a vpc")
    parsed = json.loads(result)
    assert isinstance(parsed, list)


def test_retrieve_modules_respects_top_k(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.create_index()

    result = service.retrieve_modules("create a vpc", top_k=1)
    parsed = json.loads(result)
    assert len(parsed) <= 1


# ------------------------------
# module_to_embedding_text
# ------------------------------

def test_module_to_embedding_text_contains_expected_fields(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    text = service.module_to_embedding_text(SAMPLE_MODULES[0])
    assert "vpc" in text
    assert "aws" in text
    assert "app.terraform.io/my-org/vpc/aws" in text
    assert "1.0.0" in text
    assert "region" in text


def test_module_to_embedding_text_handles_missing_fields(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    text = service.module_to_embedding_text({})
    assert "N/A" in text


# ------------------------------
# modules_to_string
# ------------------------------

def test_modules_to_string_returns_valid_json(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    result = service.modules_to_string(SAMPLE_MODULES)
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    assert len(parsed) == 2


def test_modules_to_string_includes_expected_keys(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    result = service.modules_to_string(SAMPLE_MODULES)
    parsed = json.loads(result)
    for entry in parsed:
        assert "source" in entry
        assert "version" in entry
        assert "module_name" in entry
        assert "provider" in entry
        assert "variables" in entry
        assert "vcs_link" in entry


def test_modules_to_string_uses_na_for_missing_vcs_link(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    module = {**SAMPLE_MODULES[0]}
    del module["vcs_link"]
    result = service.modules_to_string([module])
    parsed = json.loads(result)
    assert parsed[0]["vcs_link"] == "N/A"


def test_modules_to_string_empty_list(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    result = service.modules_to_string([])
    assert json.loads(result) == []
