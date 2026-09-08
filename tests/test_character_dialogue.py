"""Tests for the default template-based dialogue engine."""

from atreus.character.dialogue import TemplateDialogueEngine
from atreus.character.models import Character, CharacterState


def test_empty_message_yields_idle_state():
    engine = TemplateDialogueEngine()
    character = Character(id="nova", name="Nova")
    turn = engine.respond(character, "   ")
    assert turn.state == CharacterState.IDLE
    assert "Nova" in turn.text


def test_humour_marker_yields_reacting_state():
    engine = TemplateDialogueEngine()
    character = Character(id="nova", name="Nova")
    turn = engine.respond(character, "haha that's funny")
    assert turn.state == CharacterState.REACTING


def test_plain_message_yields_active_state():
    engine = TemplateDialogueEngine()
    character = Character(id="nova", name="Nova")
    turn = engine.respond(character, "Hello there")
    assert turn.state == CharacterState.ACTIVE


def test_curious_character_mentions_an_interest():
    engine = TemplateDialogueEngine()
    character = Character(
        id="nova", name="Nova", traits={"curiosity": 0.9}, interests=["astronomy"]
    )
    turn = engine.respond(character, "Hello there")
    assert "astronomy" in turn.text
