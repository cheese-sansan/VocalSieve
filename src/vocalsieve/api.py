"""Loopback-only FastAPI adapter."""

from __future__ import annotations

import asyncio
import logging
import secrets
import threading
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .api_models import (
    CheckResponse,
    ConfigRequest,
    ErrorResponse,
    EventResponse,
    ExportResponse,
    FileResultResponse,
    HealthResponse,
    JobResponse,
    ModelResponse,
    ReviewRequest,
    RuntimeStatusResponse,
)
from .doctor import run_diagnostics
from .domain import JobStatus, ReviewDecision, RuntimePolicy
from .errors import JobNotFoundError, JobStateError, ResourceCapacityError
from .logging_config import configure_file_logging
from .service import VocalSieveService

MODELS = (
    ModelResponse(id="tiny", label="Tiny", approximate_vram_mb=1000),
    ModelResponse(id="base", label="Base", approximate_vram_mb=1200),
    ModelResponse(id="small", label="Small", approximate_vram_mb=2000),
    ModelResponse(id="medium", label="Medium", approximate_vram_mb=5000),
    ModelResponse(id="large-v3", label="Large v3", approximate_vram_mb=10000),
)

logger = logging.getLogger(__name__)


def create_app(
    database_path: str | Path | None = None,
    session_token: str | None = None,
    runtime_policy: RuntimePolicy | None = None,
) -> FastAPI:
    configure_file_logging()
    token = session_token or secrets.token_urlsafe(32)
    service = VocalSieveService(database_path, runtime_policy)
    workers: dict[str, threading.Thread] = {}
    workers_lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        with workers_lock:
            active = list(workers.items())
        for job_id, _worker in active:
            with suppress(JobNotFoundError, JobStateError):
                service.cancel_job(job_id)
        for _job_id, worker in active:
            worker.join(timeout=5)
        service.close()

    app = FastAPI(
        title="VocalSieve Local API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
        responses={
            401: {"model": ErrorResponse, "description": "Authentication failed"},
            404: {"model": ErrorResponse, "description": "Resource not found"},
            409: {"model": ErrorResponse, "description": "State or capacity conflict"},
            422: {"model": ErrorResponse, "description": "Invalid request"},
            503: {"model": ErrorResponse, "description": "Backend unavailable"},
        },
    )
    app.state.session_token = token
    app.state.service = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-VocalSieve-Token"],
    )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            detail = exc.detail
        else:
            defaults = {
                401: (
                    "invalid_session_token",
                    "Restart the local API and use the newly printed session token.",
                    False,
                ),
                404: ("not_found", "Refresh the job list and verify the identifier.", False),
                409: ("state_conflict", "Refresh the job state and retry if appropriate.", True),
                422: ("invalid_request", "Correct the request fields and try again.", False),
                503: ("backend_unavailable", "Run VocalSieve doctor and retry.", True),
            }
            code, action, retryable = defaults.get(
                exc.status_code,
                ("request_failed", "Review the request and local logs.", False),
            )
            detail = {
                "code": code,
                "message": str(exc.detail),
                "action": action,
                "retryable": retryable,
            }
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": detail},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first.get("loc", ()))
        message = str(first.get("msg", "Request validation failed"))
        if location:
            message = f"{location}: {message}"
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": message,
                    "action": "Correct the request fields and try again.",
                    "retryable": False,
                }
            },
        )

    def require_token(x_vocalsieve_token: str = Header(default="")) -> None:
        if not secrets.compare_digest(x_vocalsieve_token, token):
            raise HTTPException(status_code=401, detail="Invalid session token")

    def capacity_detail(exc: ResourceCapacityError) -> dict:
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

    def make_worker(job_id: str) -> threading.Thread:
        def target() -> None:
            try:
                service.run_reserved_job(job_id)
                job = service.get_job(job_id)
                if job.status in {JobStatus.RUNNING, JobStatus.CANCELLING}:
                    service.database.set_job_state(
                        job_id,
                        JobStatus.FAILED,
                        error="Background worker exited before the job reached a terminal state",
                    )
            except Exception as exc:
                logger.exception("Background job %s failed", job_id)
                with suppress(JobNotFoundError):
                    job = service.get_job(job_id)
                    if job.status in {JobStatus.RUNNING, JobStatus.CANCELLING}:
                        service.database.set_job_state(
                            job_id,
                            JobStatus.FAILED,
                            error=str(exc),
                        )
            finally:
                with workers_lock:
                    workers.pop(job_id, None)

        return threading.Thread(target=target, name=f"vocalsieve-{job_id[:8]}", daemon=True)

    def start_worker(job_id: str, worker: threading.Thread) -> None:
        with workers_lock:
            workers[job_id] = worker
        try:
            worker.start()
        except RuntimeError as exc:
            with workers_lock:
                workers.pop(job_id, None)
            service.database.set_job_state(job_id, JobStatus.FAILED, error=str(exc))
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "worker_start_failed",
                    "message": str(exc),
                    "action": "Restart the local API and retry the job.",
                    "retryable": True,
                },
            ) from exc

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    @app.get(
        "/api/v1/doctor",
        response_model=list[CheckResponse],
        dependencies=[Depends(require_token)],
    )
    def doctor(
        deep: bool = False,
        device: str = Query(default="auto", pattern="^(auto|cpu|cuda)$"),
        model: str = "tiny",
    ) -> list[CheckResponse]:
        return [
            CheckResponse(**asdict(check))
            for check in run_diagnostics(deep=deep, device=device, model_size=model)
        ]

    @app.get(
        "/api/v1/models",
        response_model=list[ModelResponse],
        dependencies=[Depends(require_token)],
    )
    def models() -> tuple[ModelResponse, ...]:
        return MODELS

    @app.get(
        "/api/v1/runtime",
        response_model=RuntimeStatusResponse,
        dependencies=[Depends(require_token)],
    )
    def runtime_status() -> RuntimeStatusResponse:
        return RuntimeStatusResponse(**service.runtime_status())

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
            worker = make_worker(job.id)
            start_worker(job.id, worker)
            return JobResponse.from_domain(job)
        except ResourceCapacityError as exc:
            if job is not None:
                service.database.delete_pending_job(job.id)
            raise HTTPException(
                status_code=409,
                detail=capacity_detail(exc),
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
            worker = make_worker(job.id)
            start_worker(job.id, worker)
            return JobResponse.from_domain(job)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Job not found") from exc
        except ResourceCapacityError as exc:
            raise HTTPException(status_code=409, detail=capacity_detail(exc)) from exc
        except JobStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

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

    @app.patch(
        "/api/v1/jobs/{job_id}/results/review",
        response_model=FileResultResponse,
        dependencies=[Depends(require_token)],
    )
    def review_result(job_id: str, request: ReviewRequest) -> FileResultResponse:
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

    @app.websocket("/api/v1/jobs/{job_id}/events")
    async def events(websocket: WebSocket, job_id: str, after: int = 0) -> None:
        websocket_token = websocket.query_params.get("token", "")
        origin = websocket.headers.get("origin", "")
        allowed_origins = {"http://127.0.0.1:5173", "http://localhost:5173"}
        if not secrets.compare_digest(websocket_token, token):
            await websocket.close(code=4401, reason="Invalid session token")
            return
        if origin not in allowed_origins:
            await websocket.close(code=4403, reason="Origin not allowed")
            return
        await websocket.accept()
        cursor = after
        try:
            service.get_job(job_id)
            while True:
                rows = service.database.get_events(job_id, cursor)
                for row in rows:
                    cursor = row["id"]
                    await websocket.send_json(EventResponse(**row).model_dump())
                job = service.get_job(job_id)
                if (
                    job.status in {JobStatus.CANCELLED, JobStatus.COMPLETED, JobStatus.FAILED}
                    and not rows
                ):
                    break
                await asyncio.sleep(0.2)
        except JobNotFoundError:
            await websocket.close(code=4404, reason="Job not found")
        except WebSocketDisconnect:
            return
        await websocket.close(code=1000)

    return app
