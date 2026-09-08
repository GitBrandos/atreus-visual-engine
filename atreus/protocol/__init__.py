"""Wire message schemas shared between the FastAPI backend and web/mobile clients."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from atreus.character.models import CharacterState, InteractionMode


class AgentCommandMessage(BaseModel):
    """Inbound agent command sent from the mobile web UI."""

    action: str
    payload: dict[str, Any] | None = None


class ParticleSnapshotMessage(BaseModel):
    """Outbound down-sampled particle snapshot streamed to clients."""

    type: str = Field(default="snapshot")
    positions: list[list[float]]
    colors: list[list[int]]
    iteration: int
    timestamp: float
    particle_count: int
    sample_count: int
    fps: float = 0.0
    frame_time_ms: float = 0.0


class StatusMessage(BaseModel):
    """Outbound status/metrics summary for the HTTP status endpoint."""

    running: bool
    connected_clients: int
    iteration: int
    particle_count: int
    sample_count: int
    fps: float
    frame_time_ms: float
    last_update_age_ms: float | None = None


class CharacterCreateRequest(BaseModel):
    """Inbound request to register a new character."""

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=2000)
    backstory: str = Field(default="", max_length=4000)
    traits: dict[str, float] = Field(default_factory=dict)
    interests: list[str] = Field(default_factory=list)
    interaction_modes: list[InteractionMode] = Field(
        default_factory=lambda: [InteractionMode.CHAT]
    )


class CharacterResponse(BaseModel):
    """Outbound representation of a registered character."""

    id: str
    name: str
    description: str
    backstory: str
    traits: dict[str, float]
    interests: list[str]
    interaction_modes: list[InteractionMode]
    state: CharacterState


class CharacterMessageRequest(BaseModel):
    """Inbound chat message sent to a specific character."""

    message: str = Field(min_length=1, max_length=4000)


class CharacterMessageResponse(BaseModel):
    """Outbound reply from a character after processing a chat message."""

    text: str
    state: CharacterState

