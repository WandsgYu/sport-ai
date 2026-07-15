from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


USER_FIELDS = [
    "channel_user_id",
    "subject_id",
    "display_name",
    "group",
    "category",
]


def _default_user_info(channel_user_id: str) -> dict[str, Any]:
    return {field: "" for field in USER_FIELDS} | {
        "channel_user_id": channel_user_id
    }


class UserMap:
    """Minimal identity directory; no real mapping file is distributed."""

    def __init__(self, data: dict[str, dict[str, Any]]) -> None:
        self._data = data

    def get_user_info(self, channel_user_id: str) -> dict[str, Any]:
        return self._data.get(
            channel_user_id, _default_user_info(channel_user_id)
        )


def load_user_map(csv_path: str) -> UserMap:
    if not csv_path:
        return UserMap({})
    path = Path(csv_path)
    if not path.exists():
        return UserMap({})

    data: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            channel_user_id = (row.get("channel_user_id") or "").strip()
            if not channel_user_id:
                continue
            data[channel_user_id] = {
                field: (row.get(field) or "").strip() for field in USER_FIELDS
            }
    return UserMap(data)
