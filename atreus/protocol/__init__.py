"""Wire message schemas shared between the FastAPI backend and web/mobile clients."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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


class MonicaChatRequest(BaseModel):
    """Inbound chat message sent to the Monica character endpoint."""

    message: str


class MonicaChatResponse(BaseModel):
    """Outbound reply from the Monica character endpoint."""

    reply: str
