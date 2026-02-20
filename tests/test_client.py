from src import client

class MockResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"message": "ok"}

def test_get_api_url_prefers_environment(monkeypatch):
    monkeypatch.setenv("TERRAGENAI_API_URL", "https://env.example.com/chat")
    monkeypatch.setattr(client, "load_config", lambda: {"api_url": "https://config.example.com/chat"})

    assert client.get_api_url() == "https://env.example.com/chat"


def test_send_message_returns_stub_response_when_unconfigured(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_API_URL", raising=False)
    monkeypatch.setattr(client, "load_config", lambda: {})

    response = client.send_message([{"role": "user", "content": "hello"}])

    assert "Test response" in response


def test_send_message_calls_backend_when_configured(monkeypatch):

    called = {}

    def fake_post(url, json, timeout):
        called["url"] = url
        called["json"] = json
        called["timeout"] = timeout
        return MockResponse()

    monkeypatch.setenv("TERRAGENAI_API_URL", "https://api.example.com/chat")
    monkeypatch.setattr(client.requests, "post", fake_post)

    result = client.send_message([{"role": "user", "content": "hello"}])

    assert result == "{'message': 'ok'}"
    assert called["url"] == "https://api.example.com/chat"
    assert called["json"] == {"messages": [{"role": "user", "content": "hello"}]}
    assert called["timeout"] == 30


def test_get_api_url_uses_config_when_env_missing(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_API_URL", raising=False)
    monkeypatch.setattr(client, "load_config", lambda: {"api_url": "https://config.example.com/chat"})

    assert client.get_api_url() == "https://config.example.com/chat"


def test_get_api_url_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("TERRAGENAI_API_URL", raising=False)
    monkeypatch.setattr(client, "load_config", lambda: {})

    assert client.get_api_url() == client.DEFAULT_API_URL


def test_send_message_returns_stringified_payload_when_response_key_missing(monkeypatch):


    monkeypatch.setenv("TERRAGENAI_API_URL", "https://api.example.com/chat")
    monkeypatch.setattr(client.requests, "post", lambda *_args, **_kwargs: MockResponse())

    result = client.send_message([{"role": "user", "content": "hello"}])

    assert result == "{'message': 'ok'}"
