"""Abstract message-channel contract for the public reference snapshot.

The original channel SDK adapter, authentication flow, and wire protocol are
intentionally excluded. A real implementation must be designed and reviewed
for the target platform.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol


EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class MessageChannelClient(Protocol):
    def on(self, event: str, handler: EventHandler) -> "MessageChannelClient":
        ...

    async def reply_stream(
        self,
        frame: dict[str, Any],
        content: str,
        finish: bool = True,
        stream_id: str | None = None,
    ) -> str:
        ...

    async def reply_text(self, frame: dict[str, Any], content: str) -> None:
        ...
