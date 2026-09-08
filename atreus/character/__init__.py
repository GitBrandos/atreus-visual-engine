"""Character module: isolated Monica character layer (personality, state, backend).

This package does not import from, and is not imported by, the existing
simulation/protocol/agents/server modules.
"""

from atreus.character.monica import (
    ConversationState,
    ConversationTurn,
    EchoReplyBackend,
    MonicaCharacter,
    Personality,
    ReplyBackend,
    create_character,
)
from atreus.character.openai_backend import OpenAIReplyBackend

__all__ = [
    "ConversationState",
    "ConversationTurn",
    "EchoReplyBackend",
    "MonicaCharacter",
    "OpenAIReplyBackend",
    "Personality",
    "ReplyBackend",
    "create_character",
]
