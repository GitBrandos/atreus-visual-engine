"""Tests for the isolated Monica character module."""

from atreus.character import ConversationState, MonicaCharacter, Personality


def test_personality_defaults_to_monica():
    personality = Personality()
    assert personality.name == "Monica"
    assert "curious" in personality.traits


def test_conversation_state_records_turns_in_order():
    state = ConversationState()
    state.add_turn("user", "hello")
    state.add_turn("monica", "hi there")
    history = state.history()
    assert [turn.role for turn in history] == ["user", "monica"]
    assert [turn.content for turn in history] == ["hello", "hi there"]


def test_conversation_state_reset_clears_history():
    state = ConversationState()
    state.add_turn("user", "hello")
    state.reset()
    assert state.history() == []


def test_monica_character_respond_records_both_turns():
    character = MonicaCharacter()
    reply = character.respond("hello")
    assert isinstance(reply, str)
    history = character.state.history()
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[0].content == "hello"
    assert history[1].role == "monica"
    assert history[1].content == reply


def test_monica_character_uses_custom_backend():
    class StaticBackend:
        def generate_reply(self, personality, history, message):
            return "static reply"

    character = MonicaCharacter(backend=StaticBackend())
    assert character.respond("hi") == "static reply"


def test_monica_character_default_name_used_in_default_reply():
    character = MonicaCharacter()
    reply = character.respond("test")
    assert "Monica" in reply
