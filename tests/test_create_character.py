"""Tests for the create_character convenience factory."""

from atreus.character import EchoReplyBackend, OpenAIReplyBackend, create_character
from atreus.character.openai_backend import API_KEY_ENV_VAR


def test_create_character_uses_echo_backend_without_api_key(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    character = create_character()
    assert isinstance(character.backend, EchoReplyBackend)


def test_create_character_uses_openai_backend_with_api_key(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "test-key")
    character = create_character()
    assert isinstance(character.backend, OpenAIReplyBackend)


def test_create_character_accepts_custom_personality(monkeypatch):
    from atreus.character import Personality

    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    personality = Personality(name="Monica", tone="playful")
    character = create_character(personality=personality)
    assert character.personality.tone == "playful"
