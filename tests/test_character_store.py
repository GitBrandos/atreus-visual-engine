"""Tests for the JSON-file-backed character persistence store."""

from __future__ import annotations

from atreus.character.models import Character
from atreus.character.registry import CharacterRegistry
from atreus.character.store import JSONFileStore


def test_load_returns_empty_dict_when_file_missing(tmp_path):
    store = JSONFileStore(tmp_path / "characters.json")
    assert store.load() == {}


def test_save_then_load_roundtrips_characters(tmp_path):
    store = JSONFileStore(tmp_path / "characters.json")
    nova = Character(id="nova", name="Nova", position=(100.0, 200.0))
    store.save({"nova": nova})

    loaded = store.load()
    assert set(loaded) == {"nova"}
    assert loaded["nova"].name == "Nova"
    assert loaded["nova"].position == (100.0, 200.0)
    assert loaded["nova"].marker_color == nova.marker_color


def test_save_overwrites_previous_contents(tmp_path):
    path = tmp_path / "characters.json"
    store = JSONFileStore(path)
    store.save({"a": Character(id="a", name="A")})
    store.save({"b": Character(id="b", name="B")})

    loaded = store.load()
    assert set(loaded) == {"b"}


def test_save_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "characters.json"
    store = JSONFileStore(path)
    store.save({"a": Character(id="a", name="A")})
    assert path.exists()


def test_load_ignores_blank_file(tmp_path):
    path = tmp_path / "characters.json"
    path.write_text("   ")
    store = JSONFileStore(path)
    assert store.load() == {}


def test_registry_with_json_store_survives_reload(tmp_path):
    """Simulates a process restart: a fresh registry backed by the same store
    picks up characters persisted by a previous registry instance."""
    path = tmp_path / "characters.json"
    store = JSONFileStore(path)

    first = CharacterRegistry(store=store)
    first.create(Character(id="nova", name="Nova"))

    second = CharacterRegistry(store=JSONFileStore(path))
    assert second.get("nova").name == "Nova"
