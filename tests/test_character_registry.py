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


def test_set_position_updates_only_position():
    registry = CharacterRegistry()
    registry.create(_make())
    updated = registry.set_position("nova", (10.0, 20.0))
    assert updated.position == (10.0, 20.0)
    assert registry.get("nova").position == (10.0, 20.0)


def test_set_position_missing_raises_not_found():
    registry = CharacterRegistry()
    with pytest.raises(CharacterNotFoundError):
        registry.set_position("missing", (0.0, 0.0))


class _RecordingStore:
    """A fake `CharacterStore` that records save() calls and returns fixed data."""

    def __init__(self, initial: dict[str, Character] | None = None) -> None:
        self.initial = initial or {}
        self.saved: list[dict[str, Character]] = []

    def load(self) -> dict[str, Character]:
        return dict(self.initial)

    def save(self, characters: dict[str, Character]) -> None:
        self.saved.append(dict(characters))


def test_registry_loads_characters_from_store_on_construction():
    store = _RecordingStore(initial={"nova": _make()})
    registry = CharacterRegistry(store=store)
    assert registry.get("nova").name == "Nova"


def test_registry_persists_on_create_update_delete_and_set_state():
    store = _RecordingStore()
    registry = CharacterRegistry(store=store)

    registry.create(_make())
    assert len(store.saved) == 1
    assert "nova" in store.saved[-1]

    registry.update(Character(id="nova", name="Nova Prime"))
    assert len(store.saved) == 2
    assert store.saved[-1]["nova"].name == "Nova Prime"

    registry.set_state("nova", CharacterState.ACTIVE)
    assert len(store.saved) == 3
    assert store.saved[-1]["nova"].state == CharacterState.ACTIVE

    registry.delete("nova")
    assert len(store.saved) == 4
    assert "nova" not in store.saved[-1]


def test_registry_does_not_persist_on_set_position():
    """Position changes (per-tick movement) are deliberately not written through."""
    store = _RecordingStore(initial={"nova": _make()})
    registry = CharacterRegistry(store=store)
    registry.set_position("nova", (1.0, 2.0))
    assert store.saved == []
