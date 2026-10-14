"""Per-tick movement for registered characters.

Markers previously stayed glued to their initial `position` forever. This
module gives each character a gentle, continuous motion so it reads as
"present" in the simulated world rather than a static pin dropped on a map:

- **Wander**: a small random nudge every tick, independent of the particle
  field, so a character never sits perfectly still even in an empty world.
- **Drift toward density**: characters are mildly pulled toward the local
  centroid of nearby particles, so they visibly react to the particle field
  around them (drifting toward denser clusters) without needing any new
  dependency between the physics core and the character system beyond
  reading `ParticleSystem.positions`.

Movement intentionally does not persist to disk on every tick (see
`CharacterRegistry.set_position`): it is cheap to recompute and happens far
too often to justify a disk write per character per frame.
"""

from __future__ import annotations

import numpy as np

from atreus.simulation.particles import ParticleSystem

#: How strongly characters wander randomly, in world units/second (stddev).
WANDER_STRENGTH = 12.0

#: How strongly characters drift toward the local particle centroid,
#: as a fraction of the distance to that centroid covered per second.
DRIFT_STRENGTH = 0.35

#: Radius (world units) within which particles count toward a character's
#: local density centroid.
SENSE_RADIUS = 150.0


def step_characters(registry, system: ParticleSystem, dt: float, rng: np.random.Generator | None = None) -> None:
    """Advance every registered character's position by one simulation step.

    ``registry`` is an :class:`atreus.character.registry.CharacterRegistry`
    (not type-hinted directly to avoid a circular import, since the registry
    module doesn't otherwise need to know about `ParticleSystem`). No-op if
    there are no registered characters.
    """
    characters = registry.list()
    if not characters:
        return

    rng = rng if rng is not None else np.random.default_rng()
    positions = system.positions
    radius_sq = SENSE_RADIUS * SENSE_RADIUS

    for character in characters:
        here = np.array(character.position, dtype=np.float64)

        drift = np.zeros(2, dtype=np.float64)
        if positions.size:
            offsets = positions.astype(np.float64) - here
            dist_sq = np.einsum("ij,ij->i", offsets, offsets)
            nearby = dist_sq < radius_sq
            if np.any(nearby):
                centroid = positions[nearby].astype(np.float64).mean(axis=0)
                drift = (centroid - here) * DRIFT_STRENGTH

        wander = rng.normal(0.0, WANDER_STRENGTH, size=2)
        new_position = here + (drift + wander) * dt
        new_position[0] = float(np.clip(new_position[0], 0.0, system.width))
        new_position[1] = float(np.clip(new_position[1], 0.0, system.height))

        registry.set_position(character.id, (float(new_position[0]), float(new_position[1])))
