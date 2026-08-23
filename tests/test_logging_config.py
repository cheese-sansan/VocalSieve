import logging
from pathlib import Path

from vocalsieve.logging_config import configure_file_logging


def test_configure_file_logging_is_idempotent(tmp_path: Path):
    root = logging.getLogger()
    previous = list(root.handlers)
    for handler in previous:
        root.removeHandler(handler)
    try:
        target = tmp_path / "logs" / "vocalsieve.log"
        assert configure_file_logging(target) == target
        assert configure_file_logging(target) == target
        logging.getLogger("vocalsieve-test").info("hello")
        for handler in root.handlers:
            handler.flush()
        assert "hello" in target.read_text(encoding="utf-8")
        assert len(root.handlers) == 1
    finally:
        for handler in list(root.handlers):
            handler.close()
            root.removeHandler(handler)
        for handler in previous:
            root.addHandler(handler)
