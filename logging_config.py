"""Centralized logging: every log record is written both to a rotating
logfile (logs/app.log) and printed to the console (stdout)."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.config import LOG_FILE, LOG_LEVEL

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging() -> None:
    """Configure the root logger once. Safe to call multiple times."""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Keep chatty third-party libraries quieter than our own app logs.
    for noisy_logger in ("faster_whisper", "transformers", "httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging initialized. Writing to %s", LOG_FILE)
