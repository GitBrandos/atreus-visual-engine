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


#: Default max length (characters) a wrapped engine's reply is allowed to be.
#: Mirrors the inbound message limit in `atreus.protocol.CharacterMessageRequest`
#: so a misbehaving backend can't flood a client with an unbounded response.
MAX_RESPONSE_LENGTH = 4000

#: Blocked substrings a real/hosted backend's *input or output* must never
#: contain. This is a narrow, conservative backstop (not a replacement for
#: upstream content safety on whatever backend is plugged in) that applies
#: uniformly regardless of which `DialogueEngine` is wrapped.
_BLOCKED_MARKERS = ("ignore previous instructions", "system prompt")


class SafetyGuardedDialogueEngine:
    """Wraps any :class:`DialogueEngine` with uniform safety/robustness guardrails.

    This is the intended swap-in point for a real backend (a hosted LLM
    client, a retrieval-augmented system, etc.): rather than wiring a new
    backend directly into `create_app(dialogue_engine=...)`, wrap it in
    `SafetyGuardedDialogueEngine` first so every backend -- offline or
    networked -- gets the same baseline protections:

    - **Fails closed, not open**: if the wrapped engine raises (e.g. a
      network error, a malformed response, a provider outage), this returns
      a safe, in-character fallback turn instead of propagating the
      exception to the HTTP layer.
    - **Bounds the response**: truncates replies to `MAX_RESPONSE_LENGTH`, so
      a backend that returns unbounded text can't be used to flood a client.
    - **Blocks obvious prompt-injection markers**: refuses (with a neutral
      in-character reply) rather than forwarding messages that look like an
      attempt to override the backend's instructions, and never sends such
      markers back to a client even if they end up in a reply.
    """

    def __init__(self, inner: DialogueEngine) -> None:
        self._inner = inner

    def respond(self, character: Character, message: str) -> DialogueTurn:
        lowered = message.lower()
        if any(marker in lowered for marker in _BLOCKED_MARKERS):
            return DialogueTurn(
                text=f"{character.name} doesn't engage with that kind of message.",
                state=CharacterState.IDLE,
            )

        try:
            turn = self._inner.respond(character, message)
        except Exception:  # noqa: BLE001 - never let a backend failure crash the request
            return DialogueTurn(
                text=f"{character.name} is momentarily unavailable. Please try again.",
                state=CharacterState.IDLE,
            )

        text = turn.text
        if any(marker in text.lower() for marker in _BLOCKED_MARKERS):
            text = f"{character.name} doesn't engage with that kind of message."
            return DialogueTurn(text=text, state=CharacterState.IDLE)
        if len(text) > MAX_RESPONSE_LENGTH:
            text = text[: MAX_RESPONSE_LENGTH - 1].rstrip() + "…"
        return DialogueTurn(text=text, state=turn.state)
