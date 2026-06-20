"""Structured pipeline events for every presentation layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol


class EventType(StrEnum):
    JOB_STARTED = "job_started"
    STAGE_STARTED = "stage_started"
    FILE_COMPLETED = "file_completed"
    PROGRESS = "progress"
    WARNING = "warning"
    ERROR = "error"
    CANCELLED = "cancelled"
    JOB_COMPLETED = "job_completed"


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    job_id: str
    type: EventType
    message: str
    stage: str | None = None
    current: int | None = None
    total: int | None = None
    relative_path: str | None = None
    accepted: bool | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


class EventSink(Protocol):
    def __call__(self, event: PipelineEvent) -> None: ...


def ignore_event(event: PipelineEvent) -> None:
    """Default sink used by non-interactive callers."""
