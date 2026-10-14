"""Tests for per-tick character movement (`atreus.character.movement`)."""

from __future__ import annotations

import numpy as np

from atreus.character.models import Character
from atreus.character.movement import step_characters
from atreus.character.registry import CharacterRegistry
from atreus.simulation.particles import ParticleSystem


def test_step_characters_is_noop_with_no_characters():
    registry = CharacterRegistry()
    system = ParticleSystem(count=10, seed=1)
    # Should not raise, and should not touch the particle system.
    before = system.positions.copy()
    step_characters(registry, system, dt=1 / 60)
    assert np.array_equal(system.positions, before)


def test_step_characters_moves_position_but_stays_in_bounds():
    registry = CharacterRegistry()
    registry.create(Character(id="nova", name="Nova", position=(640.0, 360.0)))
    system = ParticleSystem(count=200, seed=1)

    rng = np.random.default_rng(42)
    for _ in range(200):
        step_characters(registry, system, dt=1 / 60, rng=rng)

    position = registry.get("nova").position
    assert position != (640.0, 360.0)
    assert 0.0 <= position[0] <= system.width
    assert 0.0 <= position[1] <= system.height


def test_step_characters_is_deterministic_with_seeded_rng():
    system = ParticleSystem(count=50, seed=1)

    registry_a = CharacterRegistry()
    registry_a.create(Character(id="nova", name="Nova", position=(640.0, 360.0)))
    step_characters(registry_a, system, dt=1 / 60, rng=np.random.default_rng(7))

    registry_b = CharacterRegistry()
    registry_b.create(Character(id="nova", name="Nova", position=(640.0, 360.0)))
    step_characters(registry_b, system, dt=1 / 60, rng=np.random.default_rng(7))

    assert registry_a.get("nova").position == registry_b.get("nova").position


def test_step_characters_drifts_toward_nearby_particle_cluster():
    """A character placed right next to a dense cluster should drift toward it
    more than pure random wander alone would typically produce in one tick."""
    system = ParticleSystem(count=1, seed=1)
    system.positions[:] = np.array([[700.0, 360.0]], dtype=np.float32)
    system.velocities[:] = 0.0

    registry = CharacterRegistry()
    registry.create(Character(id="nova", name="Nova", position=(640.0, 360.0)))

    # Zero wander (rng always returns 0) isolates the drift-toward-density term.
    class _ZeroRng:
        def normal(self, loc, scale, size):
            return np.zeros(size)

    step_characters(registry, system, dt=1.0, rng=_ZeroRng())
    position = registry.get("nova").position
    assert position[0] > 640.0  # moved toward the cluster at x=700
    assert position[1] == 360.0


def test_step_characters_does_not_persist_to_store():
    from tests.test_character_registry import _RecordingStore

    store = _RecordingStore(initial={"nova": Character(id="nova", name="Nova")})
    registry = CharacterRegistry(store=store)
    system = ParticleSystem(count=10, seed=1)

    step_characters(registry, system, dt=1 / 60)

    assert store.saved == []
