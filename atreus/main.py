"""Atreus Visual Engine v0.1 - Earth Particle Sandbox

Main entry point for the Atreus system.

Running this module (``python -m atreus.main``) starts the full
synchronized system: the pygame desktop simulation and the FastAPI
mobile-streaming server, sharing the same simulation state. See
``atreus.synced_system`` for the implementation.
"""

from __future__ import annotations

from atreus.synced_system import main as run_synced_system


def main() -> None:
    """Entry point for ``python -m atreus.main``."""
    print("Atreus Visual Engine v0.1 initialized")
    run_synced_system()


if __name__ == "__main__":
    main()
