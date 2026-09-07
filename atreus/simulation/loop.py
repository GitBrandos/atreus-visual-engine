"""Shared simulation-stepping loop used by both the desktop and headless runners.

Applying agent commands, stepping physics, and refreshing the cache all
happen on whichever thread calls :meth:`SimulationLoop.tick`, keeping the
hot path free of any network I/O.
"""

from __future__ import annotations

import time
from threading import Event

from atreus.agents import AgentController
from atreus.bridge.cache import SharedParticleCache
from atreus.config import CACHE_SYNC_INTERVAL_MS, TARGET_FPS
from atreus.simulation.particles import ParticleSystem


class SimulationLoop:
    """Steps a `ParticleSystem`, applies agent commands, and refreshes the cache."""

    def __init__(
        self,
        system: ParticleSystem,
        cache: SharedParticleCache,
        controller: AgentController,
    ) -> None:
        self.system = system
        self.cache = cache
        self.controller = controller
        self._last_cache_update = 0.0
        self._stop = Event()

    def tick(self, dt: float, fps: float = 0.0) -> None:
        """Apply pending commands, step the simulation, and refresh the cache."""
        self.controller.apply_pending(self.system)

        frame_start = time.perf_counter()
        self.system.step(dt)
        frame_time_ms = (time.perf_counter() - frame_start) * 1000.0

        now = time.perf_counter()
        if (now - self._last_cache_update) * 1000.0 >= CACHE_SYNC_INTERVAL_MS:
            self.cache.update(self.system, fps=fps, frame_time_ms=frame_time_ms)
            self._last_cache_update = now

    def stop(self) -> None:
        """Signal :meth:`run_headless` to exit its loop."""
        self._stop.set()

    def run_headless(self, target_fps: int = TARGET_FPS) -> None:
        """Run the loop on the calling thread (no rendering) until stopped."""
        frame_duration = 1.0 / target_fps
        while not self._stop.is_set():
            start = time.perf_counter()
            self.tick(frame_duration, fps=float(target_fps))
            elapsed = time.perf_counter() - start
            remaining = frame_duration - elapsed
            if remaining > 0:
                time.sleep(remaining)
