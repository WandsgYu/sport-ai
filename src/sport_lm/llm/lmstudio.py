from __future__ import annotations

from typing import Any, Iterable, Optional

import aiohttp

from .base import BaseLLM, LLMResponse, Message


class LMStudioLLM(BaseLLM):
    def __init__(self, base_url: str, model: str = "local-model") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        messages: Iterable[Message],
        temperature: float = 0.7,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> LLMResponse:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=30) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                message = data.get("choices", [{}])[0].get("message", {})
                return LLMResponse(
                    content=message.get("content", "") or "",
                    tool_calls=message.get("tool_calls"),
                )
