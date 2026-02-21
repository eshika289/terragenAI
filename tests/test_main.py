import argparse
import builtins

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


def test_chat_round_trip(monkeypatch):
    prompts = iter(["hello", "exit"])
    history_store = []
    output = []

    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(prompts))
    monkeypatch.setattr(
        main,
        "get_registry_service",
        lambda: type("S", (), {"validate_catalog": lambda self: True})(),
    )
    monkeypatch.setattr(main, "load_history", lambda: history_store)
    monkeypatch.setattr(main, "send_message", lambda _history: "hi there")
    monkeypatch.setattr(
        main,
        "add_message",
        lambda history, role, content: history.append(
            {"role": role, "content": content}
        ),
    )
    monkeypatch.setattr(main, "print", lambda value: output.append(value))

    main.chat()

    assert history_store == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    assert any("TerragenAI Chat started" in str(line) for line in output)


def test_configure_uses_default_when_input_blank(monkeypatch):
    saved = {}
    output = []

    monkeypatch.setattr(main, "load_config", lambda: {})
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "")
    monkeypatch.setattr(main, "save_config", lambda cfg: saved.update(cfg))
    monkeypatch.setattr(main, "get_config_file", lambda: "/tmp/.terragenairc")
    monkeypatch.setattr(main, "print", lambda value: output.append(value))

    main.configure()

    assert saved == {
        "TF_ORG": "",
        "TF_REGISTRY_DOMAIN": "app.terraform.io",
        "TF_API_TOKEN": "",
        "GIT_CLONE_TOKEN": "",
    }
    assert any("Saved configuration" in str(line) for line in output)
