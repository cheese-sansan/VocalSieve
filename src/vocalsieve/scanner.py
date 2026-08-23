"""Recursive, read-only source discovery."""

from __future__ import annotations

from pathlib import Path

from .domain import AUDIO_EXTENSIONS, ScannedFile


def scan_audio_files(source_dir: str, output_dir: str) -> list[ScannedFile]:
    source = Path(source_dir).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    output_is_inside_source = source in output.parents
    discovered: list[ScannedFile] = []
    for path in source.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        resolved = path.resolve()
        if output_is_inside_source and (resolved == output or output in resolved.parents):
            continue
        stat = resolved.stat()
        discovered.append(
            ScannedFile(
                relative_path=resolved.relative_to(source).as_posix(),
                absolute_path=resolved,
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
            )
        )
    return sorted(discovered, key=lambda item: item.relative_path.casefold())
