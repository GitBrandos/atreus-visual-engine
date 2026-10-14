"""Tests for the Character data model."""

import pytest
from pydantic import ValidationError

from atreus.character.models import Character, CharacterState, InteractionMode, marker_color_for
from atreus.config import WORLD_HEIGHT, WORLD_WIDTH


def test_character_defaults():
    character = Character(id="nova", name="Nova")
    assert character.state == CharacterState.IDLE
    assert character.interaction_modes == [InteractionMode.CHAT]
    assert character.traits == {}
    assert character.interests == []
    assert character.position == (WORLD_WIDTH / 2, WORLD_HEIGHT / 2)


def test_character_trait_helper_returns_default_when_unset():
    character = Character(id="nova", name="Nova")
    assert character.trait("curiosity") == 0.5
    assert character.trait("curiosity", default=0.1) == 0.1


def test_character_trait_helper_returns_set_value():
    character = Character(id="nova", name="Nova", traits={"curiosity": 0.9})
    assert character.trait("curiosity") == 0.9


def test_character_rejects_out_of_range_trait():
    with pytest.raises(ValidationError):
        Character(id="nova", name="Nova", traits={"curiosity": 1.5})


def test_character_rejects_empty_id_or_name():
    with pytest.raises(ValidationError):
        Character(id="", name="Nova")
    with pytest.raises(ValidationError):
        Character(id="nova", name="")


def test_character_supports_multiple_interaction_modes():
    character = Character(
        id="nova",
        name="Nova",
        interaction_modes=[InteractionMode.CHAT, InteractionMode.NARRATION],
    )
    assert InteractionMode.NARRATION in character.interaction_modes


def test_character_accepts_position_within_world_bounds():
    character = Character(id="nova", name="Nova", position=(10.0, 20.0))
    assert character.position == (10.0, 20.0)


def test_character_rejects_position_outside_world_bounds():
    with pytest.raises(ValidationError):
        Character(id="nova", name="Nova", position=(-1.0, 0.0))
    with pytest.raises(ValidationError):
        Character(id="nova", name="Nova", position=(0.0, WORLD_HEIGHT + 1))


def test_marker_color_is_stable_and_bounded():
    color_a = marker_color_for("nova")
    color_b = marker_color_for("nova")
    assert color_a == color_b
    assert len(color_a) == 3
    assert all(0 <= channel <= 255 for channel in color_a)


def test_marker_color_differs_across_ids():
    assert marker_color_for("nova") != marker_color_for("zephyr")


def test_character_marker_color_matches_helper():
    character = Character(id="nova", name="Nova")
    assert character.marker_color == marker_color_for("nova")
