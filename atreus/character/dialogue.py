"""Pluggable interface for turning a character + user input into a response.

``DialogueEngine`` is intentionally narrow so a real backend (a hosted LLM,
a rules engine, a scripted narrative system, etc.) can be swapped in without
touching the registry, server, or simulation layers. :class:`TemplateDialogueEngine`
is a minimal, fully offline default implementation used when no other
backend is configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from atreus.character.models import Character, CharacterState


@dataclass(frozen=True)
class DialogueTurn:
    """The result of a single conversational turn with a character."""

    text: str
    state: CharacterState


class DialogueEngine(Protocol):
    """Narrow interface a pluggable response backend must implement."""

    def respond(self, character: Character, message: str) -> DialogueTurn:
        """Return the character's reply and resulting behavioural state."""
        ...


class TemplateDialogueEngine:
    """A minimal, offline, rule-based default :class:`DialogueEngine`.

    Produces deterministic, template-based responses shaped by a character's
    traits and interests. No network access or external content generation
    is involved; this exists so the character system is usable end-to-end
    without requiring an external LLM to be wired up.
    """

    _HUMOUR_MARKERS = ("haha", "lol", "funny", "joke")

    def respond(self, character: Character, message: str) -> DialogueTurn:
        stripped = message.strip()
        if not stripped:
            return DialogueTurn(
                text=f"{character.name} waits for you to say something.",
                state=CharacterState.IDLE,
            )

        lowered = stripped.lower()
        if any(marker in lowered for marker in self._HUMOUR_MARKERS):
            state = CharacterState.REACTING
        else:
            state = CharacterState.ACTIVE

        warmth = character.trait("warmth")
        curiosity = character.trait("curiosity")

        opening = "Hey there!" if warmth >= 0.5 else "Hello."
        if curiosity >= 0.5 and character.interests:
            follow_up = f" Speaking of which, have you tried {character.interests[0]}?"
        else:
            follow_up = ""

        text = f"{opening} You said: {stripped!r}.{follow_up}"
        return DialogueTurn(text=text, state=state)
