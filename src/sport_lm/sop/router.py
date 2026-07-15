from __future__ import annotations

import json
import re
from typing import Any

from ..llm.base import BaseLLM
from ..prompts import get_scene_select_prompt
from .parser import get_modify_scene_ids, get_scene_ids_by_keywords

JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


async def select_scene_ids(
    llm: BaseLLM,
    scene_menu: str,
    user_message: str,
    sop_path: str,
) -> list[str]:
    prompt = get_scene_select_prompt(scene_menu)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        response = await llm.generate(messages, temperature=0.0)
    except Exception:
        return []

    data = _safe_load_json(response.content)
    if not data:
        base = []
    else:
        scene_ids = data.get("scene_ids") or data.get("scenes") or []
        base = _normalize_scene_ids(scene_ids)

    # 报名意图优先加入报名相关场景
    if _has_signup_intent(user_message):
        signup_ids = get_scene_ids_by_keywords(sop_path, ["报名", "选项目", "项目"])
        for scene_id in signup_ids:
            if scene_id not in base:
                base.append(scene_id)

    # 修改意图优先加入修改相关场景
    if _has_modify_intent(user_message):
        modify_ids = get_modify_scene_ids(sop_path)
        for scene_id in modify_ids:
            if scene_id not in base:
                base.append(scene_id)

    base = _prioritize_and_trim(base, user_message, sop_path)
    return base


def _safe_load_json(raw: str) -> dict[str, Any]:
    if not raw:
        return {}

    raw = raw.strip().strip("`")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = JSON_BLOCK_RE.search(raw)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def _normalize_scene_ids(scene_ids: Any) -> list[str]:
    if not isinstance(scene_ids, list):
        return []

    normalized: list[str] = []
    for item in scene_ids:
        if isinstance(item, str):
            candidate = item.strip()
            if "：" in candidate:
                candidate = candidate.split("：", 1)[0].strip()
            if candidate.startswith("场景"):
                normalized.append(candidate)
        elif isinstance(item, int):
            normalized.append(f"场景{item}")

    return normalized


def _has_modify_intent(content: str) -> bool:
    keywords = ["修改", "换成", "替换", "增加", "加一个", "确认修改", "我要改", "改成", "确认"]
    return any(keyword in content for keyword in keywords)


def _has_signup_intent(content: str) -> bool:
    keywords = ["报名", "开始报名", "选项目", "我要报名", "第一次报名"]
    return any(keyword in content for keyword in keywords)


def _prioritize_and_trim(scene_ids: list[str], user_message: str, sop_path: str) -> list[str]:
    # 优先级规则：确认报名/报名优先场景1与报名类；避免冲突场景
    avoid = {"场景10", "场景3", "场景4", "场景26"}
    signup_ids = get_scene_ids_by_keywords(sop_path, ["报名", "选项目", "项目"])
    confirm_like = any(k in user_message for k in ["确认报名", "确认", "好的", "开始报名", "我要报名"])

    ordered: list[str] = []
    if confirm_like:
        if "场景1" in scene_ids or "场景1" in signup_ids:
            ordered.append("场景1")
        for sid in scene_ids:
            if sid in avoid:
                continue
            if sid not in ordered:
                ordered.append(sid)
        for sid in signup_ids:
            if sid not in avoid and sid not in ordered:
                ordered.append(sid)
    else:
        for sid in scene_ids:
            if sid not in ordered:
                ordered.append(sid)

    # 移除冲突场景
    filtered = [sid for sid in ordered if sid not in avoid]

    # 最多 3 个
    return filtered[:3]
