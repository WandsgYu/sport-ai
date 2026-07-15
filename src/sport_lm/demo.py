from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .api.mock import SyntheticSportsAdapter
from .security.privacy import pseudonymize
from .tools import run_tool


ALLOWED_ITEMS = ("示例项目A", "示例项目B", "示例项目C", "示例项目D")
CONFIRM_WORDS = {"确认", "确认提交", "好的", "是", "yes", "confirm"}


@dataclass
class DemoTurn:
    reply: str
    tool_call: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None


@dataclass
class SyntheticAgentSession:
    """Deterministic offline policy around the same structured tool boundary."""

    adapter: SyntheticSportsAdapter
    subject_id: str = "subject-demo-001"
    session_id: str = "session-demo-001"
    pending_items: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    async def handle(self, message: str) -> DemoTurn:
        normalized = message.strip()
        selected = [item for item in ALLOWED_ITEMS if item in normalized]
        if selected:
            self.pending_items = selected
            self._record("parameters_collected", item_count=len(selected))
            return DemoTurn(
                reply=(
                    f"已收集项目：{'、'.join(selected)}。"
                    "这是一次状态变更，请回复“确认提交”。"
                )
            )

        if normalized.lower() in CONFIRM_WORDS:
            if not self.pending_items:
                self._record("confirmation_rejected", reason="missing_parameters")
                return DemoTurn(reply="尚未选择项目，请先告诉我要报名哪个示例项目。")

            arguments = {
                "user_data": {
                    "subject_id": self.subject_id,
                    "selected_items": self.pending_items,
                }
            }
            tool_call = {
                "type": "function",
                "function": {
                    "name": "update_user_data",
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
            idempotency_key = (
                f"{self.session_id}:update:{','.join(self.pending_items)}"
            )
            self._record("confirmation_accepted", item_count=len(self.pending_items))
            raw_result = await run_tool(
                "update_user_data",
                tool_call["function"]["arguments"],
                "",
                {"subject_id": self.subject_id},
                adapter=self.adapter,
                idempotency_key=idempotency_key,
            )
            result = json.loads(raw_result)
            if result.get("ErrCode") != 0:
                self._record("tool_failed", error_code=result.get("ErrCode"))
                return DemoTurn(
                    reply="提交失败，没有记录任何成功状态。",
                    tool_call=tool_call,
                    tool_result=result,
                )

            operation_id = result["data"]["operation_id"]
            self._record(
                "tool_succeeded",
                operation_ref=operation_id,
                idempotent_replay=bool(result.get("idempotent_replay")),
            )
            return DemoTurn(
                reply=f"创建成功：{operation_id}",
                tool_call=tool_call,
                tool_result=result,
            )

        self._record("parameters_requested")
        return DemoTurn(
            reply="请选择示例项目A、示例项目B、示例项目C或示例项目D。"
        )

    def _record(self, event_type: str, **metadata: Any) -> None:
        self.events.append(
            {
                "type": event_type,
                "subject_ref": pseudonymize(self.subject_id),
                **metadata,
            }
        )


async def run_scripted_demo() -> list[tuple[str, DemoTurn]]:
    session = SyntheticAgentSession(SyntheticSportsAdapter())
    transcript: list[tuple[str, DemoTurn]] = []
    for message in ("我要报名示例项目A", "确认提交"):
        transcript.append((message, await session.handle(message)))
    return transcript
