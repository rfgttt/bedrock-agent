from __future__ import annotations

from typing import Protocol

from bedrock_agent.domain import Message, ModelResponse


class LanguageModel(Protocol):
    def complete(self, messages: list[Message], tools: list[dict]) -> ModelResponse:
        """Return either final text or one tool call."""
        ...
