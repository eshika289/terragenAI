import json
from pathlib import Path

from src import config
from src.config import load_config, save_config


def test_load_config_returns_empty_when_missing(tmp_path, monkeypatch):
    config_file = tmp_path / ".terragenairc"
    monkeypatch.setenv("TERRAGENAI_CONFIG_FILE", str(config_file))

    assert load_config() == {}


def test_save_and_load_config_roundtrip(tmp_path, monkeypatch):
    config_file = tmp_path / ".terragenairc"
    monkeypatch.setenv("TERRAGENAI_CONFIG_FILE", str(config_file))

    expected = {"TF_ORG": "my-org", "TF_REGISTRY_DOMAIN": "app.terraform.io"}
    save_config(expected)

    assert load_config() == expected
    assert json.loads(config_file.read_text(encoding="utf-8")) == expected


def test_get_config_file_prefers_environment_override(tmp_path, monkeypatch):
    config_file = tmp_path / "custom.json"
    monkeypatch.setenv("TERRAGENAI_CONFIG_FILE", str(config_file))

    assert config.get_config_file() == config_file


def test_get_config_file_uses_default_location(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_CONFIG_FILE", raising=False)
    monkeypatch.setattr(config, "get_config_dir", lambda: Path("/tmp/terragenai"))

    assert config.get_config_file() == Path("/tmp/terragenai/.terragenairc")
