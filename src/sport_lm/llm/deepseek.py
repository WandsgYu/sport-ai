from __future__ import annotations

from typing import Any, Iterable, Optional

import aiohttp

from .base import BaseLLM, LLMResponse, Message


class DeepSeekLLM(BaseLLM):
    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat") -> None:
        self.api_key = api_key
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
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, timeout=30
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                message = data.get("choices", [{}])[0].get("message", {})
                return LLMResponse(
                    content=message.get("content", "") or "",
                    tool_calls=message.get("tool_calls"),
                )
