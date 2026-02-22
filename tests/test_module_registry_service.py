import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

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


# ------------------------------
# _normalize_tag
# ------------------------------


def test_normalize_tag_adds_v_prefix(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert service._normalize_tag("1.2.3") == "v1.2.3"


def test_normalize_tag_preserves_existing_v_prefix(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert service._normalize_tag("v1.2.3") == "v1.2.3"


def test_normalize_tag_returns_none_for_falsy(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert service._normalize_tag(None) is None
    assert service._normalize_tag("") is None
    assert service._normalize_tag(0) is None


# ------------------------------
# _clone_url
# ------------------------------


def test_clone_url_no_token_unchanged(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    url = "https://github.com/example/repo.git"
    assert service._clone_url(url) == url


def test_clone_url_injects_token_https(tmp_path, monkeypatch):
    class FakeRegistryWithToken(FakeRegistry):
        GIT_CLONE_TOKEN = "mytoken"

    monkeypatch.setattr(base, "ModuleRegistry", lambda: FakeRegistryWithToken())
    monkeypatch.setattr(base, "get_config_dir", lambda: tmp_path)
    service = base.ModuleRegistryService()

    result = service._clone_url("https://github.com/example/repo.git")
    assert result == "https://mytoken@github.com/example/repo.git"


def test_clone_url_injects_token_http(tmp_path, monkeypatch):
    class FakeRegistryWithToken(FakeRegistry):
        GIT_CLONE_TOKEN = "mytoken"

    monkeypatch.setattr(base, "ModuleRegistry", lambda: FakeRegistryWithToken())
    monkeypatch.setattr(base, "get_config_dir", lambda: tmp_path)
    service = base.ModuleRegistryService()

    result = service._clone_url("http://github.com/example/repo.git")
    assert result == "http://mytoken@github.com/example/repo.git"


# ------------------------------
# _http_get
# ------------------------------


def test_http_get_returns_json_on_success(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": []}
    mock_resp.raise_for_status.return_value = None
    service.session.get = MagicMock(return_value=mock_resp)

    result = service._http_get("https://example.com/api")
    assert result == {"data": []}
    service.session.get.assert_called_once()


def test_http_get_retries_and_raises_on_failure(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    service.session.get = MagicMock(side_effect=requests.RequestException("timeout"))

    with pytest.raises(requests.RequestException):
        service._http_get("https://example.com/api")

    assert service.session.get.call_count == 3


def test_http_get_succeeds_after_retry(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": ["ok"]}
    mock_resp.raise_for_status.return_value = None

    service.session.get = MagicMock(
        side_effect=[requests.RequestException("fail"), mock_resp]
    )

    result = service._http_get("https://example.com/api")
    assert result == {"data": ["ok"]}
    assert service.session.get.call_count == 2


# ------------------------------
# _list_registry_modules
# ------------------------------


def test_list_registry_modules_single_page(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    monkeypatch.setattr(
        service,
        "_http_get",
        lambda _url: {"data": [{"id": "a"}, {"id": "b"}], "links": {}},
    )
    modules = service._list_registry_modules()
    assert modules == [{"id": "a"}, {"id": "b"}]


def test_list_registry_modules_empty_response(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    monkeypatch.setattr(
        service,
        "_http_get",
        lambda _url: {"data": [], "links": {}},
    )
    modules = service._list_registry_modules()
    assert modules == []


# ------------------------------
# _build_catalog_entry
# ------------------------------


def test_build_catalog_entry_structure(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    entry = service._build_catalog_entry(
        module_name="vpc",
        namespace="my-org",
        provider="aws",
        repo_url="https://github.com/example/vpc.git",
        tag="v1.0.0",
        variables=[{"name": "region", "required": True}],
        files=["main.tf", "variables.tf"],
    )
    assert entry["module_name"] == "vpc"
    assert entry["namespace"] == "my-org"
    assert entry["provider"] == "aws"
    assert entry["source"] == "app.terraform.io/my-org/vpc/aws"
    assert entry["vcs_available"] is True
    assert entry["vcs_link"] == "https://github.com/example/vpc.git/tree/v1.0.0"
    assert entry["variables"] == [{"name": "region", "required": True}]
    assert entry["files"] == ["main.tf", "variables.tf"]


# ------------------------------
# _write_catalog / validate_catalog
# ------------------------------


def test_write_catalog_creates_file(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    catalog = {"https://github.com/example/repo.git": {"v1.0.0": {"source": "x"}}}
    service._write_catalog(catalog)

    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data == catalog


def test_write_catalog_overwrites_existing(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service._write_catalog({"old": "data"})
    service._write_catalog({"new": "data"})

    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data == {"new": "data"}


def test_validate_catalog_returns_false_for_empty_file(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    Path(service.catalog_dir).mkdir(parents=True, exist_ok=True)
    Path(service.catalog_path).write_text("", encoding="utf-8")
    assert service.validate_catalog() is False


def test_validate_catalog_returns_false_when_missing(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert service.validate_catalog() is False


# ------------------------------
# _list_repo_files
# ------------------------------


def test_list_repo_files_excludes_git_dir(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    repo = tmp_path / "repo"
    (repo / ".git" / "objects").mkdir(parents=True)
    (repo / ".git" / "objects" / "pack").write_text("binary")
    (repo / "main.tf").write_text("resource {}")
    (repo / "subdir").mkdir()
    (repo / "subdir" / "outputs.tf").write_text("output {}")

    files = service._list_repo_files(repo)
    assert "main.tf" in files
    assert "subdir/outputs.tf" in files or "subdir\\outputs.tf" in files
    assert not any(".git" in f for f in files)


def test_list_repo_files_empty_repo(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    assert service._list_repo_files(repo) == []


# ------------------------------
# _parse_tf_variables
# ------------------------------


def test_parse_tf_variables_basic(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    repo = tmp_path / "tf_repo"
    repo.mkdir()
    (repo / "variables.tf").write_text(
        'variable "region" {\n  type = string\n  description = "AWS region"\n}\n'
    )

    variables = service._parse_tf_variables(repo)
    names = [v["name"] for v in variables]
    assert "region" in names

    region_var = next(v for v in variables if v["name"] == "region")
    assert region_var["required"] is True  # no default


def test_parse_tf_variables_with_default_not_required(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    repo = tmp_path / "tf_repo2"
    repo.mkdir()
    (repo / "variables.tf").write_text(
        'variable "env" {\n  type = string\n  default = "dev"\n}\n'
    )

    variables = service._parse_tf_variables(repo)
    env_var = next((v for v in variables if v["name"] == "env"), None)
    assert env_var is not None
    assert env_var["required"] is False


def test_parse_tf_variables_deduplicates(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    repo = tmp_path / "tf_dedup"
    repo.mkdir()
    content = 'variable "region" {\n  type = string\n}\n'
    (repo / "a.tf").write_text(content)
    (repo / "b.tf").write_text(content)

    variables = service._parse_tf_variables(repo)
    names = [v["name"] for v in variables]
    assert names.count("region") == 1


def test_parse_tf_variables_skips_unparseable_files(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    repo = tmp_path / "tf_bad"
    repo.mkdir()
    (repo / "broken.tf").write_bytes(b"\xff\xfe invalid hcl {{{{")
    (repo / "good.tf").write_text('variable "ok" {\n  type = string\n}\n')

    # Should not raise, and should parse good.tf
    variables = service._parse_tf_variables(repo)
    names = [v["name"] for v in variables]
    assert "ok" in names


def test_parse_tf_variables_ignores_non_tf_files(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)

    repo = tmp_path / "tf_mixed"
    repo.mkdir()
    (repo / "README.md").write_text('variable "fake" {}')
    (repo / "main.tf").write_text('variable "real" {\n  type = string\n}\n')

    variables = service._parse_tf_variables(repo)
    names = [v["name"] for v in variables]
    assert "real" in names
    assert "fake" not in names


# ------------------------------
# build_catalog edge cases
# ------------------------------


def _mock_build_catalog_service(tmp_path, monkeypatch, modules):
    service = _build_service(tmp_path, monkeypatch)
    monkeypatch.setattr(service, "_list_registry_modules", lambda: modules)
    monkeypatch.setattr(service, "_git_clone_repo", lambda _r, _d: None)
    monkeypatch.setattr(service, "_git_checkout_tag", lambda _d, _t: None)
    monkeypatch.setattr(service, "_parse_tf_variables", lambda _d: [])
    monkeypatch.setattr(service, "_list_repo_files", lambda _d: [])
    monkeypatch.setattr(base.shutil, "rmtree", lambda _p, ignore_errors=False: None)
    return service


def test_build_catalog_skips_module_missing_name(tmp_path, monkeypatch):
    modules = [
        {
            "attributes": {
                "namespace": "my-org",
                "provider": "aws",
                "vcs-repo": {"repository-http-url": "https://github.com/x/y.git"},
                "version-statuses": [{"version": "1.0.0"}],
            }
        }
    ]
    service = _mock_build_catalog_service(tmp_path, monkeypatch, modules)
    service.build_catalog()
    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {}


def test_build_catalog_skips_module_missing_vcs(tmp_path, monkeypatch):
    modules = [
        {
            "attributes": {
                "name": "vpc",
                "namespace": "my-org",
                "provider": "aws",
                "version-statuses": [{"version": "1.0.0"}],
            }
        }
    ]
    service = _mock_build_catalog_service(tmp_path, monkeypatch, modules)
    service.build_catalog()
    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {}


def test_build_catalog_skips_module_missing_repo_url(tmp_path, monkeypatch):
    modules = [
        {
            "attributes": {
                "name": "vpc",
                "namespace": "my-org",
                "provider": "aws",
                "vcs-repo": {},
                "version-statuses": [{"version": "1.0.0"}],
            }
        }
    ]
    service = _mock_build_catalog_service(tmp_path, monkeypatch, modules)
    service.build_catalog()
    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {}


def test_build_catalog_skips_invalid_version(tmp_path, monkeypatch):
    modules = [
        {
            "attributes": {
                "name": "vpc",
                "namespace": "my-org",
                "provider": "aws",
                "vcs-repo": {"repository-http-url": "https://github.com/x/vpc.git"},
                "version-statuses": [{"version": None}],
            }
        }
    ]
    service = _mock_build_catalog_service(tmp_path, monkeypatch, modules)
    service.build_catalog()
    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # repo key exists but no tags
    assert data.get("https://github.com/x/vpc.git", {}) == {}


def test_build_catalog_skips_version_when_tag_not_found(tmp_path, monkeypatch):
    modules = [
        {
            "attributes": {
                "name": "vpc",
                "namespace": "my-org",
                "provider": "aws",
                "vcs-repo": {"repository-http-url": "https://github.com/x/vpc.git"},
                "version-statuses": [{"version": "1.0.0"}],
            }
        }
    ]
    service = _build_service(tmp_path, monkeypatch)
    monkeypatch.setattr(service, "_list_registry_modules", lambda: modules)
    monkeypatch.setattr(service, "_git_clone_repo", lambda _r, _d: None)
    monkeypatch.setattr(
        service,
        "_git_checkout_tag",
        lambda _d, _t: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "git")),
    )
    monkeypatch.setattr(base.shutil, "rmtree", lambda _p, ignore_errors=False: None)
    service.build_catalog()

    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("https://github.com/x/vpc.git", {}) == {}


def test_build_catalog_continues_after_clone_failure(tmp_path, monkeypatch):
    modules = [
        {
            "attributes": {
                "name": "bad-module",
                "namespace": "my-org",
                "provider": "aws",
                "vcs-repo": {"repository-http-url": "https://github.com/x/bad.git"},
                "version-statuses": [{"version": "1.0.0"}],
            }
        },
        {
            "attributes": {
                "name": "good-module",
                "namespace": "my-org",
                "provider": "aws",
                "vcs-repo": {"repository-http-url": "https://github.com/x/good.git"},
                "version-statuses": [{"version": "2.0.0"}],
            }
        },
    ]

    service = _build_service(tmp_path, monkeypatch)
    monkeypatch.setattr(service, "_list_registry_modules", lambda: modules)

    def selective_clone(repo_url, clone_dir):
        if "bad" in repo_url:
            raise subprocess.CalledProcessError(128, "git")

    monkeypatch.setattr(service, "_git_clone_repo", selective_clone)
    monkeypatch.setattr(service, "_git_checkout_tag", lambda _d, _t: None)
    monkeypatch.setattr(service, "_parse_tf_variables", lambda _d: [])
    monkeypatch.setattr(service, "_list_repo_files", lambda _d: [])
    monkeypatch.setattr(base.shutil, "rmtree", lambda _p, ignore_errors=False: None)

    service.build_catalog()

    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # bad module repo key created before clone attempt but no tags
    assert data.get("https://github.com/x/bad.git", {}) == {}
    # good module fully indexed
    assert "v2.0.0" in data.get("https://github.com/x/good.git", {})


def test_build_catalog_multiple_versions_same_repo(tmp_path, monkeypatch):
    modules = [
        {
            "attributes": {
                "name": "vpc",
                "namespace": "my-org",
                "provider": "aws",
                "vcs-repo": {"repository-http-url": "https://github.com/x/vpc.git"},
                "version-statuses": [
                    {"version": "1.0.0"},
                    {"version": "2.0.0"},
                    {"version": "3.0.0"},
                ],
            }
        }
    ]
    service = _mock_build_catalog_service(tmp_path, monkeypatch, modules)
    service.build_catalog()

    with open(service.catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    repo_data = data["https://github.com/x/vpc.git"]
    assert set(repo_data.keys()) == {"v1.0.0", "v2.0.0", "v3.0.0"}
