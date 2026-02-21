import pytest

from src.models import module_registry


def test_module_registry_loads_config_and_computed_fields(monkeypatch):
    monkeypatch.setattr(
        module_registry,
        "load_config",
        lambda: {
            "TF_ORG": "my-org",
            "TF_REGISTRY_DOMAIN": "tfe.example.com",
            "TF_API_TOKEN": "token-123",
            "GIT_CLONE_TOKEN": "git-456",
        },
    )

    registry = module_registry.ModuleRegistry()

    assert registry.TF_ORG == "my-org"
    assert registry.TF_REGISTRY_DOMAIN == "tfe.example.com"
    assert registry.TF_API_TOKEN == "token-123"
    assert registry.GIT_CLONE_TOKEN == "git-456"
    assert registry.IS_TFE is True
    assert registry.TF_BASE_URL == "https://tfe.example.com/api/v2"
    assert (
        registry.TF_REGISTRY_MODULES_URL
        == "https://tfe.example.com/api/v2/organizations/my-org/registry-modules"
    )
    assert registry.TF_HEADERS["Authorization"] == "Bearer token-123"


def test_module_registry_defaults_registry_domain(monkeypatch):
    monkeypatch.setattr(
        module_registry,
        "load_config",
        lambda: {"TF_ORG": "my-org", "TF_API_TOKEN": "token-123"},
    )

    registry = module_registry.ModuleRegistry()

    assert registry.TF_REGISTRY_DOMAIN == "app.terraform.io"
    assert registry.IS_TFE is False


@pytest.mark.parametrize(
    "cfg,missing_key",
    [
        ({"TF_API_TOKEN": "token-123"}, "TF_ORG"),
        ({"TF_ORG": "my-org"}, "TF_API_TOKEN"),
    ],
)
def test_module_registry_validate_missing_required(monkeypatch, cfg, missing_key):
    monkeypatch.setattr(module_registry, "load_config", lambda: cfg)

    with pytest.raises(ValueError) as exc:
        module_registry.ModuleRegistry()

    assert missing_key in str(exc.value)
