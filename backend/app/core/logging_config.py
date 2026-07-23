"""Application-wide logging configuration. No print() statements anywhere."""
import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. reload) - avoid duplicate handlers.
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL.upper())

    # Quiet down noisy third-party loggers.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
