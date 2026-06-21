"""Runtime diagnostics, including optional real inference probes."""

from __future__ import annotations

import ctypes
import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .database import default_database_path
from .domain import PipelineConfig
from .runtime import configure_runtime, find_ffmpeg
from .transcription import FasterWhisperTranscriber


def _is_windows() -> bool:
    return os.name == "nt"


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _ffmpeg_path() -> str | None:
    ffmpeg = find_ffmpeg()
    return str(ffmpeg) if ffmpeg else None


def _model_cache_path() -> Path:
    try:
        from huggingface_hub.constants import HF_HUB_CACHE
    except ImportError:
        hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
        return hf_home.expanduser() / "hub"

    return Path(HF_HUB_CACHE).expanduser()


def _writable_path_check(name: str, target: Path) -> Check:
    target = target.expanduser().resolve()
    if target.exists() and not target.is_dir():
        return Check(name, False, f"not a directory: {target}")
    probe_root = target if target.is_dir() else target.parent
    while not probe_root.exists() and probe_root != probe_root.parent:
        probe_root = probe_root.parent
    try:
        with tempfile.NamedTemporaryFile(prefix="vocalsieve-doctor-", dir=probe_root):
            pass
    except OSError as exc:
        return Check(name, False, f"not writable: {target} ({exc})")
    detail = str(target) if target.exists() else f"writable parent; will create {target}"
    return Check(name, True, detail)


def _ffmpeg_check(ffmpeg: str | None) -> Check:
    if ffmpeg is None:
        return Check("FFmpeg", False, "not found; see docs/FFMPEG.md")
    try:
        completed = subprocess.run(
            [ffmpeg, "-version"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check("FFmpeg", False, f"not executable: {exc}")
    if completed.returncode != 0:
        return Check("FFmpeg", False, f"exited with code {completed.returncode}")
    version = completed.stdout.splitlines()[0] if completed.stdout else "available"
    return Check("FFmpeg", True, f"{ffmpeg} ({version})")


def _windows_cuda_libraries() -> list[Check]:
    if not _is_windows():
        return []
    configure_runtime()
    checks = []
    win_dll = ctypes.WinDLL  # pyright: ignore[reportAttributeAccessIssue]
    for label, filename in (("cuBLAS", "cublas64_12.dll"), ("cuDNN", "cudnn64_9.dll")):
        try:
            win_dll(filename)
            checks.append(Check(label, True, filename, required=False))
        except OSError as exc:
            checks.append(Check(label, False, f"{filename} not loadable: {exc}", required=False))
    return checks


def run_diagnostics(
    *,
    deep: bool = False,
    device: str = "auto",
    model_size: str = "tiny",
    output_path: str | Path | None = None,
) -> list[Check]:
    configure_runtime()
    faster_whisper = importlib.util.find_spec("faster_whisper") is not None
    librosa = importlib.util.find_spec("librosa") is not None
    ffmpeg = _ffmpeg_path()
    checks = [
        Check("Python", (3, 11) <= sys.version_info[:2] < (3, 13), sys.version.split()[0]),
        Check("faster-whisper", faster_whisper, "available" if faster_whisper else "not installed"),
        Check("librosa", librosa, "available" if librosa else "not installed"),
        _ffmpeg_check(ffmpeg),
        Check("SQLite", True, sqlite3.sqlite_version),
        _writable_path_check("Model cache", _model_cache_path()),
        _writable_path_check("Database directory", default_database_path().parent),
    ]
    if output_path is not None:
        checks.append(_writable_path_check("Output directory", Path(output_path)))
    try:
        import ctranslate2

        compute_types = ctranslate2.get_supported_compute_types("cuda")
        checks.append(
            Check(
                "CUDA capability",
                bool(compute_types),
                ", ".join(sorted(compute_types)),
                required=False,
            )
        )
    except Exception as exc:
        checks.append(
            Check(
                "CUDA capability",
                False,
                f"unavailable: {exc}; see docs/CUDA.md",
                required=False,
            )
        )
    checks.extend(_windows_cuda_libraries())

    if deep and faster_whisper:
        config = PipelineConfig(
            source_dir=".",
            output_dir="./.vocalsieve-doctor-output",
            model_size=model_size,
            device=device,
            compute_type="auto",
        )
        transcriber = FasterWhisperTranscriber(config)
        try:
            transcriber.prepare()
            checks.append(
                Check(
                    "Inference probe",
                    True,
                    f"{model_size} on {transcriber.effective_device} "
                    f"({getattr(transcriber, 'effective_compute_type', 'unknown')})",
                )
            )
        except Exception as exc:
            checks.append(Check("Inference probe", False, str(exc)))
    return checks
