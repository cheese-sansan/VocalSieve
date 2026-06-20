"""Speech-to-text port and faster-whisper adapter."""

from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from typing import Protocol

from .domain import PipelineConfig, Transcript
from .errors import BackendUnavailableError
from .runtime import configure_windows_cuda


class Transcriber(Protocol):
    def prepare(self) -> None: ...

    def transcribe(self, path: Path) -> Transcript: ...


class FasterWhisperTranscriber:
    def __init__(self, config: PipelineConfig):
        self._config = config
        self._model = None
        self._device = config.device

    def _load_model(self):
        if self._model is None:
            configure_windows_cuda()
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self._config.model_size,
                device=self._device,
                compute_type=self._config.compute_type,
            )
        return self._model

    @property
    def effective_device(self) -> str:
        return self._device

    def prepare(self) -> None:
        """Load the model and run a short probe before processing user files."""
        probe_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                probe_path = Path(handle.name)
            with wave.open(str(probe_path), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(16_000)
                audio.writeframes(b"\x00\x00" * 4_000)
            self.transcribe(probe_path)
        except Exception as exc:
            raise BackendUnavailableError(
                f"{self._config.device} inference backend failed: {exc}"
            ) from exc
        finally:
            if probe_path is not None:
                probe_path.unlink(missing_ok=True)

    def transcribe(self, path: Path) -> Transcript:
        kwargs = {}
        if self._config.language != "auto":
            kwargs["language"] = self._config.language
        try:
            segments, info = self._load_model().transcribe(str(path), **kwargs)
            segment_list = list(segments)
        except Exception as exc:
            if self._config.device != "auto" or not self._is_cuda_runtime_error(exc):
                raise
            from faster_whisper import WhisperModel

            self._device = "cpu"
            self._model = WhisperModel(self._config.model_size, device="cpu", compute_type="int8")
            segments, info = self._model.transcribe(str(path), **kwargs)
            segment_list = list(segments)
        text = " ".join(segment.text.strip() for segment in segment_list).strip()
        weighted = [
            (
                max(0.0, float(segment.end) - float(segment.start)),
                float(getattr(segment, "no_speech_prob", 0.0)),
            )
            for segment in segment_list
        ]
        total_duration = sum(duration for duration, _ in weighted)
        no_speech = (
            sum(duration * probability for duration, probability in weighted) / total_duration
            if total_duration
            else 1.0
        )
        return Transcript(
            text=text,
            language=getattr(info, "language", None),
            no_speech_prob=no_speech,
        )

    @staticmethod
    def _is_cuda_runtime_error(error: Exception) -> bool:
        message = str(error).casefold()
        return any(token in message for token in ("cublas", "cudnn", "cuda", ".dll"))
