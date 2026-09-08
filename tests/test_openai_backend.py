"""Tests for the OpenAI-backed Monica reply backend (no real network calls)."""

import httpx
import pytest

from atreus.character import MonicaCharacter, OpenAIReplyBackend
from atreus.character.openai_backend import API_KEY_ENV_VAR, OPENAI_API_URL


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    with pytest.raises(RuntimeError):
        OpenAIReplyBackend()


def test_reads_api_key_from_environment(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "test-key-from-env")
    backend = OpenAIReplyBackend()
    assert backend._api_key == "test-key-from-env"


def test_explicit_api_key_overrides_environment(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    backend = OpenAIReplyBackend(api_key="explicit-key")
    assert backend._api_key == "explicit-key"


def test_generate_reply_calls_openai_and_parses_response(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return httpx.Response(
            status_code=200,
            json={"choices": [{"message": {"content": "Hello there!"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    backend = OpenAIReplyBackend(api_key="test-key")
    character = MonicaCharacter(backend=backend)
    reply = character.respond("hi Monica")

    assert reply == "Hello there!"
    assert captured["url"] == OPENAI_API_URL
    expected_auth = "Bearer " + "test-key"
    assert captured["headers"]["Authorization"] == expected_auth
    assert captured["json"]["messages"][-1] == {"role": "user", "content": "hi Monica"}


def test_generate_reply_raises_on_http_error(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return httpx.Response(
            status_code=401,
            json={"error": "unauthorized"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    backend = OpenAIReplyBackend(api_key="bad-key")
    with pytest.raises(httpx.HTTPStatusError):
        backend.generate_reply(character_personality(), [], "hi")


def character_personality():
    from atreus.character import Personality

    return Personality()
