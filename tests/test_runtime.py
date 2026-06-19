from pathlib import Path

from vocalsieve import runtime


def test_configure_windows_cuda_discovers_side_by_side_runtime(tmp_path: Path, monkeypatch):
    program_files = tmp_path / "Program Files"
    cuda_bin = program_files / "NVIDIA GPU Computing Toolkit" / "CUDA" / "v12.8" / "bin"
    cudnn_bin = program_files / "NVIDIA" / "CUDNN" / "v9" / "bin" / "12.8"
    cuda_bin.mkdir(parents=True)
    cudnn_bin.mkdir(parents=True)
    (cudnn_bin / "cudnn64_9.dll").write_bytes(b"")
    registered = []
    monkeypatch.setattr(runtime.os, "name", "nt")
    monkeypatch.setenv("PROGRAMFILES", str(program_files))
    monkeypatch.setattr(runtime.os, "add_dll_directory", registered.append, raising=False)

    configured = runtime.configure_windows_cuda()

    assert cuda_bin.resolve() in configured
    assert cudnn_bin.resolve() in configured
    assert str(cuda_bin.resolve()) in registered


def test_ffmpeg_prefers_portable_path(tmp_path: Path, monkeypatch):
    executable = tmp_path / "VocalSieve.exe"
    bundled = tmp_path / "tools" / "ffmpeg" / "ffmpeg.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"ffmpeg")
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime.sys, "executable", str(executable))
    monkeypatch.setenv("PATH", "")

    assert runtime.find_ffmpeg() == bundled
    assert str(bundled.parent) in runtime.os.environ["PATH"]


def test_source_runtime_uses_path_ffmpeg(tmp_path: Path, monkeypatch):
    binary = tmp_path / "ffmpeg.exe"
    binary.write_bytes(b"ffmpeg")
    monkeypatch.setattr(runtime.sys, "frozen", False, raising=False)
    monkeypatch.setattr(runtime, "user_ffmpeg_path", lambda: None)
    monkeypatch.setattr(runtime.shutil, "which", lambda _: str(binary))

    assert runtime.find_ffmpeg() == binary.resolve()
