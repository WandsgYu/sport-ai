from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterable, Optional

Message = dict[str, Any]


@dataclass
class LLMResponse:
    content: str
    tool_calls: Optional[list[dict[str, Any]]] = None


class BaseLLM(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: Iterable[Message],
        temperature: float = 0.7,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> LLMResponse:
        raise NotImplementedError
