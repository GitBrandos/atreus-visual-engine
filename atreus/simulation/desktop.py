"""Pygame-based desktop renderer for the Atreus particle sandbox.

Keeps the original desktop rendering path working while feeding the same
`SharedParticleCache`/`AgentController` used by the FastAPI streaming
backend, so a single process can drive both the desktop window and the
mobile web stream.
"""

from __future__ import annotations

import numpy as np
import pygame

from atreus.agents import AgentController
from atreus.bridge.cache import SharedParticleCache
from atreus.config import DESKTOP_PARTICLE_COUNT, TARGET_FPS
from atreus.simulation.loop import SimulationLoop
from atreus.simulation.particles import ParticleSystem

BACKGROUND_COLOR = (8, 8, 16)


def run_desktop_simulation(
    particle_count: int = DESKTOP_PARTICLE_COUNT,
    target_fps: int = TARGET_FPS,
    system: ParticleSystem | None = None,
    cache: SharedParticleCache | None = None,
    controller: AgentController | None = None,
) -> None:
    """Run the pygame desktop simulation loop until the window is closed."""
    system = system if system is not None else ParticleSystem(count=particle_count)
    cache = cache if cache is not None else SharedParticleCache()
    controller = controller if controller is not None else AgentController()
    loop = SimulationLoop(system, cache, controller)

    pygame.init()
    screen = pygame.display.set_mode((int(system.width), int(system.height)))
    pygame.display.set_caption("Atreus Visual Engine - Desktop Simulation")
    clock = pygame.time.Clock()

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        system.paused = not system.paused
                    elif event.key == pygame.K_r:
                        system.reset()

            dt = clock.tick(target_fps) / 1000.0
            loop.tick(dt, fps=clock.get_fps())

            screen.fill(BACKGROUND_COLOR)
            positions = np.clip(
                system.positions, [0, 0], [system.width - 1, system.height - 1]
            ).astype(np.int32)
            colors = system.colors()
            pixels = pygame.surfarray.pixels3d(screen)
            pixels[positions[:, 0], positions[:, 1]] = colors
            del pixels
            pygame.display.set_caption(
                f"Atreus Visual Engine - {clock.get_fps():.1f} FPS - "
                f"iteration {system.iteration}"
            )
            pygame.display.flip()
    finally:
        loop.stop()
        pygame.quit()


def main() -> None:
    """Entry point for ``python -m atreus.simulation.desktop``."""
    run_desktop_simulation()


if __name__ == "__main__":
    main()
