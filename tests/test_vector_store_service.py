import json

import pytest

from src.services.vector_store.base_store import VectorStoreService


# Minimal concrete implementation to allow instantiation
class ConcreteVectorStoreService(VectorStoreService):
    def create_index(self, force: bool = False):
        pass

    def retrieve_modules(self, user_prompt: str, top_k: int = 5) -> list[dict]:
        pass


@pytest.fixture
def service():
    return ConcreteVectorStoreService()


FULL_MODULE = {
    "source": "app.terraform.io/my-org/vpc/aws",
    "module_name": "vpc",
    "provider": "aws",
    "version": "1.0.0",
    "vcs_link": "https://github.com/my-org/vpc",
    "variables": [{"name": "region", "required": True}],
}


# ------------------------------
# Abstract interface
# ------------------------------

def test_cannot_instantiate_abstract_class():
    with pytest.raises(TypeError):
        VectorStoreService()


def test_concrete_subclass_missing_create_index_raises():
    class Incomplete(VectorStoreService):
        def retrieve_modules(self, user_prompt, top_k=5):
            pass

    with pytest.raises(TypeError):
        Incomplete()


def test_concrete_subclass_missing_retrieve_modules_raises():
    class Incomplete(VectorStoreService):
        def create_index(self, force=False):
            pass

    with pytest.raises(TypeError):
        Incomplete()


# ------------------------------
# module_to_embedding_text
# ------------------------------

def test_module_to_embedding_text_contains_all_fields(service):
    text = service.module_to_embedding_text(FULL_MODULE)
    assert "vpc" in text
    assert "aws" in text
    assert "app.terraform.io/my-org/vpc/aws" in text
    assert "1.0.0" in text
    assert "https://github.com/my-org/vpc" in text
    assert "region" in text


def test_module_to_embedding_text_returns_string(service):
    result = service.module_to_embedding_text(FULL_MODULE)
    assert isinstance(result, str)


def test_module_to_embedding_text_uses_na_for_missing_fields(service):
    text = service.module_to_embedding_text({})
    assert text.count("N/A") == 5  # module_name, provider, source, version, vcs_link


def test_module_to_embedding_text_partial_fields(service):
    text = service.module_to_embedding_text({"module_name": "eks", "provider": "aws"})
    assert "eks" in text
    assert "aws" in text
    assert "N/A" in text  # remaining missing fields


def test_module_to_embedding_text_empty_variables(service):
    module = {**FULL_MODULE, "variables": []}
    text = service.module_to_embedding_text(module)
    assert "Variables:" in text
    assert "[]" in text


def test_module_to_embedding_text_is_stripped(service):
    text = service.module_to_embedding_text(FULL_MODULE)
    assert text == text.strip()


def test_module_to_embedding_text_variables_as_json(service):
    text = service.module_to_embedding_text(FULL_MODULE)
    # variables block should be valid json embedded in the text
    variables_section = text.split("Variables:")[1].strip()
    parsed = json.loads(variables_section)
    assert isinstance(parsed, list)


# ------------------------------
# modules_to_string
# ------------------------------

def test_modules_to_string_returns_valid_json(service):
    result = service.modules_to_string([FULL_MODULE])
    parsed = json.loads(result)
    assert isinstance(parsed, list)


def test_modules_to_string_returns_string(service):
    result = service.modules_to_string([FULL_MODULE])
    assert isinstance(result, str)


def test_modules_to_string_contains_expected_keys(service):
    result = service.modules_to_string([FULL_MODULE])
    parsed = json.loads(result)
    for entry in parsed:
        assert "source" in entry
        assert "version" in entry
        assert "module_name" in entry
        assert "provider" in entry
        assert "variables" in entry
        assert "vcs_link" in entry


def test_modules_to_string_correct_values(service):
    result = service.modules_to_string([FULL_MODULE])
    parsed = json.loads(result)
    assert parsed[0]["source"] == "app.terraform.io/my-org/vpc/aws"
    assert parsed[0]["module_name"] == "vpc"
    assert parsed[0]["provider"] == "aws"
    assert parsed[0]["version"] == "1.0.0"


def test_modules_to_string_uses_na_for_missing_vcs_link(service):
    module = {k: v for k, v in FULL_MODULE.items() if k != "vcs_link"}
    result = service.modules_to_string([module])
    parsed = json.loads(result)
    assert parsed[0]["vcs_link"] == "N/A"


def test_modules_to_string_empty_list(service):
    result = service.modules_to_string([])
    assert json.loads(result) == []


def test_modules_to_string_multiple_modules(service):
    second = {**FULL_MODULE, "source": "app.terraform.io/my-org/eks/aws", "module_name": "eks"}
    result = service.modules_to_string([FULL_MODULE, second])
    parsed = json.loads(result)
    assert len(parsed) == 2
    assert parsed[1]["module_name"] == "eks"