"""Local rotating log configuration shared by executable entry points."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_path


def default_log_path() -> Path:
    return user_log_path("VocalSieve", appauthor=False) / "vocalsieve.log"


def configure_file_logging(path: str | Path | None = None) -> Path | None:
    target = Path(path) if path else default_log_path()
    root = logging.getLogger()
    if any(getattr(handler, "_vocalsieve_file_handler", False) for handler in root.handlers):
        return target
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            target,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
    except OSError:
        return None
    handler._vocalsieve_file_handler = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return target
