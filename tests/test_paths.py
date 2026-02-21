from pathlib import Path
from types import SimpleNamespace

from src import paths


def test_get_config_dir_uses_terragenai_home_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TERRAGENAI_HOME", str(tmp_path))
    monkeypatch.setattr(paths.sys, "platform", "linux")

    assert paths.get_config_dir() == tmp_path.resolve()


def test_get_state_dir_uses_terragenai_home_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TERRAGENAI_HOME", str(tmp_path))
    monkeypatch.setattr(paths.sys, "platform", "linux")

    assert paths.get_state_dir() == tmp_path.resolve()


def test_get_config_dir_uses_xdg_config_on_posix(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_HOME", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/xdg-config")
    monkeypatch.setattr(paths.sys, "platform", "linux")

    assert paths.get_config_dir() == Path("/tmp/xdg-config/terragenai")


def test_get_state_dir_uses_xdg_state_on_posix(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_HOME", raising=False)
    monkeypatch.setenv("XDG_STATE_HOME", "/tmp/xdg-state")
    monkeypatch.setattr(paths.sys, "platform", "linux")

    assert paths.get_state_dir() == Path("/tmp/xdg-state/terragenai")


def test_get_config_dir_uses_appdata_on_windows(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_HOME", raising=False)
    monkeypatch.setattr(paths.sys, "platform", "win32")
    fake_os = SimpleNamespace(
        name="nt", getenv=lambda key: {"APPDATA": "/tmp/appdata"}.get(key)
    )
    monkeypatch.setattr(paths, "os", fake_os)

    assert paths.get_config_dir() == Path("/tmp/appdata/.terragenai")


def test_get_state_dir_uses_localappdata_on_windows(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_HOME", raising=False)
    monkeypatch.setattr(paths.sys, "platform", "win32")
    fake_os = SimpleNamespace(
        name="nt", getenv=lambda key: {"LOCALAPPDATA": "/tmp/localappdata"}.get(key)
    )
    monkeypatch.setattr(paths, "os", fake_os)

    assert paths.get_state_dir() == Path("/tmp/localappdata/.terragenai")


def test_get_config_dir_darwin(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_HOME", raising=False)
    monkeypatch.setattr(paths.sys, "platform", "darwin")
    monkeypatch.setattr(
        paths.Path, "home", classmethod(lambda _cls: Path("/Users/test"))
    )

    assert paths.get_config_dir() == Path("/Users/test/.terragenai")


def test_get_state_dir_darwin(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_HOME", raising=False)
    monkeypatch.setattr(paths.sys, "platform", "darwin")
    monkeypatch.setattr(
        paths.Path, "home", classmethod(lambda _cls: Path("/Users/test"))
    )

    assert paths.get_state_dir() == Path(
        "/Users/test/Library/Application Support/.terragenai"
    )


def test_ensure_dir_creates_directory(tmp_path):
    new_dir = tmp_path / "nested" / "path"

    returned = paths.ensure_dir(new_dir)

    assert new_dir.exists()
    assert returned == new_dir
