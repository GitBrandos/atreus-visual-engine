"""Agent command handling bridging the mobile UI and the running simulation."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - avoids a runtime circular import
    from atreus.simulation.particles import ParticleSystem

#: Command actions understood by :class:`AgentController`.
SUPPORTED_COMMANDS = {"pause", "resume", "reset", "set_param"}


@dataclass
class AgentCommand:
    """A single command issued by the mobile web UI (or any other client)."""

    action: str
    payload: dict[str, Any] | None = None


class AgentController:
    """Thread-safe queue applying UI-issued commands to a `ParticleSystem`.

    Commands are submitted from the (async) server thread via :meth:`submit`
    and applied from the simulation thread via :meth:`apply_pending`, so the
    simulation loop is never blocked waiting on network I/O.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queue: list[AgentCommand] = []
        self.last_error: str | None = None

    def submit(self, command: AgentCommand) -> None:
        """Queue ``command`` for the simulation loop to apply."""
        if command.action not in SUPPORTED_COMMANDS:
            raise ValueError(f"Unsupported agent command: {command.action}")
        with self._lock:
            self._queue.append(command)

    def drain(self) -> list[AgentCommand]:
        """Pop and return all currently queued commands."""
        with self._lock:
            pending, self._queue = self._queue, []
        return pending

    def apply_pending(self, system: ParticleSystem) -> list[AgentCommand]:
        """Apply any queued commands to ``system``. Called from the sim loop."""
        applied = []
        for command in self.drain():
            try:
                if command.action == "pause":
                    system.paused = True
                elif command.action == "resume":
                    system.paused = False
                elif command.action == "reset":
                    system.reset()
                elif command.action == "set_param":
                    payload = command.payload or {}
                    system.set_param(payload["name"], payload["value"])
                applied.append(command)
            except Exception as exc:  # noqa: BLE001 - surfaced via last_error
                self.last_error = str(exc)
        return applied
