"""Tests for the thread-safe down-sampling cache."""

from atreus.bridge.cache import SharedParticleCache
from atreus.simulation.particles import ParticleSystem


def test_cache_starts_empty():
    cache = SharedParticleCache(sample_size=10)
    assert cache.snapshot() is None


def test_cache_downsamples_to_sample_size():
    system = ParticleSystem(count=1000, seed=1)
    cache = SharedParticleCache(sample_size=250)
    snapshot = cache.update(system)
    assert snapshot.sample_count == 250
    assert snapshot.particle_count == 1000
    assert len(snapshot.positions) == 250
    assert len(snapshot.colors) == 250


def test_cache_keeps_all_particles_when_smaller_than_sample_size():
    system = ParticleSystem(count=50, seed=2)
    cache = SharedParticleCache(sample_size=2500)
    snapshot = cache.update(system)
    assert snapshot.sample_count == 50
    assert len(snapshot.positions) == 50


def test_snapshot_reflects_iteration_and_metrics():
    system = ParticleSystem(count=20, seed=3)
    system.step(1 / 60)
    cache = SharedParticleCache(sample_size=10)
    snapshot = cache.update(system, fps=59.5, frame_time_ms=1.23)
    assert snapshot.iteration == 1
    assert snapshot.fps == 59.5
    assert snapshot.frame_time_ms == 1.23


def test_to_dict_is_json_friendly():
    system = ParticleSystem(count=20, seed=4)
    cache = SharedParticleCache(sample_size=5)
    snapshot = cache.update(system)
    data = snapshot.to_dict()
    assert set(data.keys()) == {
        "positions",
        "colors",
        "iteration",
        "timestamp",
        "particle_count",
        "sample_count",
        "fps",
        "frame_time_ms",
    }
