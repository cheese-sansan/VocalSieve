"""Convenient synchronous and asynchronous SDK clients."""

from __future__ import annotations

import asyncio
from pathlib import Path

from .domain import FileResult, Job, PipelineConfig, ReviewDecision, RuntimePolicy
from .events import EventSink, ignore_event
from .service import VocalSieveService


class VocalSieveClient(VocalSieveService):
    def __enter__(self) -> VocalSieveClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class AsyncVocalSieveClient:
    def __init__(
        self,
        database_path: str | Path | None = None,
        runtime_policy: RuntimePolicy | None = None,
    ):
        self._client = VocalSieveClient(database_path, runtime_policy)

    async def __aenter__(self) -> AsyncVocalSieveClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await asyncio.to_thread(self._client.close)

    async def create_job(self, config: PipelineConfig) -> Job:
        return await asyncio.to_thread(self._client.create_job, config)

    async def run_job(self, job_id: str, event_sink: EventSink = ignore_event) -> Job:
        return await asyncio.to_thread(self._client.run_job, job_id, event_sink)

    async def resume_job(self, job_id: str, event_sink: EventSink = ignore_event) -> Job:
        return await asyncio.to_thread(self._client.resume_job, job_id, event_sink)

    async def cancel_job(self, job_id: str) -> None:
        await asyncio.to_thread(self._client.cancel_job, job_id)

    async def list_jobs(self, limit: int = 100) -> list[Job]:
        return await asyncio.to_thread(self._client.list_jobs, limit)

    async def query_results(self, job_id: str) -> list[FileResult]:
        return await asyncio.to_thread(self._client.query_results, job_id)

    async def review_result(
        self,
        job_id: str,
        relative_path: str,
        decision: ReviewDecision | None,
        note: str | None = None,
    ) -> FileResult:
        return await asyncio.to_thread(
            self._client.review_result,
            job_id,
            relative_path,
            decision,
            note,
        )

    async def export_job(self, job_id: str) -> dict[str, str]:
        return await asyncio.to_thread(self._client.export_job, job_id)

    async def report_job(self, job_id: str) -> dict:
        return await asyncio.to_thread(self._client.report_job, job_id)

    async def runtime_status(self) -> dict:
        return await asyncio.to_thread(self._client.runtime_status)
