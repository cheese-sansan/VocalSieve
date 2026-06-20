"""Runtime library discovery for native Windows inference."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

from platformdirs import user_data_path

_DLL_HANDLES: list[Any] = []


def _is_windows() -> bool:
    return os.name == "nt"


def portable_root() -> Path | None:
    """Return the portable application root when running a frozen executable."""
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable).resolve().parent


def bundled_ffmpeg_path() -> Path | None:
    root = portable_root()
    if root is None:
        return None
    candidate = root / "tools" / "ffmpeg" / "ffmpeg.exe"
    return candidate if candidate.is_file() else None


def user_ffmpeg_path() -> Path | None:
    candidate = user_data_path("VocalSieve", appauthor=False) / "tools/ffmpeg/bin/ffmpeg.exe"
    return candidate if candidate.is_file() else None


def configure_ffmpeg() -> Path | None:
    candidate = bundled_ffmpeg_path() or user_ffmpeg_path()
    if candidate is not None:
        directory = str(candidate.parent)
        path_parts = os.environ.get("PATH", "").split(os.pathsep)
        if directory not in path_parts:
            os.environ["PATH"] = f"{directory}{os.pathsep}{os.environ.get('PATH', '')}"
        return candidate
    discovered = shutil.which("ffmpeg")
    return Path(discovered).resolve() if discovered else None


def find_ffmpeg() -> Path | None:
    return configure_ffmpeg()


def configure_runtime() -> None:
    configure_ffmpeg()
    configure_windows_cuda()


def configure_windows_cuda() -> list[Path]:
    if not _is_windows():
        return []

    candidates: list[Path] = []
    cuda_root = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / (
        "NVIDIA GPU Computing Toolkit/CUDA"
    )
    if cuda_root.is_dir():
        candidates.extend(sorted(cuda_root.glob("v12*/bin"), reverse=True))

    cudnn_root = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "NVIDIA/CUDNN"
    if cudnn_root.is_dir():
        candidates.extend(path.parent for path in cudnn_root.rglob("cudnn64_9.dll"))

    for name in ("CUDA_PATH_V12_8", "CUDA_PATH"):
        value = os.environ.get(name)
        if value:
            candidates.append(Path(value) / "bin")

    configured: list[Path] = []
    add_dll_directory = getattr(os, "add_dll_directory", None)
    for candidate in candidates:
        resolved = candidate.resolve()
        if not resolved.is_dir() or resolved in configured:
            continue
        configured.append(resolved)
        os.environ["PATH"] = f"{resolved}{os.pathsep}{os.environ.get('PATH', '')}"
        if add_dll_directory is not None:
            _DLL_HANDLES.append(add_dll_directory(str(resolved)))
    return configured
