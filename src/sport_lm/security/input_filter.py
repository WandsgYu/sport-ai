from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class FilterResult:
    allowed: bool
    reason: str = ""


_KEYWORDS: Iterable[str] = [
    "忽略",
    "忘记",
    "无视",
    "绕过",
    "越狱",
    "jailbreak",
    "提示词",
    "prompt",
    "system",
    "指令",
    "现在开始",
    "新的指令",
    "你现在是",
    "从现在起",
    "接下来",
    "假设你是",
    "扮演",
    "角色扮演",
    "roleplay",
    "重置",
    "重启",
    "清除",
    "覆写",
    "override",
    "注入",
    "injection",
    "测试",
    "测试模式",
    "开发者模式",
    "debug",
    "admin",
    "后台",
    "内部指令",
    "特殊指令",
    "真实指令",
    "隐藏指令",
    "真正",
    "实际",
    "秘密",
    "不要告诉",
    "保密",
    "私下",
    "只回答",
    "直接回答",
    "不考虑",
    "不管",
    "无论",
    "任何",
    "一切",
    "开始新",
    "切换",
    "现在你是",
    "我是你的",
    "听我的",
    "服从",
    "执行",
    "遵循",
    "新的规则",
    "新规则",
    "规则变更",
]

_REGEX_PATTERNS: Iterable[re.Pattern] = [
    re.compile(r"(?i)ignore\s+previous"),
    re.compile(r"(?i)system\s+prompt"),
    re.compile(r"(?i)developer\s+mode"),
    re.compile(r"(?i)jailbreak"),
    re.compile(r"(?i)show\s+your\s+prompt"),
    re.compile(r"(?i)repeat\s+instructions"),
    re.compile(r"忽略.*指令"),
    re.compile(r"忘记.*规则"),
    re.compile(r"现在开始.*指令"),
]

_BASE64_RE = re.compile(r"[A-Za-z0-9+/=]{200,}")
_SYMBOL_RE = re.compile(r"[^A-Za-z0-9\u4e00-\u9fff\s]{40,}")
_DISALLOWED_CHAR_RE = re.compile(r"[^\u4e00-\u9fff0-9\s\.,!?;:，。！？；：、“”‘’（）()【】\[\]《》<>…—\-+/=_]")


def check_message(content: str) -> FilterResult:
    if not content:
        return FilterResult(True)

    if len(content) > 800:
        return FilterResult(False, "message_too_long")

    lowered = content.lower()
    for kw in _KEYWORDS:
        if kw.lower() in lowered:
            return FilterResult(False, "keyword_match")

    for pattern in _REGEX_PATTERNS:
        if pattern.search(content):
            return FilterResult(False, "pattern_match")

    if content.count("\n") >= 20:
        return FilterResult(False, "too_many_newlines")

    if _BASE64_RE.search(content):
        return FilterResult(False, "base64_suspected")

    if _SYMBOL_RE.search(content):
        return FilterResult(False, "symbols_flood")

    # Extra rule: allow only Chinese chars, digits, and punctuation.
    # If other characters appear 6+ times, block.
    if len(_DISALLOWED_CHAR_RE.findall(content)) >= 6:
        return FilterResult(False, "non_cn_chars_over_limit")

    return FilterResult(True)
