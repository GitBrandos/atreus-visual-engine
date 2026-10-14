"""Tests for `SimulationLoop` reflecting character markers in cache snapshots."""

from atreus.agents import AgentController
from atreus.bridge.cache import SharedParticleCache
from atreus.character.models import Character, CharacterState
from atreus.character.registry import CharacterRegistry
from atreus.simulation.loop import SimulationLoop
from atreus.simulation.particles import ParticleSystem


def test_tick_without_registry_leaves_character_markers_empty():
    system = ParticleSystem(count=10, seed=1)
    cache = SharedParticleCache(sample_size=5)
    controller = AgentController()
    loop = SimulationLoop(system, cache, controller)

    loop.tick(dt=1 / 60, fps=60.0)

    snapshot = cache.snapshot()
    assert snapshot is not None
    assert snapshot.character_markers == []


def test_tick_with_registry_reflects_character_marker():
    system = ParticleSystem(count=10, seed=1)
    cache = SharedParticleCache(sample_size=5)
    controller = AgentController()
    registry = CharacterRegistry()
    character = registry.create(
        Character(id="nova", name="Nova", state=CharacterState.REACTING, position=(100.0, 200.0))
    )
    loop = SimulationLoop(system, cache, controller, character_registry=registry)

    loop.tick(dt=1 / 60, fps=60.0)

    snapshot = cache.snapshot()
    assert snapshot is not None
    assert len(snapshot.character_markers) == 1
    marker = snapshot.character_markers[0]
    assert marker["id"] == "nova"
    assert marker["name"] == "Nova"
    # Characters drift/wander a little every tick (see `atreus.character.movement`),
    # so the marker position won't be pixel-identical to the registered
    # position, but a single 1/60s tick should only move it a tiny amount.
    assert len(marker["position"]) == 2
    moved_x, moved_y = marker["position"]
    assert abs(moved_x - 100.0) < 5.0
    assert abs(moved_y - 200.0) < 5.0
    assert marker["state"] == "reacting"
    assert marker["color"] == character.marker_color


def test_tick_moves_character_position_over_time():
    system = ParticleSystem(count=10, seed=1)
    cache = SharedParticleCache(sample_size=5)
    controller = AgentController()
    registry = CharacterRegistry()
    registry.create(Character(id="nova", name="Nova", position=(640.0, 360.0)))
    loop = SimulationLoop(system, cache, controller, character_registry=registry)

    for _ in range(120):
        loop.tick(dt=1 / 60, fps=60.0)

    moved = registry.get("nova").position
    assert moved != (640.0, 360.0)
    # Movement stays within the world bounds.
    assert 0.0 <= moved[0] <= system.width
    assert 0.0 <= moved[1] <= system.height
