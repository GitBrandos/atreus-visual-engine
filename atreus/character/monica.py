"""Monica character layer: personality, conversation state, and reply backend.

This module is intentionally isolated from the rest of Atreus (simulation,
protocol, agents, server) -- nothing here is imported by, or imports from,
those modules. It defines a minimal, self-contained character model that a
future OpenAI-backed :class:`ReplyBackend` can plug into via
:meth:`MonicaCharacter.respond`, without requiring any changes to the
existing particle simulation/streaming architecture.

No network calls are made by this module. Wiring an actual OpenAI-backed
:class:`ReplyBackend` (reading ``OPENAI_API_KEY`` from the environment) is a
follow-up step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Personality:
    """Static character traits describing how Monica should communicate."""

    name: str = "Monica"
    tone: str = "warm and encouraging"
    traits: tuple[str, ...] = ("curious", "supportive", "concise")
    description: str = "A friendly conversational companion."


@dataclass(frozen=True)
class ConversationTurn:
    """A single exchange in a conversation: one speaker, one message."""

    role: str
    content: str


@dataclass
class ConversationState:
    """Ordered history of turns for a single conversation session."""

    turns: list[ConversationTurn] = field(default_factory=list)

    def add_turn(self, role: str, content: str) -> ConversationTurn:
        """Append and return a new :class:`ConversationTurn`."""
        turn = ConversationTurn(role=role, content=content)
        self.turns.append(turn)
        return turn

    def history(self) -> list[ConversationTurn]:
        """Return all recorded turns, oldest first."""
        return list(self.turns)

    def reset(self) -> None:
        """Clear all recorded turns."""
        self.turns.clear()


class ReplyBackend(Protocol):
    """Clean interface a reply-generation backend must implement.

    A future OpenAI-backed implementation can satisfy this interface (e.g.
    by calling the Chat Completions API with ``personality`` and ``history``
    as context) without any other change to :class:`MonicaCharacter`.
    """

    def generate_reply(
        self,
        personality: Personality,
        history: list[ConversationTurn],
        message: str,
    ) -> str:
        """Return a reply to ``message`` given ``personality`` and ``history``."""
        ...


class EchoReplyBackend:
    """Minimal default backend with no external dependencies.

    Used until a real (e.g. OpenAI-backed) :class:`ReplyBackend` is wired in.
    """

    def generate_reply(
        self,
        personality: Personality,
        history: list[ConversationTurn],
        message: str,
    ) -> str:
        return f"{personality.name}: I heard you say '{message}'."


class MonicaCharacter:
    """The Monica character: personality + conversation state + reply backend."""

    def __init__(
        self,
        personality: Personality | None = None,
        backend: ReplyBackend | None = None,
    ) -> None:
        self.personality = personality or Personality()
        self.state = ConversationState()
        self.backend = backend or EchoReplyBackend()

    def respond(self, message: str) -> str:
        """Record ``message``, generate a reply via ``backend``, and record it."""
        self.state.add_turn("user", message)
        reply = self.backend.generate_reply(
            self.personality, self.state.history(), message
        )
        self.state.add_turn(self.personality.name.lower(), reply)
        return reply


def create_character(personality: Personality | None = None) -> MonicaCharacter:
    """Build a :class:`MonicaCharacter` with the best available backend.

    If the ``OPENAI_API_KEY`` environment variable is set, replies are
    generated via :class:`~atreus.character.openai_backend.OpenAIReplyBackend`.
    Otherwise, the dependency-free :class:`EchoReplyBackend` is used, so this
    always succeeds even without an API key configured.
    """
    import os

    if os.environ.get("OPENAI_API_KEY"):
        from atreus.character.openai_backend import OpenAIReplyBackend

        backend: ReplyBackend = OpenAIReplyBackend()
    else:
        backend = EchoReplyBackend()
    return MonicaCharacter(personality=personality, backend=backend)
