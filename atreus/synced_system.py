"""Command-line entry point for the Atreus synchronized system.

Runs the pygame desktop simulation and the FastAPI mobile-streaming server
together in a single process, sharing the same `ParticleSystem`,
`SharedParticleCache`, and `AgentController` instances so the mobile web UI
mirrors what is shown on the desktop window.
"""

from __future__ import annotations

import threading

import uvicorn

from atreus.agents import AgentController
from atreus.bridge.cache import SharedParticleCache
from atreus.config import DESKTOP_PARTICLE_COUNT, SERVER_HOST, SERVER_PORT, TARGET_FPS
from atreus.server.app import create_app
from atreus.simulation.desktop import run_desktop_simulation
from atreus.simulation.particles import ParticleSystem


def main() -> None:
    """Start the synchronized system: desktop window + streaming backend."""
    print("Atreus synchronized system initialized")

    system = ParticleSystem(count=DESKTOP_PARTICLE_COUNT)
    cache = SharedParticleCache()
    controller = AgentController()

    # The server drives its own headless copy of the stepping loop via
    # `SimulationLoop.run_headless`; here it shares the desktop's `system`,
    # `cache`, and `controller` instead of stepping a separate simulation.
    app = create_app(
        system=system,
        cache=cache,
        controller=controller,
        run_simulation=False,
    )
    server_config = uvicorn.Config(app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")
    server = uvicorn.Server(server_config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    try:
        run_desktop_simulation(
            particle_count=DESKTOP_PARTICLE_COUNT,
            target_fps=TARGET_FPS,
            system=system,
            cache=cache,
            controller=controller,
        )
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)


if __name__ == "__main__":
    main()

