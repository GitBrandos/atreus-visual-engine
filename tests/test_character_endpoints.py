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
        assert len(data["position"]) == 2
        assert len(data["marker_color"]) == 3


def test_create_character_accepts_explicit_position():
    app, _registry = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/characters",
            json={"id": "nova", "name": "Nova", "position": [100, 200]},
        )
        assert response.status_code == 200
        assert response.json()["position"] == [100.0, 200.0]


def test_create_character_rejects_out_of_bounds_position():
    app, _registry = _build_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/characters",
            json={"id": "nova", "name": "Nova", "position": [-5, 0]},
        )
        assert response.status_code == 422


def test_create_character_marker_color_is_stable():
    app, registry = _build_app()
    with TestClient(app) as client:
        response = client.post("/api/characters", json={"id": "nova", "name": "Nova"})
        color = response.json()["marker_color"]
        assert color == registry.get("nova").marker_color


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


def test_concurrent_messages_to_different_characters_do_not_cross_talk():
    """Hammers `/message` for several distinct characters concurrently and
    checks each character's final state/registry entry only ever reflects
    replies addressed to it -- i.e. the shared registry lock doesn't let one
    character's update clobber or leak into another's."""
    import concurrent.futures

    app, registry = _build_app()
    character_ids = [f"char-{i}" for i in range(8)]
    with TestClient(app) as client:
        for character_id in character_ids:
            client.post("/api/characters", json={"id": character_id, "name": character_id})

        def send(character_id: str) -> tuple[str, int, str]:
            response = client.post(
                f"/api/characters/{character_id}/message",
                json={"message": f"hello from {character_id}"},
            )
            return character_id, response.status_code, response.json()["text"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(send, character_ids * 5))

        for character_id, status_code, text in results:
            assert status_code == 200
            assert character_id in text  # each reply echoes only its own character's message

        for character_id in character_ids:
            assert registry.get(character_id).id == character_id
            assert registry.get(character_id).state.value == "active"


def test_concurrent_messages_to_same_character_are_serialized_safely():
    """Many concurrent messages to a single character should all succeed and
    leave the registry in a consistent (not corrupted/partially-written) state."""
    import concurrent.futures

    app, registry = _build_app()
    with TestClient(app) as client:
        client.post("/api/characters", json={"id": "nova", "name": "Nova"})

        def send(i: int) -> int:
            response = client.post("/api/characters/nova/message", json={"message": f"msg {i}"})
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            statuses = list(executor.map(send, range(50)))

        assert all(status == 200 for status in statuses)
        final = registry.get("nova")
        assert final.id == "nova"
        assert final.name == "Nova"
        assert final.state.value == "active"
