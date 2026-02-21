import json

from src.services.registry import base


class FakeRegistry:
    TF_ORG = "my-org"
    TF_REGISTRY_DOMAIN = "app.terraform.io"
    TF_API_TOKEN = "token-123"
    GIT_CLONE_TOKEN = ""
    TF_HEADERS = {"Authorization": "Bearer token-123"}
    TF_REGISTRY_MODULES_URL = (
        "https://app.terraform.io/api/v2/organizations/my-org/registry-modules"
    )


def _build_service(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "ModuleRegistry", lambda: FakeRegistry())
    monkeypatch.setattr(base, "get_config_dir", lambda: tmp_path)
    return base.ModuleRegistryService()


def test_service_initializes_paths(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    assert service.repo_dir == str(tmp_path / "my-org" / "registry-repos")
    assert service.catalog_dir == str(tmp_path / "my-org" / "catalog")
    assert service.catalog_path == str(tmp_path / "my-org" / "catalog" / "modules.json")


def test_validate_catalog(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    assert service.validate_catalog() is False

    (tmp_path / "my-org" / "catalog").mkdir(parents=True, exist_ok=True)
    with open(service.catalog_path, "w", encoding="utf-8") as f:
        f.write("{}")

    assert service.validate_catalog() is True


def test_list_registry_modules_follows_pagination(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    pages = [
        {
            "data": [{"id": "1"}],
            "links": {"next": "https://example.com/page-2"},
        },
        {
            "data": [{"id": "2"}],
            "links": {"next": None},
        },
    ]
    calls = {"count": 0}

    def fake_get(_url):
        idx = calls["count"]
        calls["count"] += 1
        return pages[idx]

    monkeypatch.setattr(service, "_http_get", fake_get)

    modules = service._list_registry_modules()

    assert modules == [{"id": "1"}, {"id": "2"}]
    assert calls["count"] == 2


def test_git_clone_repo_uses_clone_token(tmp_path, monkeypatch):
    class FakeRegistryWithToken(FakeRegistry):
        GIT_CLONE_TOKEN = "git-token"

    monkeypatch.setattr(base, "ModuleRegistry", lambda: FakeRegistryWithToken())
    monkeypatch.setattr(base, "get_config_dir", lambda: tmp_path)
    service = base.ModuleRegistryService()

    called = {}

    def fake_run(cmd, check):
        called["cmd"] = cmd
        called["check"] = check

    monkeypatch.setattr(base.subprocess, "run", fake_run)
    service._git_clone_repo("https://github.com/example/repo.git")

    assert called["check"] is True
    assert called["cmd"][0:3] == ["git", "clone", "--quiet"]
    assert called["cmd"][3].startswith("https://git-token@github.com/")


def test_build_catalog_writes_modules_json(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    monkeypatch.setattr(
        service,
        "_list_registry_modules",
        lambda: [
            {
                "attributes": {
                    "name": "vpc",
                    "namespace": "my-org",
                    "provider": "aws",
                    "vcs-repo": {
                        "repository-http-url": "https://github.com/example/vpc.git"
                    },
                    "version-statuses": [{"version": "1.0.0"}],
                }
            }
        ],
    )
    monkeypatch.setattr(service, "_git_clone_repo", lambda _repo_url: None)
    monkeypatch.setattr(service, "_git_checkout_tag", lambda _tag: None)
    monkeypatch.setattr(
        service, "_parse_tf_variables", lambda: [{"name": "region", "required": True}]
    )
    monkeypatch.setattr(service, "_list_repo_files", lambda: ["main.tf"])
    monkeypatch.setattr(base.shutil, "rmtree", lambda _path: None)

    service.build_catalog()

    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    repo_key = "https://github.com/example/vpc.git"
    assert repo_key in data
    assert "v1.0.0" in data[repo_key]
    assert data[repo_key]["v1.0.0"]["source"] == "app.terraform.io/my-org/vpc/aws"
