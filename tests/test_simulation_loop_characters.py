"""Tests for `SimulationLoop` reflecting character state in cache snapshots."""

from atreus.agents import AgentController
from atreus.bridge.cache import SharedParticleCache
from atreus.character.models import Character, CharacterState
from atreus.character.registry import CharacterRegistry
from atreus.simulation.loop import SimulationLoop
from atreus.simulation.particles import ParticleSystem


def test_tick_without_registry_leaves_character_states_empty():
    system = ParticleSystem(count=10, seed=1)
    cache = SharedParticleCache(sample_size=5)
    controller = AgentController()
    loop = SimulationLoop(system, cache, controller)

    loop.tick(dt=1 / 60, fps=60.0)

    snapshot = cache.snapshot()
    assert snapshot is not None
    assert snapshot.character_states == {}


def test_tick_with_registry_reflects_character_state():
    system = ParticleSystem(count=10, seed=1)
    cache = SharedParticleCache(sample_size=5)
    controller = AgentController()
    registry = CharacterRegistry()
    registry.create(Character(id="nova", name="Nova", state=CharacterState.REACTING))
    loop = SimulationLoop(system, cache, controller, character_registry=registry)

    loop.tick(dt=1 / 60, fps=60.0)

    snapshot = cache.snapshot()
    assert snapshot is not None
    assert snapshot.character_states == {"nova": "reacting"}
