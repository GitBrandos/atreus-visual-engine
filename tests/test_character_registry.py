"""Tests for the in-memory character registry."""

import pytest

from atreus.character.models import Character, CharacterState
from atreus.character.registry import CharacterNotFoundError, CharacterRegistry


def _make(character_id: str = "nova") -> Character:
    return Character(id=character_id, name="Nova")


def test_create_and_get_roundtrip():
    registry = CharacterRegistry()
    registry.create(_make())
    assert registry.get("nova").name == "Nova"


def test_create_rejects_duplicate_id():
    registry = CharacterRegistry()
    registry.create(_make())
    with pytest.raises(ValueError):
        registry.create(_make())


def test_get_missing_raises_not_found():
    registry = CharacterRegistry()
    with pytest.raises(CharacterNotFoundError):
        registry.get("missing")


def test_list_returns_all_characters():
    registry = CharacterRegistry()
    registry.create(_make("a"))
    registry.create(_make("b"))
    ids = {c.id for c in registry.list()}
    assert ids == {"a", "b"}


def test_update_replaces_existing_character():
    registry = CharacterRegistry()
    registry.create(_make())
    updated = Character(id="nova", name="Nova Prime")
    registry.update(updated)
    assert registry.get("nova").name == "Nova Prime"


def test_update_missing_raises_not_found():
    registry = CharacterRegistry()
    with pytest.raises(CharacterNotFoundError):
        registry.update(_make())


def test_set_state_updates_only_state():
    registry = CharacterRegistry()
    registry.create(_make())
    updated = registry.set_state("nova", CharacterState.REACTING)
    assert updated.state == CharacterState.REACTING
    assert registry.get("nova").state == CharacterState.REACTING


def test_delete_removes_character():
    registry = CharacterRegistry()
    registry.create(_make())
    registry.delete("nova")
    with pytest.raises(CharacterNotFoundError):
        registry.get("nova")


def test_delete_missing_raises_not_found():
    registry = CharacterRegistry()
    with pytest.raises(CharacterNotFoundError):
        registry.delete("missing")
