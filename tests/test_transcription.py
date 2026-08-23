import sys
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest

from vocalsieve.domain import PipelineConfig
from vocalsieve.errors import BackendUnavailableError
from vocalsieve.transcription import FasterWhisperTranscriber


class Segment:
    def __init__(self, text=" hello ", start=0.0, end=1.0, probability=0.2):
        self.text = text
        self.start = start
        self.end = end
        self.no_speech_prob = probability


class FakeModel:
    failures: ClassVar[list[Exception]] = []
    instances: ClassVar[list[tuple[str, str]]] = []

    def __init__(self, model, device, compute_type):
        self.instances.append((device, compute_type))
        self.device = "cpu" if device == "auto" else device
        self.compute_type = "int8" if compute_type == "auto" else compute_type

    def transcribe(self, path, **kwargs):
        if self.failures:
            raise self.failures.pop(0)
        return iter([Segment(), Segment(" world ", 1, 3, 0.4)]), SimpleNamespace(language="en")


@pytest.fixture(autouse=True)
def fake_whisper(monkeypatch):
    FakeModel.failures = []
    FakeModel.instances = []
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeModel))


def config(tmp_path: Path, device="cpu"):
    return PipelineConfig(str(tmp_path), str(tmp_path / "out"), device=device, compute_type="int8")


def test_transcriber_loads_once_and_weights_probability(tmp_path: Path):
    transcriber = FasterWhisperTranscriber(config(tmp_path))
    result = transcriber.transcribe(tmp_path / "a.wav")
    assert result.text == "hello world"
    assert result.language == "en"
    assert result.no_speech_prob == pytest.approx((0.2 + 0.8) / 3)
    assert transcriber.effective_device == "cpu"
    assert len(FakeModel.instances) == 1


def test_auto_cuda_failure_falls_back_to_cpu(tmp_path: Path):
    FakeModel.failures = [RuntimeError("cublas64_12.dll missing")]
    transcriber = FasterWhisperTranscriber(config(tmp_path, "auto"))
    result = transcriber.transcribe(tmp_path / "a.wav")
    assert result.text
    assert transcriber.effective_device == "cpu"
    assert FakeModel.instances == [("auto", "int8"), ("cpu", "int8")]
    assert transcriber.effective_compute_type == "int8"
    assert transcriber.fallback_reason == "cuda_library_unavailable"
    assert transcriber.fallback_occurred


def test_auto_cpu_selection_is_not_fallback(tmp_path: Path):
    transcriber = FasterWhisperTranscriber(config(tmp_path, "auto"))
    transcriber.transcribe(tmp_path / "a.wav")
    assert transcriber.effective_device == "cpu"
    assert not transcriber.fallback_occurred


def test_explicit_cuda_failure_is_not_hidden(tmp_path: Path):
    FakeModel.failures = [RuntimeError("CUDA failed")]
    transcriber = FasterWhisperTranscriber(config(tmp_path, "cuda"))
    with pytest.raises(RuntimeError, match="CUDA failed"):
        transcriber.transcribe(tmp_path / "a.wav")


def test_prepare_wraps_backend_failure(tmp_path: Path):
    FakeModel.failures = [RuntimeError("decoder failed")]
    transcriber = FasterWhisperTranscriber(config(tmp_path))
    with pytest.raises(BackendUnavailableError, match="backend failed"):
        transcriber.prepare()
