"""Tests for the Monica chat HTTP endpoint on the FastAPI server."""

from fastapi.testclient import TestClient

from atreus.agents import AgentController
from atreus.bridge.cache import SharedParticleCache
from atreus.server.app import create_app
from atreus.simulation.particles import ParticleSystem


def _build_app():
    system = ParticleSystem(count=10, seed=1)
    cache = SharedParticleCache(sample_size=5)
    controller = AgentController()
    cache.update(system, fps=60.0, frame_time_ms=1.5)
    return create_app(system=system, cache=cache, controller=controller, run_simulation=False)


def test_monica_chat_endpoint_returns_reply():
    app = _build_app()
    with TestClient(app) as client:
        response = client.post("/api/monica-chat", json={"message": "hello"})
        assert response.status_code == 200
        data = response.json()
        assert "Monica" in data["reply"]


def test_monica_chat_endpoint_preserves_conversation_state():
    app = _build_app()
    with TestClient(app) as client:
        client.post("/api/monica-chat", json={"message": "first"})
        client.post("/api/monica-chat", json={"message": "second"})
        history = app.state.monica.state.history()
        assert [turn.content for turn in history] == [
            "first",
            "Monica: I heard you say 'first'.",
            "second",
            "Monica: I heard you say 'second'.",
        ]


def test_index_page_includes_monica_panel():
    app = _build_app()
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "Monica" in response.text
        assert 'id="monica-input"' in response.text
