from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Non-secret settings retained for code-reading and local tests only."""

    sop_file_path: str
    user_csv_path: str
    log_viewer_host: str
    log_viewer_port: int
    log_viewer_enabled: bool

    @classmethod
    def load(cls) -> "Config":
        base_dir = Path(__file__).resolve().parent
        return cls(
            sop_file_path=os.getenv(
                "SOP_FILE_PATH", str(base_dir / "问答示例.md")
            ),
            user_csv_path=os.getenv("USER_CSV_PATH", ""),
            log_viewer_host="localhost",
            log_viewer_port=int(os.getenv("LOG_VIEWER_PORT", "8080")),
            log_viewer_enabled=False,
        )


_CONFIG: Config | None = None


def get_config() -> Config:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = Config.load()
    return _CONFIG
