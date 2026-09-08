"""Data model for user-authored AI characters.

Characters are plain, validated data -- no dialogue/inference logic lives
here. Traits are general-purpose personality axes (curiosity, formality,
energy, warmth, humour) so the model supports hobbyist, educational,
storytelling, or customer-service-style characters alike, rather than any
single narrow persona.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

#: Personality axes a character's traits are scored on, each in ``[0.0, 1.0]``.
TRAIT_NAMES = ("curiosity", "formality", "energy", "warmth", "humour")


class InteractionMode(str, Enum):
    """Ways a client is allowed to interact with a character."""

    CHAT = "chat"
    NARRATION = "narration"


class CharacterState(str, Enum):
    """Coarse behavioural state a character can be in.

    The simulation loop may read this (via
    :class:`atreus.character.registry.CharacterRegistry`) to reflect a
    character's state visually, without the physics core depending on any
    character/dialogue logic.
    """

    IDLE = "idle"
    ACTIVE = "active"
    REACTING = "reacting"


class Trait(BaseModel):
    """A single named personality axis, scored from 0.0 to 1.0."""

    name: str
    value: float = Field(ge=0.0, le=1.0)


class Character(BaseModel):
    """A user-authored AI character definition.

    Instances are pure data: name, description, personality traits,
    backstory, and the interaction modes a client is allowed to use. Any
    generation/inference backend is supplied separately via
    :mod:`atreus.character.dialogue`.
    """

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=2000)
    backstory: str = Field(default="", max_length=4000)
    traits: dict[str, float] = Field(default_factory=dict)
    interests: list[str] = Field(default_factory=list)
    interaction_modes: list[InteractionMode] = Field(
        default_factory=lambda: [InteractionMode.CHAT]
    )
    state: CharacterState = CharacterState.IDLE

    @field_validator("traits")
    @classmethod
    def _validate_trait_range(cls, traits: dict[str, float]) -> dict[str, float]:
        for name, value in traits.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"Trait {name!r} must be between 0.0 and 1.0, got {value}")
        return traits

    def trait(self, name: str, default: float = 0.5) -> float:
        """Return the value of trait ``name``, or ``default`` if unset."""
        return self.traits.get(name, default)
