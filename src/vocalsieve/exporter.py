"""Safe final-result export with human-readable reports."""

from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from .domain import PipelineConfig
from .rules import rejection_info

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
    "review_decision",
    "review_note",
    "reviewed_at",
    "effective_selected",
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
    *,
    job_id: str | None = None,
    config: PipelineConfig | None = None,
    events: Iterable[dict] = (),
) -> dict[str, str]:
    final_root = output_root / "final_selected"
    final_root.mkdir(parents=True, exist_ok=True)
    selected_rows = list(selected)
    selected_paths = {row["relative_path"] for row in selected_rows}
    rows = list(all_results)
    for row in rows:
        previous = row.get("exported_path")
        if not previous or row["relative_path"] in selected_paths:
            continue
        destination = safe_destination(final_root, row["relative_path"])
        if destination.is_file():
            destination.unlink()
    exported: dict[str, str] = {}
    for row in selected_rows:
        source = safe_destination(source_root, row["relative_path"])
        destination = safe_destination(final_root, row["relative_path"])
        if not source.is_file():
            raise FileNotFoundError(f"Source file disappeared: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        exported[row["relative_path"]] = str(destination)

    csv_path = output_root / "vocalsieve-report.csv"
    json_path = output_root / "vocalsieve-report.json"
    summary_path = output_root / "vocalsieve-summary.json"
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
    if job_id is not None and config is not None:
        summary = build_report_summary(job_id, config, rows, events)
        with summary_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)
    return exported


def build_report_summary(
    job_id: str,
    config: PipelineConfig,
    all_results: Iterable[dict],
    events: Iterable[dict] = (),
) -> dict:
    rows = list(all_results)
    candidate_statuses = {"selected", "transcription_passed"}
    rejected_statuses = {"physics_rejected", "transcription_rejected"}
    candidates = sum(row.get("status") in candidate_statuses for row in rows)
    automatic_selected = sum(row.get("status") == "selected" for row in rows)
    selected = sum(row.get("effective_selected", row.get("status") == "selected") for row in rows)
    manual_includes = sum(row.get("review_decision") == "include" for row in rows)
    manual_excludes = sum(row.get("review_decision") == "exclude" for row in rows)
    rejected = sum(row.get("status") in rejected_statuses for row in rows)
    errors = sum(row.get("status") == "error" for row in rows)
    durations = [float(row["duration"]) for row in rows if row.get("duration") is not None]

    counts: dict[str, int] = {}
    for row in rows:
        code = row.get("reject_code")
        if code:
            counts[code] = counts.get(code, 0) + 1
    rejection_counts = {}
    for code in sorted(counts):
        info = rejection_info(code)
        rejection_counts[code] = {
            "count": counts[code],
            "title": info.title,
            "description": info.description,
            "config_field": info.config_field,
        }

    requested_device = config.device
    effective_device = requested_device if requested_device != "auto" else "unknown"
    effective_compute_type = config.compute_type if requested_device != "auto" else "unknown"
    fallback = False
    fallback_reason = None
    for event in events:
        data = event.get("data", {})
        if data.get("backend_selected"):
            effective_device = data.get("effective_device", effective_device)
            effective_compute_type = data.get("effective_compute_type", effective_compute_type)
        if data.get("backend_fallback"):
            fallback = True
            effective_device = data.get("effective_device", effective_device)
            effective_compute_type = data.get("effective_compute_type", effective_compute_type)
            fallback_reason = data.get("reason_code")

    thresholds = {
        "min_duration": config.min_duration,
        "min_rms": config.min_rms,
        "min_centroid": config.min_centroid,
        "no_speech_threshold": config.no_speech_threshold,
        "min_text_length": config.min_text_length,
        "max_text_length": config.max_text_length,
        "repeat_char_threshold": config.repeat_char_threshold,
        "top_n": config.top_n,
    }
    total = len(rows)
    return {
        "schema_version": 2,
        "job_id": job_id,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "total_scanned": total,
        "candidate_count": candidates,
        "selected_count": selected,
        "automatic_selected_count": automatic_selected,
        "manual_include_count": manual_includes,
        "manual_exclude_count": manual_excludes,
        "rejected_count": rejected,
        "error_count": errors,
        "candidate_pass_rate": candidates / total if total else 0.0,
        "average_duration": sum(durations) / len(durations) if durations else None,
        "rejection_counts": rejection_counts,
        "thresholds": thresholds,
        "backend": {
            "requested_device": requested_device,
            "effective_device": effective_device,
            "effective_compute_type": effective_compute_type,
            "fallback": fallback,
            "fallback_reason": fallback_reason,
        },
    }
