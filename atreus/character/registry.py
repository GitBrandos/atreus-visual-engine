"""In-memory, thread-safe registry of user-authored characters.

Matches the project's existing in-process simplicity (see
:class:`atreus.bridge.cache.SharedParticleCache`,
:class:`atreus.agents.AgentController`) rather than introducing a database
dependency for what is currently a single-process application.
"""

from __future__ import annotations

import threading

from atreus.character.models import Character, CharacterState


class CharacterNotFoundError(KeyError):
    """Raised when looking up a character id that isn't registered."""


class CharacterRegistry:
    """Thread-safe create/list/get/update/delete store for :class:`Character`."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._characters: dict[str, Character] = {}

    def create(self, character: Character) -> Character:
        """Register a new character. Raises ``ValueError`` if the id exists."""
        with self._lock:
            if character.id in self._characters:
                raise ValueError(f"Character id already exists: {character.id!r}")
            self._characters[character.id] = character
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
            return updated

    def delete(self, character_id: str) -> None:
        """Remove a registered character."""
        with self._lock:
            try:
                del self._characters[character_id]
            except KeyError as exc:
                raise CharacterNotFoundError(character_id) from exc
