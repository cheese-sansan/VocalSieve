"""Runtime library discovery for native Windows inference."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_DLL_HANDLES: list[Any] = []


def configure_windows_cuda() -> list[Path]:
    if os.name != "nt":
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
