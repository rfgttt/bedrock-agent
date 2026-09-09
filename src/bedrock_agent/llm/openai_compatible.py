from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from bedrock_agent.domain import Message, ModelResponse, Role, ToolCall


class OpenAICompatibleModel:
    """Adapter for DeepSeek's OpenAI-compatible Chat Completions API.

    The Agent core depends only on the LanguageModel protocol; provider details
    remain at this outer adapter boundary.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 60.0,
        max_retries: int = 1,
    ) -> None:
        if not api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY 为空。请在桌面端“模型配置”中填写，或复制 .env.example 为 .env。"
            )
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=max(5.0, timeout_seconds),
            max_retries=max(0, min(3, max_retries)),
        )
        self._model = model

    def close(self) -> None:
        self._client.close()

    @property
    def model_name(self) -> str:
        return self._model

    def probe(self) -> dict[str, Any]:
        """Verify authentication and report whether the configured model is listed."""
        response = self._client.models.list()
        model_ids = sorted(item.id for item in response.data)
        return {
            "ok": True,
            "configured_model": self._model,
            "model_available": self._model in model_ids,
            "models": model_ids,
        }

    def complete(self, messages: list[Message], tools: list[dict]) -> ModelResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[self._to_provider_message(message) for message in messages],
            tools=tools or None,
            tool_choice="auto" if tools else None,
            parallel_tool_calls=False if tools else None,
            temperature=0.1,
        )
        choice = response.choices[0].message
        calls: list[ToolCall] = []
        for call in choice.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"_invalid_json": call.function.arguments}
            calls.append(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=arguments,
                )
            )
        return ModelResponse(text=choice.content, tool_calls=calls)

    @staticmethod
    def _to_provider_message(message: Message) -> dict[str, Any]:
        if message.role is Role.ASSISTANT and message.tool_calls:
            return {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments, ensure_ascii=False),
                        },
                    }
                    for call in message.tool_calls
                ],
            }
        if message.role is Role.TOOL:
            return {
                "role": "tool",
                "tool_call_id": message.tool_call_id,
                "content": message.content or "",
            }
        return {"role": message.role.value, "content": message.content or ""}
