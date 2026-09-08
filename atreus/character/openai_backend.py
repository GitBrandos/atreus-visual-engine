"""OpenAI-backed reply generation for the Monica character.

Reads the API key from the ``OPENAI_API_KEY`` environment variable -- it is
never hard-coded or committed to source control. Set it in your shell or in
a local (git-ignored) ``.env`` file before using this backend; see the
README for setup instructions.

This module has no dependency on the rest of Atreus (simulation, protocol,
agents, server); it only implements the :class:`atreus.character.monica.ReplyBackend`
interface so it can be passed to :class:`~atreus.character.monica.MonicaCharacter`.
"""

from __future__ import annotations

import os

import httpx

from atreus.character.monica import ConversationTurn, Personality

#: Default OpenAI chat completions endpoint.
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

#: Default model used for Monica's replies.
DEFAULT_MODEL = "gpt-4o-mini"

#: Name of the environment variable holding the OpenAI API key.
API_KEY_ENV_VAR = "OPENAI_API_KEY"


class OpenAIReplyBackend:
    """Generates Monica's replies via the OpenAI Chat Completions API.

    Parameters
    ----------
    api_key:
        Explicit API key to use. If not provided, it is read from the
        ``OPENAI_API_KEY`` environment variable when the backend is
        constructed.
    model:
        Chat completion model name.
    timeout:
        Request timeout, in seconds.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
    ) -> None:
        resolved_key = api_key or os.environ.get(API_KEY_ENV_VAR)
        if not resolved_key:
            raise RuntimeError(
                f"OpenAI API key not found. Set the {API_KEY_ENV_VAR} "
                "environment variable before using OpenAIReplyBackend."
            )
        self._api_key = resolved_key
        self.model = model
        self.timeout = timeout

    def _build_messages(
        self,
        personality: Personality,
        history: list[ConversationTurn],
        message: str,
    ) -> list[dict[str, str]]:
        system_prompt = (
            f"You are {personality.name}, {personality.description} "
            f"Speak in a {personality.tone} tone. "
            f"Character traits: {', '.join(personality.traits)}."
        )
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role = "assistant" if turn.role == personality.name.lower() else "user"
            messages.append({"role": role, "content": turn.content})
        messages.append({"role": "user", "content": message})
        return messages

    def generate_reply(
        self,
        personality: Personality,
        history: list[ConversationTurn],
        message: str,
    ) -> str:
        """Return Monica's reply to ``message`` using the OpenAI API."""
        payload = {
            "model": self.model,
            "messages": self._build_messages(personality, history, message),
        }
        headers = {"Authorization": "Bearer " + self._api_key}
        response = httpx.post(
            OPENAI_API_URL, json=payload, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
