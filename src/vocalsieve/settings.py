"""Small persistent preferences for the local workbench."""

from __future__ import annotations

import json
from pathlib import Path

from platformdirs import user_config_path

SUPPORTED_LANGUAGES = frozenset({"en", "zh"})


def default_settings_path() -> Path:
    return user_config_path("VocalSieve", appauthor=False) / "settings.json"


def load_language(path: str | Path | None = None) -> str | None:
    settings_path = Path(path) if path else default_settings_path()
    try:
        payload = json.loads(settings_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    language = payload.get("interface_language")
    return language if language in SUPPORTED_LANGUAGES else None


def save_language(language: str, path: str | Path | None = None) -> None:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported interface language: {language}")
    settings_path = Path(path) if path else default_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = settings_path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"interface_language": language}, indent=2), encoding="utf-8")
    temporary.replace(settings_path)
