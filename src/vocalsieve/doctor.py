"""Runtime diagnostics, including optional real inference probes."""

from __future__ import annotations

import ctypes
import importlib.util
import os
import sqlite3
import sys
from dataclasses import dataclass

from .domain import PipelineConfig
from .runtime import configure_runtime, find_ffmpeg
from .transcription import FasterWhisperTranscriber


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _ffmpeg_path() -> str | None:
    ffmpeg = find_ffmpeg()
    return str(ffmpeg) if ffmpeg else None


def _windows_cuda_libraries() -> list[Check]:
    if os.name != "nt":
        return []
    configure_runtime()
    checks = []
    for label, filename in (("cuBLAS", "cublas64_12.dll"), ("cuDNN", "cudnn64_9.dll")):
        try:
            ctypes.WinDLL(filename)
            checks.append(Check(label, True, filename, required=False))
        except OSError as exc:
            checks.append(Check(label, False, f"{filename} not loadable: {exc}", required=False))
    return checks


def run_diagnostics(
    *, deep: bool = False, device: str = "auto", model_size: str = "tiny"
) -> list[Check]:
    configure_runtime()
    faster_whisper = importlib.util.find_spec("faster_whisper") is not None
    librosa = importlib.util.find_spec("librosa") is not None
    ffmpeg = _ffmpeg_path()
    checks = [
        Check("Python", (3, 11) <= sys.version_info[:2] < (3, 13), sys.version.split()[0]),
        Check("faster-whisper", faster_whisper, "available" if faster_whisper else "not installed"),
        Check("librosa", librosa, "available" if librosa else "not installed"),
        Check("FFmpeg", ffmpeg is not None, ffmpeg or "not found"),
        Check("SQLite", True, sqlite3.sqlite_version),
    ]
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
        checks.append(Check("CUDA capability", False, f"unavailable: {exc}", required=False))
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
                Check("Inference probe", True, f"{model_size} on {transcriber.effective_device}")
            )
        except Exception as exc:
            checks.append(Check("Inference probe", False, str(exc)))
    return checks
