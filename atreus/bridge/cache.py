"""Thread-safe cache bridging the particle simulation and the streaming server.

The simulation thread calls :meth:`SharedParticleCache.update` roughly every
``CACHE_SYNC_INTERVAL_MS`` milliseconds with a fresh, down-sampled view of the
particle state. Reader threads (e.g. the WebSocket broadcast loop) call
:meth:`SharedParticleCache.snapshot`, which only ever blocks for the very
short time it takes to copy a reference under the lock -- never on network
I/O -- so the simulation loop is never stalled by slow clients.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING, Any

import numpy as np

from atreus.config import CACHE_SAMPLE_SIZE

if TYPE_CHECKING:  # pragma: no cover - avoids a runtime circular import
    from atreus.simulation.particles import ParticleSystem


@dataclass(frozen=True)
class CacheSnapshot:
    """An immutable, JSON-friendly snapshot of down-sampled particle state."""

    positions: list[list[float]]
    colors: list[list[int]]
    iteration: int
    timestamp: float
    particle_count: int
    sample_count: int
    fps: float = 0.0
    frame_time_ms: float = 0.0
    #: Optional {character_id: state} summary, populated when a
    #: `CharacterRegistry` is wired into the `SimulationLoop`; empty
    #: otherwise, so plain particle-sandbox usage is unaffected.
    character_states: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict suitable for JSON serialization."""
        return {
            "positions": self.positions,
            "colors": self.colors,
            "iteration": self.iteration,
            "timestamp": self.timestamp,
            "particle_count": self.particle_count,
            "sample_count": self.sample_count,
            "fps": self.fps,
            "frame_time_ms": self.frame_time_ms,
            "character_states": self.character_states,
        }


class SharedParticleCache:
    """Holds the most recent down-sampled particle snapshot behind a lock."""

    def __init__(self, sample_size: int = CACHE_SAMPLE_SIZE) -> None:
        self.sample_size = sample_size
        self._lock = Lock()
        self._snapshot: CacheSnapshot | None = None

    def update(
        self,
        system: ParticleSystem,
        fps: float = 0.0,
        frame_time_ms: float = 0.0,
        character_states: dict[str, str] | None = None,
    ) -> CacheSnapshot:
        """Down-sample ``system`` state and store it as the latest snapshot."""
        count = system.positions.shape[0]
        sample_count = min(self.sample_size, count)
        if count > sample_count:
            # Evenly spaced indices give a stable, flicker-free subset of
            # particles to track across successive snapshots.
            indices = np.linspace(0, count - 1, sample_count).astype(np.int64)
        else:
            indices = np.arange(count)

        positions = system.positions[indices]
        colors = system.colors()[indices]

        snapshot = CacheSnapshot(
            positions=positions.round(2).tolist(),
            colors=colors.tolist(),
            iteration=system.iteration,
            timestamp=time.time(),
            particle_count=count,
            sample_count=int(sample_count),
            fps=round(fps, 1),
            frame_time_ms=round(frame_time_ms, 2),
            character_states=dict(character_states) if character_states else {},
        )
        with self._lock:
            self._snapshot = snapshot
        return snapshot

    def snapshot(self) -> CacheSnapshot | None:
        """Return the latest snapshot, or ``None`` if nothing was cached yet."""
        with self._lock:
            return self._snapshot
