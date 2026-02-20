from src.memory import add_message, load_history


def test_load_history_returns_empty_when_missing(tmp_path, monkeypatch):
    history_file = tmp_path / "history.json"
    monkeypatch.setenv("TERRAGENAI_HISTORY_FILE", str(history_file))

    assert load_history() == []


def test_add_message_persists_history(tmp_path, monkeypatch):
    history_file = tmp_path / "history.json"
    monkeypatch.setenv("TERRAGENAI_HISTORY_FILE", str(history_file))

    history = load_history()
    add_message(history, "user", "hello")
    add_message(history, "assistant", "hi")

    assert load_history() == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
