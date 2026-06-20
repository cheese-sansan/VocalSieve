"""Safe final-result export with human-readable reports."""

from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

REPORT_FIELDS = (
    "relative_path",
    "status",
    "language",
    "transcription",
    "duration",
    "rms",
    "spectral_centroid",
    "no_speech_prob",
    "score",
    "reject_code",
    "reject_detail",
)


def safe_destination(root: Path, relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe relative path: {relative_path}")
    destination = root.joinpath(*relative.parts).resolve()
    root = root.resolve()
    if root != destination and root not in destination.parents:
        raise ValueError(f"Export escaped its root: {relative_path}")
    return destination


def export_selected(
    source_root: Path,
    output_root: Path,
    selected: Iterable[dict],
    all_results: Iterable[dict],
) -> dict[str, str]:
    final_root = output_root / "final_selected"
    final_root.mkdir(parents=True, exist_ok=True)
    exported: dict[str, str] = {}
    for row in selected:
        source = safe_destination(source_root, row["relative_path"])
        destination = safe_destination(final_root, row["relative_path"])
        if not source.is_file():
            raise FileNotFoundError(f"Source file disappeared: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        exported[row["relative_path"]] = str(destination)

    rows = list(all_results)
    csv_path = output_root / "vocalsieve-report.csv"
    json_path = output_root / "vocalsieve-report.json"
    output_root.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(
            [{key: row.get(key) for key in REPORT_FIELDS} for row in rows],
            handle,
            ensure_ascii=False,
            indent=2,
        )
    return exported
