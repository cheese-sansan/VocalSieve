"""Stable domain models shared by the CLI, TUI, and pipeline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

PIPELINE_VERSION = 1
AUDIO_EXTENSIONS = frozenset({".ogg", ".wav", ".flac", ".mp3", ".m4a"})


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class FileStatus(StrEnum):
    PENDING = "pending"
    PHYSICS_PASSED = "physics_passed"
    PHYSICS_REJECTED = "physics_rejected"
    TRANSCRIPTION_PASSED = "transcription_passed"
    TRANSCRIPTION_REJECTED = "transcription_rejected"
    SELECTED = "selected"
    ERROR = "error"


class Stage(StrEnum):
    SCAN = "scan"
    PHYSICS = "physics"
    TRANSCRIPTION = "transcription"
    RANKING = "ranking"
    EXPORT = "export"


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    source_dir: str
    output_dir: str
    model_size: str = "small"
    device: str = "auto"
    compute_type: str = "auto"
    language: str = "auto"
    top_n: int = 1200
    min_duration: float = 0.4
    min_rms: float = 0.015
    min_centroid: float = 1000.0
    no_speech_threshold: float = 0.45
    min_text_length: int = 2
    max_text_length: int = 40
    repeat_char_threshold: int = 4
    ideal_text_length: int = 10
    physics_workers: int = 4

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_dir", self._clean_path(self.source_dir))
        object.__setattr__(self, "output_dir", self._clean_path(self.output_dir))

    @staticmethod
    def _clean_path(value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1].strip()
        return cleaned

    def validate(self, require_source: bool = True) -> None:
        source = Path(self.source_dir).expanduser()
        output = Path(self.output_dir).expanduser()
        if require_source and not source.is_dir():
            raise ValueError(f"Source directory does not exist: {source}")
        if source == output:
            raise ValueError("Source and output directories must be different")
        if self.device not in {"auto", "cpu", "cuda"}:
            raise ValueError("Device must be auto, cpu, or cuda")
        if not self.model_size.strip():
            raise ValueError("Model size cannot be empty")
        if self.top_n < 1:
            raise ValueError("top_n must be at least 1")
        if self.physics_workers < 1 or self.physics_workers > 32:
            raise ValueError("physics_workers must be between 1 and 32")
        if self.min_duration < 0 or self.min_rms < 0 or self.min_centroid < 0:
            raise ValueError("Physics thresholds cannot be negative")
        if not 0 <= self.no_speech_threshold <= 1:
            raise ValueError("no_speech_threshold must be between 0 and 1")
        if not 1 <= self.min_text_length <= self.max_text_length:
            raise ValueError("Text length limits are invalid")
        if self.repeat_char_threshold < 2:
            raise ValueError("repeat_char_threshold must be at least 2")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PipelineConfig:
        return cls(**value)

    @property
    def cache_key(self) -> str:
        payload = {"pipeline_version": PIPELINE_VERSION, "config": self.to_dict()}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AudioMetrics:
    duration: float
    rms: float
    spectral_centroid: float


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    language: str | None
    no_speech_prob: float


@dataclass(frozen=True, slots=True)
class ScannedFile:
    relative_path: str
    absolute_path: Path
    size: int
    mtime_ns: int


@dataclass(frozen=True, slots=True)
class Job:
    id: str
    status: JobStatus
    config: PipelineConfig
    created_at: str
    updated_at: str
    current_stage: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class FileResult:
    relative_path: str
    status: FileStatus
    reject_code: str | None = None
    reject_detail: str | None = None
    duration: float | None = None
    rms: float | None = None
    spectral_centroid: float | None = None
    transcription: str | None = None
    language: str | None = None
    no_speech_prob: float | None = None
    score: float | None = None
    exported_path: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> FileResult:
        return cls(
            relative_path=value["relative_path"],
            status=FileStatus(value["status"]),
            reject_code=value.get("reject_code"),
            reject_detail=value.get("reject_detail"),
            duration=value.get("duration"),
            rms=value.get("rms"),
            spectral_centroid=value.get("spectral_centroid"),
            transcription=value.get("transcription"),
            language=value.get("language"),
            no_speech_prob=value.get("no_speech_prob"),
            score=value.get("score"),
            exported_path=value.get("exported_path"),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value
