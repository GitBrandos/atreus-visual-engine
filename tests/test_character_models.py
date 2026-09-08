"""Tests for the Character data model."""

import pytest
from pydantic import ValidationError

from atreus.character.models import Character, CharacterState, InteractionMode


def test_character_defaults():
    character = Character(id="nova", name="Nova")
    assert character.state == CharacterState.IDLE
    assert character.interaction_modes == [InteractionMode.CHAT]
    assert character.traits == {}
    assert character.interests == []


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
