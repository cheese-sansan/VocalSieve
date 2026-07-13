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


class ConfigResponse(BaseModel):
    source_dir: str
    output_dir: str
    model_size: str
    device: str
    compute_type: str
    language: str
    top_n: int
    min_duration: float
    min_rms: float
    min_centroid: float
    no_speech_threshold: float
    min_text_length: int
    max_text_length: int
    repeat_char_threshold: int
    ideal_text_length: int
    physics_workers: int

    @classmethod
    def from_domain(cls, config: PipelineConfig) -> ConfigResponse:
        return cls(**config.to_dict())


class JobResponse(BaseModel):
    id: str
    status: str
    config: ConfigResponse
    created_at: str
    updated_at: str
    current_stage: str | None
    error: str | None

    @classmethod
    def from_domain(cls, job: Job) -> JobResponse:
        return cls(
            id=job.id,
            status=job.status.value,
            config=ConfigResponse.from_domain(job.config),
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
    review_decision: str | None
    review_note: str | None
    reviewed_at: str | None
    effective_selected: bool

    @classmethod
    def from_domain(cls, result: FileResult) -> FileResultResponse:
        return cls(**result.to_dict())


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str = Field(min_length=1)
    decision: str = Field(pattern="^(automatic|include|exclude)$")
    note: str | None = Field(default=None, max_length=500)


class CheckResponse(BaseModel):
    name: str
    ok: bool
    detail: str
    required: bool
    code: str
    severity: str
    action: str


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


class RejectionSummary(BaseModel):
    count: int
    title: str
    description: str
    config_field: str | None


class ThresholdSummary(BaseModel):
    min_duration: float
    min_rms: float
    min_centroid: float
    no_speech_threshold: float
    min_text_length: int
    max_text_length: int
    repeat_char_threshold: int
    top_n: int


class BackendSummary(BaseModel):
    requested_device: str
    effective_device: str
    effective_compute_type: str
    fallback: bool
    fallback_reason: str | None


class ReportResponse(BaseModel):
    schema_version: int
    job_id: str
    generated_at: str
    total_scanned: int
    candidate_count: int
    selected_count: int
    automatic_selected_count: int
    manual_include_count: int
    manual_exclude_count: int
    rejected_count: int
    error_count: int
    candidate_pass_rate: float
    average_duration: float | None
    rejection_counts: dict[str, RejectionSummary]
    thresholds: ThresholdSummary
    backend: BackendSummary

    @classmethod
    def from_summary(cls, summary: dict[str, object]) -> ReportResponse:
        return cls.model_validate(summary)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    api_version: str = "v1"


class ModelResponse(BaseModel):
    id: str
    label: str
    approximate_vram_mb: int | None


class ResourceLeaseResponse(BaseModel):
    job_id: str
    device_class: str
    acquired_at: str


class RuntimeStatusResponse(BaseModel):
    max_active_jobs: int
    active_jobs: int
    max_cuda_jobs: int
    active_cuda_jobs: int
    leases: list[ResourceLeaseResponse]


class ErrorDetail(BaseModel):
    code: str
    message: str
    action: str
    retryable: bool = False


class ErrorResponse(BaseModel):
    error: ErrorDetail
