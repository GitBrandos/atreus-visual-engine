"""AI Character layer: user-authored characters that can inhabit the Atreus world.

This package is intentionally separate from and optional to the existing
particle simulation/streaming stack (``agents``, ``simulation``, ``bridge``,
``server``). A character is pure data (see :mod:`atreus.character.models`)
plus a small, pluggable dialogue interface (see
:mod:`atreus.character.dialogue`); nothing here couples the particle sandbox
to character logic, so ``python -m atreus.synced_system`` keeps working
exactly as before with zero characters registered.
"""

from __future__ import annotations

from atreus.character.dialogue import DialogueEngine, TemplateDialogueEngine
from atreus.character.models import Character, CharacterState, Trait
from atreus.character.registry import CharacterRegistry

__all__ = [
    "Character",
    "CharacterState",
    "Trait",
    "CharacterRegistry",
    "DialogueEngine",
    "TemplateDialogueEngine",
]
