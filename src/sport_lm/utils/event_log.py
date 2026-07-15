from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..security.privacy import sanitize


_LOCK = threading.Lock()


def log_event(event: dict[str, Any]) -> None:
    """Write sanitized event metadata; raw conversations are never persisted."""

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_path = log_dir / "events.jsonl"

    payload = sanitize(dict(event))
    payload.setdefault("ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    line = json.dumps(payload, ensure_ascii=False, default=str)

    with _LOCK:
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
