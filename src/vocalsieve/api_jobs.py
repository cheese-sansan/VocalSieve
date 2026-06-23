"""Job lifecycle, result, export, and report endpoints."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Query

from .api_models import (
    ConfigRequest,
    ExportResponse,
    FileResultResponse,
    JobResponse,
    ReportResponse,
)
from .api_workers import WorkerState
from .errors import JobNotFoundError, JobStateError
from .service import VocalSieveService


def register_job_routes(
    app: FastAPI,
    require_token: Callable[[str], None],
    service: VocalSieveService,
    workers: WorkerState,
) -> None:
    @app.post(
        "/api/v1/jobs",
        response_model=JobResponse,
        status_code=202,
        dependencies=[Depends(require_token)],
    )
    def create_job(request: ConfigRequest) -> JobResponse:
        try:
            job = workers.create_and_start(lambda: service.create_job(request.to_domain()))
            return JobResponse.from_domain(job)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get(
        "/api/v1/jobs",
        response_model=list[JobResponse],
        dependencies=[Depends(require_token)],
    )
    def list_jobs(limit: int = Query(default=100, ge=1, le=500)) -> list[JobResponse]:
        return [JobResponse.from_domain(job) for job in service.list_jobs(limit)]

    @app.get(
        "/api/v1/jobs/{job_id}",
        response_model=JobResponse,
        dependencies=[Depends(require_token)],
    )
    def get_job(job_id: str) -> JobResponse:
        try:
            return JobResponse.from_domain(service.get_job(job_id))
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc

    @app.post(
        "/api/v1/jobs/{job_id}/cancel",
        response_model=JobResponse,
        dependencies=[Depends(require_token)],
    )
    def cancel_job(job_id: str) -> JobResponse:
        try:
            service.cancel_job(job_id)
            return JobResponse.from_domain(service.get_job(job_id))
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except JobStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post(
        "/api/v1/jobs/{job_id}/resume",
        response_model=JobResponse,
        status_code=202,
        dependencies=[Depends(require_token)],
    )
    def resume_job(job_id: str) -> JobResponse:
        try:
            job = service.get_job(job_id)
            workers.start(job.id, resume=True)
            return JobResponse.from_domain(job)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc

    @app.get(
        "/api/v1/jobs/{job_id}/results",
        response_model=list[FileResultResponse],
        dependencies=[Depends(require_token)],
    )
    def results(
        job_id: str,
        status: str | None = None,
        language: str | None = None,
        reason: str | None = None,
    ) -> list[FileResultResponse]:
        try:
            return [
                FileResultResponse.from_domain(result)
                for result in service.query_results(
                    job_id, status=status, language=language, reason=reason
                )
            ]
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc

    @app.get(
        "/api/v1/jobs/{job_id}/report",
        response_model=ReportResponse,
        dependencies=[Depends(require_token)],
    )
    def report(job_id: str) -> ReportResponse:
        try:
            return ReportResponse.from_summary(service.report_job(job_id))
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc

    @app.post(
        "/api/v1/jobs/{job_id}/export",
        response_model=ExportResponse,
        dependencies=[Depends(require_token)],
    )
    def export(job_id: str) -> ExportResponse:
        try:
            files = service.export_job(job_id)
            return ExportResponse(count=len(files), files=files)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
