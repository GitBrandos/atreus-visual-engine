"""Numpy-backed particle physics shared by the desktop renderer and the
streaming backend.

Keeping the physics free of any rendering/network dependency lets the same
:class:`ParticleSystem` be stepped headlessly (for the FastAPI server) or
driven by the pygame desktop loop.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from atreus.config import DESKTOP_PARTICLE_COUNT, WORLD_HEIGHT, WORLD_WIDTH


@dataclass
class ParticleSystem:
    """A bounded particle sandbox driven by vectorized numpy operations.

    Particles drift under a gentle pull toward the center plus damped random
    jitter, bounce off the world bounds, and are colored by their speed.
    """

    count: int = DESKTOP_PARTICLE_COUNT
    width: float = WORLD_WIDTH
    height: float = WORLD_HEIGHT
    seed: int | None = None

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self.positions = self._rng.uniform(
            [0.0, 0.0], [self.width, self.height], size=(self.count, 2)
        ).astype(np.float32)
        angle = self._rng.uniform(0.0, 2 * np.pi, size=self.count)
        speed = self._rng.uniform(5.0, 40.0, size=self.count)
        self.velocities = np.stack(
            [np.cos(angle) * speed, np.sin(angle) * speed], axis=1
        ).astype(np.float32)
        self.iteration = 0
        self.paused = False
        self._center = np.array([self.width / 2.0, self.height / 2.0], dtype=np.float32)
        self.attraction = 0.02
        self.jitter = 6.0

    def step(self, dt: float) -> None:
        """Advance the simulation by ``dt`` seconds."""
        if self.paused:
            return

        to_center = self._center - self.positions
        self.velocities += to_center * self.attraction * dt
        jitter = self._rng.normal(0.0, self.jitter, size=self.velocities.shape)
        self.velocities += jitter.astype(np.float32) * dt
        self.positions += self.velocities * dt

        for axis, limit in ((0, self.width), (1, self.height)):
            below = self.positions[:, axis] < 0
            above = self.positions[:, axis] > limit
            self.positions[below, axis] = -self.positions[below, axis]
            self.positions[above, axis] = 2 * limit - self.positions[above, axis]
            self.velocities[below, axis] *= -1
            self.velocities[above, axis] *= -1

        self.iteration += 1

    def colors(self) -> np.ndarray:
        """Return an ``(N, 3)`` uint8 array of colors derived from speed."""
        speed = np.linalg.norm(self.velocities, axis=1)
        max_speed = float(speed.max()) if speed.size else 1.0
        normalized = np.clip(speed / max(max_speed, 1e-6), 0.0, 1.0)
        red = (normalized * 255).astype(np.uint8)
        blue = (255 - red).astype(np.uint8)
        green = np.full_like(red, 96)
        return np.stack([red, green, blue], axis=1)

    def reset(self) -> None:
        """Reinitialize the simulation to a fresh random state."""
        self.__post_init__()

    def set_param(self, name: str, value: float) -> None:
        """Update a tunable physics parameter (``attraction`` or ``jitter``)."""
        if name == "attraction":
            self.attraction = float(value)
        elif name == "jitter":
            self.jitter = float(value)
        else:
            raise ValueError(f"Unknown parameter: {name}")
