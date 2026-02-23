import argparse
import builtins
from unittest.mock import MagicMock

from src import main


def test_build_parser_has_expected_flags():
    parser = main.build_parser()
    assert isinstance(parser, argparse.ArgumentParser)

    parsed = parser.parse_args(["--version"])
    assert parsed.version is True
    assert parsed.configure is False


def test_run_starts_chat_when_no_args(monkeypatch):
    monkeypatch.setattr(main.sys, "argv", ["terragenai"])
    called = {"chat": 0}
    monkeypatch.setattr(
        main, "chat", lambda: called.__setitem__("chat", called["chat"] + 1)
    )
    main.run()
    assert called["chat"] == 1


def test_run_version_flag_prints_version(monkeypatch):
    monkeypatch.setattr(main.sys, "argv", ["terragenai", "--version"])
    output = []
    monkeypatch.setattr(main, "print", lambda value: output.append(value))
    main.run()
    assert output == [main.__version__]


def test_run_configure_flag_calls_configure(monkeypatch):
    monkeypatch.setattr(main.sys, "argv", ["terragenai", "--configure"])
    called = {"configure": 0}
    monkeypatch.setattr(
        main,
        "configure",
        lambda: called.__setitem__("configure", called["configure"] + 1),
    )
    main.run()
    assert called["configure"] == 1


def test_run_sync_flag_calls_sync(monkeypatch):
    monkeypatch.setattr(main.sys, "argv", ["terragenai", "--sync"])
    called = {"sync": 0}
    monkeypatch.setattr(
        main,
        "sync_registry_modules",
        lambda: called.__setitem__("sync", called["sync"] + 1),
    )
    main.run()
    assert called["sync"] == 1


# ------------------------------
# chat
# ------------------------------

def _mock_registry(validate=True):
    registry = MagicMock()
    registry.validate_catalog.return_value = validate
    registry.pull_catalog.return_value = []
    return registry


def _mock_vector_store():
    vector_store = MagicMock()
    vector_store.create_index.return_value = None
    return vector_store


def _mock_session():
    session = MagicMock()
    session.load_session.return_value = []
    return session


def test_chat_exits_early_when_catalog_not_found(monkeypatch):
    output = []
    monkeypatch.setattr(main, "SessionService", lambda: _mock_session())
    monkeypatch.setattr(main, "get_registry_service", lambda: _mock_registry(validate=False))
    monkeypatch.setattr(main, "print", lambda value: output.append(str(value)))
    main.chat()
    assert any("sync" in line.lower() or "not found" in line.lower() for line in output)


def test_chat_round_trip(monkeypatch):
    prompts = iter(["hello", "exit"])
    output = []
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(prompts))
    monkeypatch.setattr(main, "SessionService", lambda: _mock_session())
    monkeypatch.setattr(main, "get_registry_service", lambda: _mock_registry())
    monkeypatch.setattr(main, "FaissService", lambda catalog: _mock_vector_store())
    monkeypatch.setattr(main, "send_message", lambda prompt, history, vs: "hi there")
    monkeypatch.setattr(main, "print", lambda value: output.append(str(value)))
    main.chat()
    assert any("TerragenAI Chat started" in line for line in output)
    assert any("hi there" in line for line in output)


def test_chat_loop_exits_on_quit(monkeypatch):
    prompts = iter(["quit"])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(prompts))
    monkeypatch.setattr(main, "SessionService", lambda: _mock_session())
    monkeypatch.setattr(main, "get_registry_service", lambda: _mock_registry())
    monkeypatch.setattr(main, "FaissService", lambda catalog: _mock_vector_store())
    monkeypatch.setattr(main, "send_message", lambda prompt, history, vs: "reply")
    monkeypatch.setattr(main, "print", lambda value: None)
    main.chat()  # should not raise StopIteration


def test_chat_sends_user_input_to_send_message(monkeypatch):
    prompts = iter(["create a vpc", "exit"])
    received_prompts = []
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(prompts))
    monkeypatch.setattr(main, "SessionService", lambda: _mock_session())
    monkeypatch.setattr(main, "get_registry_service", lambda: _mock_registry())
    monkeypatch.setattr(main, "FaissService", lambda catalog: _mock_vector_store())
    monkeypatch.setattr(
        main,
        "send_message",
        lambda prompt, history, vs: received_prompts.append(prompt) or "reply",
    )
    monkeypatch.setattr(main, "print", lambda value: None)
    main.chat()
    assert received_prompts == ["create a vpc"]


