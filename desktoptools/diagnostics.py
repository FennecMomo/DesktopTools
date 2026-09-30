"""Bounded local diagnostics; never log note, todo or clipboard content."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(directory: Path) -> None:
    logger = logging.getLogger("desktoptools")
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            directory / "desktoptools.log", maxBytes=1024 * 1024,
            backupCount=2, encoding="utf-8",
        )
    except OSError:
        # Logging failure must never prevent startup or recovery.
        handler = logging.NullHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)


def report_callback_exception(kind, error, traceback) -> None:
    logging.getLogger("desktoptools").error(
        "UI callback failed", exc_info=(kind, error, traceback),
    )
