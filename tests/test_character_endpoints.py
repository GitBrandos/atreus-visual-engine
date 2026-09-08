"""Tests for the character CRUD/message endpoints on the FastAPI backend."""

from fastapi.testclient import TestClient

from atreus.agents import AgentController
from atreus.bridge.cache import SharedParticleCache
from atreus.character.registry import CharacterRegistry
from atreus.server.app import create_app
from atreus.simulation.particles import ParticleSystem


def _build_app():
    system = ParticleSystem(count=10, seed=1)
    cache = SharedParticleCache(sample_size=5)
    controller = AgentController()
    cache.update(system)
    registry = CharacterRegistry()
    app = create_app(
        system=system,
        cache=cache,
        controller=controller,
        run_simulation=False,
        character_registry=registry,
    )
    return app, registry


def test_create_character_returns_stored_character():
    app, _registry = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/characters",
            json={"id": "nova", "name": "Nova", "traits": {"curiosity": 0.8}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "nova"
        assert data["name"] == "Nova"
        assert data["state"] == "idle"


def test_create_character_rejects_duplicate_id():
    app, _registry = _build_app()
    with TestClient(app) as client:
        client.post("/api/characters", json={"id": "nova", "name": "Nova"})
        response = client.post("/api/characters", json={"id": "nova", "name": "Nova 2"})
        assert response.status_code == 409


def test_create_character_rejects_out_of_range_trait():
    app, _registry = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/characters",
            json={"id": "nova", "name": "Nova", "traits": {"curiosity": 2.0}},
        )
        assert response.status_code == 422


def test_list_characters_returns_all_registered():
    app, registry = _build_app()
    with TestClient(app) as client:
        client.post("/api/characters", json={"id": "a", "name": "A"})
        client.post("/api/characters", json={"id": "b", "name": "B"})
        response = client.get("/api/characters")
        assert response.status_code == 200
        ids = {c["id"] for c in response.json()}
        assert ids == {"a", "b"}


def test_get_character_not_found_returns_404():
    app, _registry = _build_app()
    with TestClient(app) as client:
        response = client.get("/api/characters/missing")
        assert response.status_code == 404


def test_message_character_returns_reply_and_updates_state():
    app, registry = _build_app()
    with TestClient(app) as client:
        client.post("/api/characters", json={"id": "nova", "name": "Nova"})
        response = client.post("/api/characters/nova/message", json={"message": "hi there"})
        assert response.status_code == 200
        data = response.json()
        assert "hi there" in data["text"]
        assert data["state"] == "active"
        assert registry.get("nova").state.value == "active"


def test_message_unknown_character_returns_404():
    app, _registry = _build_app()
    with TestClient(app) as client:
        response = client.post("/api/characters/missing/message", json={"message": "hi"})
        assert response.status_code == 404
