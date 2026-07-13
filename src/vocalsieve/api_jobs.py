"""Job lifecycle, result, review, export, and report endpoints."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Query

from .api_models import (
    ConfigRequest,
    ExportResponse,
    FileResultResponse,
    JobResponse,
    ReportResponse,
    ReviewRequest,
)
from .api_workers import WorkerStartError, WorkerState
from .domain import ReviewDecision
from .errors import JobNotFoundError, JobStateError, ResourceCapacityError
from .service import VocalSieveService


def capacity_detail(exc: ResourceCapacityError) -> dict[str, object]:
    return {
        "code": "path_conflict" if exc.resource == "paths" else "capacity_exceeded",
        "message": str(exc),
        "action": (
            "Choose non-overlapping source and output directories."
            if exc.resource == "paths"
            else "Wait for an active job to finish or raise the configured limit."
        ),
        "retryable": True,
    }


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
        job = None
        try:
            job = service.create_job(request.to_domain())
            job = service.reserve_job(job.id)
            workers.start_reserved(job.id)
            return JobResponse.from_domain(job)
        except ResourceCapacityError as exc:
            if job is not None:
                service.database.delete_pending_job(job.id)
            raise HTTPException(status_code=409, detail=capacity_detail(exc)) from exc
        except WorkerStartError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "worker_start_failed",
                    "message": str(exc),
                    "action": "Restart the local API and retry the job.",
                    "retryable": True,
                },
            ) from exc
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
            job = service.reserve_job(job_id)
            workers.start_reserved(job.id)
            return JobResponse.from_domain(job)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ResourceCapacityError as exc:
            raise HTTPException(status_code=409, detail=capacity_detail(exc)) from exc
        except JobStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except WorkerStartError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "worker_start_failed",
                    "message": str(exc),
                    "action": "Restart the local API and retry the job.",
                    "retryable": True,
                },
            ) from exc

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

    def apply_review(job_id: str, request: ReviewRequest) -> FileResultResponse:
        try:
            decision = None if request.decision == "automatic" else ReviewDecision(request.decision)
            return FileResultResponse.from_domain(
                service.review_result(job_id, request.relative_path, decision, request.note)
            )
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job or result not found") from exc
        except JobStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post(
        "/api/v1/jobs/{job_id}/results/review",
        response_model=FileResultResponse,
        dependencies=[Depends(require_token)],
    )
    def review_result(job_id: str, request: ReviewRequest) -> FileResultResponse:
        return apply_review(job_id, request)

    @app.patch(
        "/api/v1/jobs/{job_id}/results/review",
        response_model=FileResultResponse,
        dependencies=[Depends(require_token)],
        deprecated=True,
    )
    def review_result_legacy(job_id: str, request: ReviewRequest) -> FileResultResponse:
        return apply_review(job_id, request)

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
