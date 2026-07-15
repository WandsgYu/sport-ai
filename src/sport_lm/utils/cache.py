from __future__ import annotations

import asyncio
from typing import Any


class UserCache:
    def __init__(self, max_turns: int = 10) -> None:
        self._max_turns = max_turns
        self._data: dict[str, list[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def add_message(self, wecom_id: str, role: str, content: str) -> None:
        if not wecom_id:
            return
        if role not in ("user", "assistant"):
            return
        async with self._lock:
            history = self._data.setdefault(wecom_id, [])
            history.append({"role": role, "content": content})
            # 保留最近 N 轮（每轮两条消息，使用 2*max_turns 作为上限）
            limit = self._max_turns * 2
            if len(history) > limit:
                self._data[wecom_id] = history[-limit:]

    async def get_recent_history(self, wecom_id: str, limit: int = 8) -> list[dict[str, Any]]:
        if not wecom_id:
            return []
        async with self._lock:
            history = list(self._data.get(wecom_id, []))
        return history[-limit:]
