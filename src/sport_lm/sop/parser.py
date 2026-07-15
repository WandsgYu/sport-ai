from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

SCENE_HEADER_RE = re.compile(r"^##\s*(场景\d+)(：.*)?$")


def parse_sop_scenes(sop_path: str) -> list[dict[str, str]]:
    path = Path(sop_path)
    if not path.exists():
        return []

    scenes: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    body_lines: list[str] = []

    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            header = SCENE_HEADER_RE.match(line.strip())
            if header:
                if current is not None:
                    current["body"] = "\n".join(body_lines).strip()
                    scenes.append(current)
                scene_id = header.group(1)
                title_suffix = (header.group(2) or "").lstrip("：").strip()
                title = f"{scene_id}：{title_suffix}" if title_suffix else scene_id
                current = {"id": scene_id, "title": title, "body": ""}
                body_lines = []
                continue

            if current is not None:
                body_lines.append(line)

    if current is not None:
        current["body"] = "\n".join(body_lines).strip()
        scenes.append(current)

    return scenes


def build_scene_menu(scenes: Iterable[dict[str, str]]) -> str:
    items = [scene["title"] for scene in scenes if scene.get("title")]
    return "；".join(items) if items else "暂无场景"


def load_scene_menu(sop_path: str) -> str:
    return build_scene_menu(parse_sop_scenes(sop_path))


def build_sop_context(scene_ids: list[str], sop_path: str) -> str:
    scenes = parse_sop_scenes(sop_path)
    scene_map = {scene["id"]: scene for scene in scenes}
    chunks: list[str] = []
    for scene_id in scene_ids:
        scene = scene_map.get(scene_id)
        if not scene:
            continue
        body = scene.get("body", "").strip()
        if body:
            chunks.append(f"{scene['title']}\n{body}")

    if not chunks:
        return ""

    return "已获取以下场景剧本：\n\n" + "\n\n".join(chunks)


def get_modify_scene_ids(sop_path: str) -> list[str]:
    scenes = parse_sop_scenes(sop_path)
    return [scene["id"] for scene in scenes if "修改" in scene.get("title", "")]


def get_scene_ids_by_keywords(sop_path: str, keywords: list[str]) -> list[str]:
    scenes = parse_sop_scenes(sop_path)
    ids: list[str] = []
    for scene in scenes:
        title = scene.get("title", "")
        if any(keyword in title for keyword in keywords):
            ids.append(scene["id"])
    return ids
