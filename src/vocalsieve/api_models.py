"""Versioned HTTP API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .domain import FileResult, Job, PipelineConfig


class ConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_dir: str
    output_dir: str
    model_size: str = "small"
    device: str = "auto"
    compute_type: str = "auto"
    language: str = "auto"
    top_n: int = Field(default=1200, ge=1)
    min_duration: float = Field(default=0.4, ge=0)
    min_rms: float = Field(default=0.015, ge=0)
    min_centroid: float = Field(default=1000.0, ge=0)
    no_speech_threshold: float = Field(default=0.45, ge=0, le=1)
    min_text_length: int = Field(default=2, ge=1)
    max_text_length: int = Field(default=40, ge=1)
    repeat_char_threshold: int = Field(default=4, ge=2)
    ideal_text_length: int = Field(default=10, ge=1)
    physics_workers: int = Field(default=4, ge=1, le=32)

    def to_domain(self) -> PipelineConfig:
        return PipelineConfig(**self.model_dump())


class JobResponse(BaseModel):
    id: str
    status: str
    config: dict[str, Any]
    created_at: str
    updated_at: str
    current_stage: str | None
    error: str | None

    @classmethod
    def from_domain(cls, job: Job) -> JobResponse:
        return cls(
            id=job.id,
            status=job.status.value,
            config=job.config.to_dict(),
            created_at=job.created_at,
            updated_at=job.updated_at,
            current_stage=job.current_stage,
            error=job.error,
        )


class FileResultResponse(BaseModel):
    relative_path: str
    status: str
    reject_code: str | None
    reject_detail: str | None
    duration: float | None
    rms: float | None
    spectral_centroid: float | None
    transcription: str | None
    language: str | None
    no_speech_prob: float | None
    score: float | None
    exported_path: str | None

    @classmethod
    def from_domain(cls, result: FileResult) -> FileResultResponse:
        return cls(**result.to_dict())


class CheckResponse(BaseModel):
    name: str
    ok: bool
    detail: str
    required: bool


class ExportResponse(BaseModel):
    count: int
    files: dict[str, str]


class EventResponse(BaseModel):
    id: int
    job_id: str
    type: str
    stage: str | None
    message: str
    data: dict[str, Any]
    timestamp: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    api_version: str = "v1"


class ModelResponse(BaseModel):
    id: str
    label: str
    approximate_vram_mb: int | None
