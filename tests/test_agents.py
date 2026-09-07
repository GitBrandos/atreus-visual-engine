"""Tests for the agent command controller."""

import pytest

from atreus.agents import AgentCommand, AgentController
from atreus.simulation.particles import ParticleSystem


def test_submit_rejects_unsupported_action():
    controller = AgentController()
    with pytest.raises(ValueError):
        controller.submit(AgentCommand(action="fly"))


def test_apply_pending_pauses_and_resumes():
    system = ParticleSystem(count=10, seed=1)
    controller = AgentController()

    controller.submit(AgentCommand(action="pause"))
    controller.apply_pending(system)
    assert system.paused is True

    controller.submit(AgentCommand(action="resume"))
    controller.apply_pending(system)
    assert system.paused is False


def test_apply_pending_resets_system():
    system = ParticleSystem(count=10, seed=2)
    system.step(1 / 60)
    controller = AgentController()
    controller.submit(AgentCommand(action="reset"))
    controller.apply_pending(system)
    assert system.iteration == 0


def test_apply_pending_set_param():
    system = ParticleSystem(count=10, seed=3)
    controller = AgentController()
    controller.submit(AgentCommand(action="set_param", payload={"name": "jitter", "value": 12.0}))
    controller.apply_pending(system)
    assert system.jitter == 12.0


def test_apply_pending_records_error_for_bad_param():
    system = ParticleSystem(count=10, seed=4)
    controller = AgentController()
    controller.submit(
        AgentCommand(action="set_param", payload={"name": "bogus", "value": 1.0})
    )
    controller.apply_pending(system)
    assert controller.last_error is not None


def test_drain_empties_queue():
    controller = AgentController()
    controller.submit(AgentCommand(action="pause"))
    controller.submit(AgentCommand(action="resume"))
    pending = controller.drain()
    assert len(pending) == 2
    assert controller.drain() == []
