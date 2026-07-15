from __future__ import annotations

import logging
import threading
from typing import Optional

import uvicorn

from ..config import Config
from .app import app

logger = logging.getLogger(__name__)


def start_log_viewer(config: Config) -> Optional[threading.Thread]:
    if not config.log_viewer_enabled:
        logger.info("日志查看器未启用")
        return None

    def _run() -> None:
        try:
            uvicorn.run(
                app,
                host=config.log_viewer_host,
                port=config.log_viewer_port,
                log_level="warning",
            )
        except Exception as exc:
            logger.exception("日志查看器启动失败: %s", exc)

    thread = threading.Thread(target=_run, name="log_viewer", daemon=True)
    thread.start()
    logger.info(
        "脱敏事件查看器已在本机启动，port=%s",
        config.log_viewer_port,
    )
    return thread
