"""Tests for the FastAPI streaming backend (endpoints + WebSocket contract)."""

from fastapi.testclient import TestClient

from atreus.agents import AgentController
from atreus.bridge.cache import SharedParticleCache
from atreus.server.app import create_app
from atreus.simulation.particles import ParticleSystem


def _build_app_with_seeded_cache():
    """Create an app with `run_simulation=False` and a pre-populated cache.

    Avoids depending on background-thread timing in tests.
    """
    system = ParticleSystem(count=40, seed=1)
    cache = SharedParticleCache(sample_size=10)
    controller = AgentController()
    cache.update(system, fps=60.0, frame_time_ms=1.5)
    app = create_app(system=system, cache=cache, controller=controller, run_simulation=False)
    return app, system, cache, controller


def test_status_endpoint_reports_cached_metrics():
    app, *_ = _build_app_with_seeded_cache()
    with TestClient(app) as client:
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["particle_count"] == 40
        assert data["sample_count"] == 10
        assert data["fps"] == 60.0


def test_index_serves_mobile_page():
    app, *_ = _build_app_with_seeded_cache()
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Atreus Visual Engine" in response.text


def test_agent_command_endpoint_queues_command():
    app, _system, _cache, controller = _build_app_with_seeded_cache()
    with TestClient(app) as client:
        response = client.post("/api/agent-command", json={"action": "pause"})
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        pending = controller.drain()
        assert len(pending) == 1
        assert pending[0].action == "pause"


def test_agent_command_endpoint_rejects_unknown_action():
    app, *_ = _build_app_with_seeded_cache()
    with TestClient(app) as client:
        response = client.post("/api/agent-command", json={"action": "fly"})
        assert response.status_code == 200
        assert response.json()["ok"] is False


def test_websocket_receives_snapshot_and_can_send_commands():
    app, _system, _cache, controller = _build_app_with_seeded_cache()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/particles") as websocket:
            websocket.send_json({"action": "pause"})
            ack = websocket.receive_json()
            assert ack == {"type": "ack", "action": "pause"}
            pending = controller.drain()
            assert len(pending) == 1
            assert pending[0].action == "pause"