def test_chat_clears_session_on_exit(monkeypatch):
    prompts = iter(["exit"])
    mock_session = _mock_session()
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(prompts))
    monkeypatch.setattr(main, "SessionService", lambda: mock_session)
    monkeypatch.setattr(main, "get_registry_service", lambda: _mock_registry())
    monkeypatch.setattr(main, "FaissService", lambda catalog: _mock_vector_store())
    monkeypatch.setattr(main, "send_message", lambda prompt, history, vs: "reply")
    monkeypatch.setattr(main, "print", lambda value: None)
    main.chat()
    mock_session.clear_session.assert_called_once()


def test_chat_adds_user_and_assistant_messages_to_session(monkeypatch):
    prompts = iter(["hello", "exit"])
    mock_session = _mock_session()
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(prompts))
    monkeypatch.setattr(main, "SessionService", lambda: mock_session)
    monkeypatch.setattr(main, "get_registry_service", lambda: _mock_registry())
    monkeypatch.setattr(main, "FaissService", lambda catalog: _mock_vector_store())
    monkeypatch.setattr(main, "send_message", lambda prompt, history, vs: "hi there")
    monkeypatch.setattr(main, "print", lambda value: None)
    main.chat()
    calls = [(c.args[1], c.args[2]) for c in mock_session.add_message.call_args_list]
    assert ("user", "hello") in calls
    assert ("assistant", "hi there") in calls


# ------------------------------
# configure
# ------------------------------

def test_configure_uses_default_when_input_blank(monkeypatch):
    saved = {}
    output = []
    monkeypatch.setattr(main, "load_config", lambda: {})
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "")
    monkeypatch.setattr(main, "save_config", lambda cfg: saved.update(cfg))
    monkeypatch.setattr(main, "get_config_file", lambda: "/tmp/.terragenairc")
    monkeypatch.setattr(main, "print", lambda value: output.append(str(value)))
    main.configure()
    assert saved == {
        "TF_ORG": "",
        "TF_REGISTRY_DOMAIN": "app.terraform.io",
        "TF_API_TOKEN": "",
        "GIT_CLONE_TOKEN": "",
        "OPENAI_API_KEY": "",
    }
    assert any("Saved configuration" in line for line in output)


def test_configure_uses_provided_input(monkeypatch):
    saved = {}
    inputs = iter(["my-org", "app.terraform.io", "tf-token", "git-token", "openai-key"])
    monkeypatch.setattr(main, "load_config", lambda: {})
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(main, "save_config", lambda cfg: saved.update(cfg))
    monkeypatch.setattr(main, "get_config_file", lambda: "/tmp/.terragenairc")
    monkeypatch.setattr(main, "print", lambda value: None)
    main.configure()
    assert saved["TF_ORG"] == "my-org"
    assert saved["TF_API_TOKEN"] == "tf-token"
    assert saved["OPENAI_API_KEY"] == "openai-key"


def test_configure_falls_back_to_existing_config(monkeypatch):
    saved = {}
    existing = {
        "TF_ORG": "existing-org",
        "TF_REGISTRY_DOMAIN": "app.terraform.io",
        "TF_API_TOKEN": "existing-token",
        "GIT_CLONE_TOKEN": "",
        "OPENAI_API_KEY": "existing-key",
    }
    monkeypatch.setattr(main, "load_config", lambda: existing)
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "")
    monkeypatch.setattr(main, "save_config", lambda cfg: saved.update(cfg))
    monkeypatch.setattr(main, "get_config_file", lambda: "/tmp/.terragenairc")
    monkeypatch.setattr(main, "print", lambda value: None)
    main.configure()
    assert saved["TF_ORG"] == "existing-org"
    assert saved["TF_API_TOKEN"] == "existing-token"
    assert saved["OPENAI_API_KEY"] == "existing-key"
