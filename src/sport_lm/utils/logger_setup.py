import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from ..security.privacy import redact_text


class RedactingFilter(logging.Filter):
    """Last-resort protection for accidental sensitive values in log calls."""

    def filter(self, record: logging.LogRecord) -> bool:
        rendered = record.getMessage()
        record.msg = redact_text(rendered)
        record.args = ()
        return True


def setup_logging() -> None:
    logger = logging.getLogger()
    if logger.handlers:
        return

    logger.setLevel(logging.INFO)
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    redacting_filter = RedactingFilter()

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(redacting_filter)

    file_handler = TimedRotatingFileHandler(
        log_dir / "app.log", when="midnight", backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redacting_filter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.WARNING)
    security_logger.propagate = False
    security_handler = TimedRotatingFileHandler(
        log_dir / "security.log", when="midnight", backupCount=7, encoding="utf-8"
    )
    security_handler.setFormatter(formatter)
    security_handler.addFilter(redacting_filter)
    security_logger.addHandler(security_handler)
