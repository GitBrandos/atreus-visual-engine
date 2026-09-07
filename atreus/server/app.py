"""FastAPI backend streaming down-sampled particle snapshots to mobile clients.

Data flow
---------
``ParticleSystem`` (numpy) --step()--> ``SharedParticleCache`` (down-sampled,
refreshed every ``CACHE_SYNC_INTERVAL_MS``) --broadcast loop--> WebSocket
clients (every ``STREAM_INTERVAL_MS``).

Running ``create_app()`` standalone (e.g. via ``uvicorn atreus.server.app:app``)
spins up its own background simulation thread so the server works without a
desktop process. When wired up by :mod:`atreus.synced_system`, the same
``ParticleSystem``/``SharedParticleCache``/``AgentController`` instances used
by the pygame desktop loop can be injected instead, so the mobile stream
mirrors exactly what is shown on the desktop window.
"""

from __future__ import annotations

import asyncio
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from atreus.agents import AgentCommand, AgentController
from atreus.bridge.cache import SharedParticleCache
from atreus.config import DESKTOP_PARTICLE_COUNT, STREAM_INTERVAL_MS, TARGET_FPS
from atreus.protocol import AgentCommandMessage, StatusMessage
from atreus.simulation.loop import SimulationLoop
from atreus.simulation.particles import ParticleSystem

STATIC_DIR = Path(__file__).parent / "static"


class ConnectionManager:
    """Tracks connected WebSocket clients and broadcasts snapshots to them."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        async with self._lock:
            connections = list(self._connections)
        stale = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:  # noqa: BLE001 - drop unreachable clients
                stale.append(connection)
        if stale:
            async with self._lock:
                for connection in stale:
                    self._connections.discard(connection)

    def count(self) -> int:
        return len(self._connections)


def create_app(
    system: ParticleSystem | None = None,
    cache: SharedParticleCache | None = None,
    controller: AgentController | None = None,
    run_simulation: bool = True,
    particle_count: int = DESKTOP_PARTICLE_COUNT,
    target_fps: int = TARGET_FPS,
) -> FastAPI:
    """Build the FastAPI streaming app.

    If ``run_simulation`` is ``True`` (default) and no ``system``/``cache``/
    ``controller`` are injected, the app starts its own headless background
    simulation thread on startup so it can run independently of the desktop
    process.
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.run_simulation:
            thread = threading.Thread(
                target=app.state.loop.run_headless,
                kwargs={"target_fps": target_fps},
                daemon=True,
            )
            app.state.sim_thread = thread
            thread.start()
        app.state.broadcast_task = asyncio.create_task(_broadcast_loop(app))
        try:
            yield
        finally:
            app.state.loop.stop()
            task = getattr(app.state, "broadcast_task", None)
            if task is not None:
                task.cancel()

    app = FastAPI(title="Atreus Visual Engine Streaming API", lifespan=lifespan)

    app.state.system = system if system is not None else ParticleSystem(count=particle_count)
    app.state.cache = cache if cache is not None else SharedParticleCache()
    app.state.controller = controller if controller is not None else AgentController()
    app.state.manager = ConnectionManager()
    app.state.loop = SimulationLoop(app.state.system, app.state.cache, app.state.controller)
    app.state.sim_thread = None
    app.state.run_simulation = run_simulation
    app.state.started_at = time.time()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        html_path = STATIC_DIR / "index.html"
        if not html_path.exists():
            return HTMLResponse("<h1>Atreus mobile UI not found</h1>", status_code=404)
        return HTMLResponse(html_path.read_text())

    @app.get("/api/status", response_model=StatusMessage)
    async def status() -> StatusMessage:
        snapshot = app.state.cache.snapshot()
        last_update_age_ms = None
        if snapshot is not None:
            last_update_age_ms = (time.time() - snapshot.timestamp) * 1000.0
        sim_thread = app.state.sim_thread
        return StatusMessage(
            running=bool(sim_thread and sim_thread.is_alive()),
            connected_clients=app.state.manager.count(),
            iteration=snapshot.iteration if snapshot else app.state.system.iteration,
            particle_count=snapshot.particle_count if snapshot else app.state.system.count,
            sample_count=snapshot.sample_count if snapshot else 0,
            fps=snapshot.fps if snapshot else 0.0,
            frame_time_ms=snapshot.frame_time_ms if snapshot else 0.0,
            last_update_age_ms=last_update_age_ms,
        )

    @app.post("/api/agent-command")
    async def agent_command(message: AgentCommandMessage) -> dict:
        try:
            app.state.controller.submit(
                AgentCommand(action=message.action, payload=message.payload)
            )
        except ValueError:
            return {"ok": False, "error": f"Unsupported action: {message.action}"}
        return {"ok": True}

    @app.websocket("/ws/particles")
    async def particles_ws(websocket: WebSocket) -> None:
        await app.state.manager.connect(websocket)
        try:
            while True:
                raw = await websocket.receive_json()
                try:
                    message = AgentCommandMessage(**raw)
                    app.state.controller.submit(
                        AgentCommand(action=message.action, payload=message.payload)
                    )
                    await websocket.send_json({"type": "ack", "action": message.action})
                except (ValueError, TypeError):
                    action = raw.get("action") if isinstance(raw, dict) else None
                    await websocket.send_json({"type": "error", "error": f"Invalid command: {action}"})
        except WebSocketDisconnect:
            pass
        finally:
            await app.state.manager.disconnect(websocket)

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    return app


async def _broadcast_loop(app: FastAPI) -> None:
    """Periodically push the latest cache snapshot to all connected clients."""
    interval = STREAM_INTERVAL_MS / 1000.0
    while True:
        await asyncio.sleep(interval)
        snapshot = app.state.cache.snapshot()
        if snapshot is None:
            continue
        message = snapshot.to_dict()
        message["type"] = "snapshot"
        await app.state.manager.broadcast(message)


#: Module-level app so ``uvicorn atreus.server.app:app`` works standalone.
app = create_app()
