"""Tests for the numpy-backed particle physics."""

from atreus.simulation.particles import ParticleSystem


def test_particle_system_initializes_within_bounds():
    system = ParticleSystem(count=500, width=100.0, height=50.0, seed=1)
    assert system.positions.shape == (500, 2)
    assert (system.positions[:, 0] >= 0).all()
    assert (system.positions[:, 0] <= 100.0).all()
    assert (system.positions[:, 1] >= 0).all()
    assert (system.positions[:, 1] <= 50.0).all()
    assert system.iteration == 0


def test_step_advances_iteration_and_moves_particles():
    system = ParticleSystem(count=200, seed=2)
    before = system.positions.copy()
    system.step(1 / 60)
    assert system.iteration == 1
    assert not (system.positions == before).all()


def test_pause_stops_stepping():
    system = ParticleSystem(count=50, seed=3)
    system.paused = True
    before = system.positions.copy()
    system.step(1 / 60)
    assert system.iteration == 0
    assert (system.positions == before).all()


def test_reset_reinitializes_state():
    system = ParticleSystem(count=50, seed=4)
    system.step(1 / 60)
    assert system.iteration == 1
    system.reset()
    assert system.iteration == 0


def test_colors_are_valid_rgb():
    system = ParticleSystem(count=100, seed=5)
    colors = system.colors()
    assert colors.shape == (100, 3)
    assert colors.dtype.name == "uint8"


def test_set_param_updates_physics_and_rejects_unknown():
    system = ParticleSystem(count=10, seed=6)
    system.set_param("attraction", 0.1)
    assert system.attraction == 0.1
    system.set_param("jitter", 3.0)
    assert system.jitter == 3.0
    try:
        system.set_param("unknown", 1.0)
        assert False, "expected ValueError"
    except ValueError:
        pass
