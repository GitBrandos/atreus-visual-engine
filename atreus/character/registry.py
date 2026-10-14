"""In-memory, thread-safe registry of user-authored characters.

Matches the project's existing in-process simplicity (see
:class:`atreus.bridge.cache.SharedParticleCache`,
:class:`atreus.agents.AgentController`) rather than introducing a database
dependency for what is currently a single-process application. Durability
across restarts is an optional, orthogonal concern handled by a pluggable
:class:`atreus.character.store.JSONFileStore` passed in at construction time;
the registry's in-memory dict remains the single source of truth while the
process is running.
"""

from __future__ import annotations

import threading
from typing import Protocol

from atreus.character.models import Character, CharacterState


class CharacterNotFoundError(KeyError):
    """Raised when looking up a character id that isn't registered."""


class CharacterStore(Protocol):
    """Narrow persistence interface a durable backing store must implement."""

    def load(self) -> dict[str, Character]: ...

    def save(self, characters: dict[str, Character]) -> None: ...


class CharacterRegistry:
    """Thread-safe create/list/get/update/delete store for :class:`Character`.

    If ``store`` is given, existing characters are loaded from it on
    construction, and the full character set is persisted back to it after
    every mutation. Persistence is best-effort and synchronous: it happens
    under the same lock as the in-memory mutation, so a snapshot of the
    store never races a concurrent CRUD call, but a slow disk will add
    latency to mutating calls (reads are unaffected).
    """

    def __init__(self, store: CharacterStore | None = None) -> None:
        self._lock = threading.Lock()
        self._store = store
        self._characters: dict[str, Character] = store.load() if store is not None else {}

    def _persist_locked(self) -> None:
        """Write the current character set to the store. Caller must hold the lock."""
        if self._store is not None:
            self._store.save(dict(self._characters))

    def create(self, character: Character) -> Character:
        """Register a new character. Raises ``ValueError`` if the id exists."""
        with self._lock:
            if character.id in self._characters:
                raise ValueError(f"Character id already exists: {character.id!r}")
            self._characters[character.id] = character
            self._persist_locked()
        return character

    def list(self) -> list[Character]:
        """Return all registered characters."""
        with self._lock:
            return list(self._characters.values())

    def get(self, character_id: str) -> Character:
        """Return the character registered under ``character_id``."""
        with self._lock:
            try:
                return self._characters[character_id]
            except KeyError as exc:
                raise CharacterNotFoundError(character_id) from exc

    def update(self, character: Character) -> Character:
        """Replace the stored character sharing ``character.id``."""
        with self._lock:
            if character.id not in self._characters:
                raise CharacterNotFoundError(character.id)
            self._characters[character.id] = character
            self._persist_locked()
        return character

    def set_state(self, character_id: str, state: CharacterState) -> Character:
        """Update just the behavioural state of a registered character.

        Intended to be read by the simulation loop so it can reflect a
        character's state visually without depending on dialogue logic.
        """
        with self._lock:
            try:
                character = self._characters[character_id]
            except KeyError as exc:
                raise CharacterNotFoundError(character_id) from exc
            updated = character.model_copy(update={"state": state})
            self._characters[character_id] = updated
            self._persist_locked()
            return updated

    def set_position(self, character_id: str, position: tuple[float, float]) -> Character:
        """Update just a character's world position (e.g. from per-tick movement).

        Unlike :meth:`create`/:meth:`update`/:meth:`set_state`, this does
        *not* write through to the backing store: movement updates happen
        many times per second, and position is cosmetic/ephemeral state that
        is fine to recompute (it defaults back to the character's last
        persisted position) rather than fsync on every simulation tick.
        """
        with self._lock:
            try:
                character = self._characters[character_id]
            except KeyError as exc:
                raise CharacterNotFoundError(character_id) from exc
            updated = character.model_copy(update={"position": position})
            self._characters[character_id] = updated
            return updated

    def delete(self, character_id: str) -> None:
        """Remove a registered character."""
        with self._lock:
            try:
                del self._characters[character_id]
            except KeyError as exc:
                raise CharacterNotFoundError(character_id) from exc
            self._persist_locked()
