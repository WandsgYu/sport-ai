from __future__ import annotations

import json
import logging
from typing import Any

from .api.sports import query_user_info, update_user_data
from .security.privacy import pseudonymize
from .sop.parser import build_sop_context


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "textfetch_scene_sop",
            "description": "获取脱敏教学场景的流程说明",
            "parameters": {
                "type": "object",
                "properties": {"scene_id": {"type": "string"}},
                "required": ["scene_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_user_info",
            "description": "查询当前匿名主体的示例状态；公开版始终返回不可用",
            "parameters": {
                "type": "object",
                "properties": {"subject_id": {"type": "string"}},
                "required": ["subject_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_user_data",
            "description": "提交当前匿名主体的示例项目选择；公开版始终返回不可用",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_data": {
                        "type": "object",
                        "properties": {
                            "subject_id": {"type": "string"},
                            "selected_items": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["subject_id", "selected_items"],
                    }
                },
                "required": ["user_data"],
            },
        },
    },
]


async def run_tool(
    name: str,
    arguments: str,
    sop_path: str,
    user_info: dict[str, Any] | None = None,
    *,
    adapter: Any | None = None,
    idempotency_key: str = "",
) -> str:
    try:
        payload = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        payload = {}

    if name == "textfetch_scene_sop":
        scene_id = str(payload.get("scene_id", "")).strip()
        if not scene_id:
            return "scene_id 为空。"
        return build_sop_context([scene_id], sop_path) or "未找到对应场景。"

    current_subject = str((user_info or {}).get("subject_id", "")).strip()
    if not current_subject:
        return _json_error(403, "无法确认当前匿名主体。")

    if name == "query_user_info":
        requested_subject = str(payload.get("subject_id", "")).strip()
        if requested_subject and requested_subject != current_subject:
            logging.getLogger("security").warning(
                "query_blocked reason=subject_mismatch subject_ref=%s",
                pseudonymize(current_subject),
            )
            return _json_error(403, "禁止查询其他主体。")
        result = (
            await adapter.query_user_info(current_subject)
            if adapter is not None
            else await query_user_info(current_subject)
        )
        return json.dumps(result, ensure_ascii=False)

    if name == "update_user_data":
        user_data = payload.get("user_data")
        if not isinstance(user_data, dict):
            return _json_error(400, "user_data 格式不正确。")
        requested_subject = str(user_data.get("subject_id", "")).strip()
        if requested_subject and requested_subject != current_subject:
            return _json_error(403, "禁止修改其他主体。")
        safe_payload = {
            "subject_id": current_subject,
            "selected_items": _normalize_items(user_data.get("selected_items")),
        }
        result = (
            await adapter.update_user_data(
                safe_payload,
                idempotency_key=idempotency_key or "missing-idempotency-key",
            )
            if adapter is not None
            else await update_user_data(safe_payload)
        )
        return json.dumps(result, ensure_ascii=False)

    return _json_error(404, "未实现的工具。")


def _normalize_items(value: Any) -> list[str]:
    allowed = {"示例项目A", "示例项目B", "示例项目C", "示例项目D"}
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item) in allowed][:4]


def _json_error(code: int, message: str) -> str:
    return json.dumps(
        {"ErrCode": code, "Message": message, "data": None},
        ensure_ascii=False,
    )
