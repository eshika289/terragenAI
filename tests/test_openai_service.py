from unittest.mock import MagicMock, patch

import pytest

from src.services.llm.openai import OpenAIService


def _build_service(monkeypatch, api_key="test-key", dry_run="false"):
    monkeypatch.setattr(
        "src.services.llm.openai.load_config",
        lambda: {"OPENAI_API_KEY": api_key},
    )
    monkeypatch.setenv("DRY_RUN", dry_run)
    with patch("src.services.llm.openai.OpenAI"):
        return OpenAIService()


# ------------------------------
# __init__
# ------------------------------


def test_init_exits_when_no_api_key(monkeypatch):
    monkeypatch.setattr(
        "src.services.llm.openai.load_config",
        lambda: {"OPENAI_API_KEY": ""},
    )
    monkeypatch.setenv("DRY_RUN", "false")
    with patch("src.services.llm.openai.OpenAI"):
        with pytest.raises(SystemExit):
            OpenAIService()


def test_init_exits_when_api_key_is_whitespace(monkeypatch):
    monkeypatch.setattr(
        "src.services.llm.openai.load_config",
        lambda: {"OPENAI_API_KEY": "   "},
    )
    monkeypatch.setenv("DRY_RUN", "false")
    with patch("src.services.llm.openai.OpenAI"):
        with pytest.raises(SystemExit):
            OpenAIService()


def test_init_dry_run_true(monkeypatch):
    service = _build_service(monkeypatch, dry_run="true")
    assert service.dry_run is True


def test_init_dry_run_false(monkeypatch):
    service = _build_service(monkeypatch, dry_run="false")
    assert service.dry_run is False


def test_init_dry_run_case_insensitive(monkeypatch):
    service = _build_service(monkeypatch, dry_run="TRUE")
    assert service.dry_run is True


# ------------------------------
# create_embedding
# ------------------------------


def test_create_embedding_returns_none_when_dry_run(monkeypatch):
    service = _build_service(monkeypatch, dry_run="true")
    result = service.create_embedding("some text")
    assert result is None


def test_create_embedding_calls_openai_and_returns_floats(monkeypatch):
    service = _build_service(monkeypatch, dry_run="false")

    mock_embedding = [0.1, 0.2, 0.3]
    service.client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=mock_embedding)]
    )

    result = service.create_embedding("some text")

    assert result == mock_embedding
    service.client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small", input="some text"
    )


def test_create_embedding_returns_list_of_floats(monkeypatch):
    service = _build_service(monkeypatch, dry_run="false")

    mock_embedding = [0.1, 0.2, 0.3]
    service.client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=mock_embedding)]
    )

    result = service.create_embedding("hello")
    assert isinstance(result, list)
    assert all(isinstance(v, float) for v in result)


# ------------------------------
# generate
# ------------------------------


def test_generate_returns_dry_run_value_when_dry_run(monkeypatch):
    service = _build_service(monkeypatch, dry_run="true")
    result = service.generate([{"role": "user", "content": "hello"}])
    assert result is not None
    assert "DRY_RUN==true" in str(result)


def test_generate_calls_openai_and_returns_content(monkeypatch):
    service = _build_service(monkeypatch, dry_run="false")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "resource aws_s3_bucket {}"
    service.client.chat.completions.create.return_value = mock_response

    result = service.generate([{"role": "user", "content": "create an S3 bucket"}])

    assert result == "resource aws_s3_bucket {}"
    service.client.chat.completions.create.assert_called_once()


def test_generate_uses_default_model_when_env_not_set(monkeypatch):
    service = _build_service(monkeypatch, dry_run="false")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "output"
    service.client.chat.completions.create.return_value = mock_response

    service.generate([{"role": "user", "content": "hello"}])

    call_kwargs = service.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-3.5-turbo"


def test_generate_uses_model_from_env(monkeypatch):
    service = _build_service(monkeypatch, dry_run="false")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "output"
    service.client.chat.completions.create.return_value = mock_response

    service.generate([{"role": "user", "content": "hello"}])

    call_kwargs = service.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4"


def test_generate_uses_temperature_zero(monkeypatch):
    service = _build_service(monkeypatch, dry_run="false")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "output"
    service.client.chat.completions.create.return_value = mock_response

    service.generate([{"role": "user", "content": "hello"}])

    call_kwargs = service.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0
