import json
import uuid

from src.services.session.session import SessionService


def _build_service(tmp_path, monkeypatch):
    monkeypatch.setattr("src.services.session.session.get_state_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "src.services.session.session.ensure_dir",
        lambda p: p.mkdir(parents=True, exist_ok=True),
    )
    return SessionService()


# ------------------------------
# __init__
# ------------------------------


def test_init_creates_unique_session_file_per_instance(tmp_path, monkeypatch):
    service_a = _build_service(tmp_path, monkeypatch)
    service_b = _build_service(tmp_path, monkeypatch)
    assert service_a.session_file != service_b.session_file


def test_init_session_file_uses_uuid(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    filename = service.session_file.name
    assert filename.startswith("session_")
    # extract uuid part and validate it
    uid = filename.replace("session_", "").replace(".json", "")
    uuid.UUID(uid)  # raises if not a valid uuid


def test_init_max_history_is_10(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert service.MAX_HISTORY == 10


# ------------------------------
# load_session
# ------------------------------


def test_load_session_returns_empty_list_when_file_missing(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    result = service.load_session()
    assert result == []


def test_load_session_returns_saved_messages(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    messages = [{"role": "user", "content": "hello"}]
    service.session_file.write_text(json.dumps(messages), encoding="utf-8")

    result = service.load_session()
    assert result == messages


def test_load_session_caps_at_max_history(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    messages = [{"role": "user", "content": str(i)} for i in range(15)]
    service.session_file.write_text(json.dumps(messages), encoding="utf-8")

    result = service.load_session()
    assert len(result) == 10


def test_load_session_returns_most_recent_messages(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    messages = [{"role": "user", "content": str(i)} for i in range(15)]
    service.session_file.write_text(json.dumps(messages), encoding="utf-8")

    result = service.load_session()
    assert result[0]["content"] == "5"
    assert result[-1]["content"] == "14"


def test_load_session_returns_all_when_under_max_history(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    messages = [{"role": "user", "content": str(i)} for i in range(5)]
    service.session_file.write_text(json.dumps(messages), encoding="utf-8")

    result = service.load_session()
    assert len(result) == 5


def test_load_session_returns_empty_for_empty_file_content(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.session_file.write_text(json.dumps([]), encoding="utf-8")

    result = service.load_session()
    assert result == []


# ------------------------------
# save_session
# ------------------------------


def test_save_session_writes_to_disk(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    messages = [{"role": "user", "content": "hello"}]
    service.save_session(messages)

    assert service.session_file.exists()
    with open(service.session_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == messages


def test_save_session_overwrites_existing(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.save_session([{"role": "user", "content": "first"}])
    service.save_session([{"role": "user", "content": "second"}])

    with open(service.session_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["content"] == "second"


# ------------------------------
# add_message
# ------------------------------


def test_add_message_appends_to_session(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    session = []
    service.add_message(session, "user", "hello")
    assert session == [{"role": "user", "content": "hello"}]


def test_add_message_persists_to_disk(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    session = []
    service.add_message(session, "user", "hello")

    with open(service.session_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == [{"role": "user", "content": "hello"}]


def test_add_message_multiple_messages(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    session = []
    service.add_message(session, "user", "hello")
    service.add_message(session, "assistant", "hi there")

    assert len(session) == 2
    assert session[1] == {"role": "assistant", "content": "hi there"}


def test_add_message_correct_role_and_content(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    session = []
    service.add_message(session, "assistant", "here is your terraform")

    assert session[0]["role"] == "assistant"
    assert session[0]["content"] == "here is your terraform"


# ------------------------------
# clear_session
# ------------------------------


def test_clear_session_deletes_file(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    service.save_session([{"role": "user", "content": "hello"}])
    assert service.session_file.exists()

    service.clear_session()
    assert not service.session_file.exists()


def test_clear_session_does_not_raise_when_file_missing(tmp_path, monkeypatch):
    service = _build_service(tmp_path, monkeypatch)
    assert not service.session_file.exists()
    service.clear_session()  # should not raise


def test_clear_session_leaves_other_session_files_intact(tmp_path, monkeypatch):
    service_a = _build_service(tmp_path, monkeypatch)
    service_b = _build_service(tmp_path, monkeypatch)

    service_a.save_session([{"role": "user", "content": "from a"}])
    service_b.save_session([{"role": "user", "content": "from b"}])

    service_a.clear_session()

    assert not service_a.session_file.exists()
    assert service_b.session_file.exists()
