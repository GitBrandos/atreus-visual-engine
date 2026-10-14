"""Optional on-disk persistence for :class:`atreus.character.registry.CharacterRegistry`.

The registry itself stays an in-memory dict (see its docstring for why: this
is a single-process application, not a multi-tenant service needing a real
database). A :class:`JSONFileStore` is a thin, swappable persistence layer
the registry can read from on startup and write to on every mutation, so
characters survive a server restart without requiring any new infrastructure
or external dependency.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from atreus.character.models import Character


class JSONFileStore:
    """Persists characters as a single JSON file: ``{"characters": [...]}``.

    Writes are atomic (write to a temp file in the same directory, then
    ``os.replace``) so a crash mid-write can't corrupt the existing file.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Character]:
        """Return all persisted characters, or an empty dict if none exist yet."""
        if not self.path.exists():
            return {}
        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        characters = {}
        for item in data.get("characters", []):
            character = Character(**item)
            characters[character.id] = character
        return characters

    def save(self, characters: dict[str, Character]) -> None:
        """Atomically overwrite the store with the given characters."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"characters": [c.model_dump(mode="json") for c in characters.values()]}
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=f".{self.path.name}.", suffix=".tmp"
        )
        try:
            with open(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
            Path(tmp_name).replace(self.path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
