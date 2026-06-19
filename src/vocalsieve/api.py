"""Loopback-only FastAPI adapter."""

from __future__ import annotations

import asyncio
import secrets
import threading
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api_models import (
    CheckResponse,
    ConfigRequest,
    EventResponse,
    ExportResponse,
    FileResultResponse,
    HealthResponse,
    JobResponse,
    ModelResponse,
)
from .doctor import run_diagnostics
from .domain import JobStatus
from .errors import JobNotFoundError, JobStateError
from .service import VocalSieveService

MODELS = (
    ModelResponse(id="tiny", label="Tiny", approximate_vram_mb=1000),
    ModelResponse(id="base", label="Base", approximate_vram_mb=1200),
    ModelResponse(id="small", label="Small", approximate_vram_mb=2000),
    ModelResponse(id="medium", label="Medium", approximate_vram_mb=5000),
    ModelResponse(id="large-v3", label="Large v3", approximate_vram_mb=10000),
)


def create_app(
    database_path: str | Path | None = None,
    session_token: str | None = None,
) -> FastAPI:
    token = session_token or secrets.token_urlsafe(32)
    service = VocalSieveService(database_path)
    workers: dict[str, threading.Thread] = {}
    workers_lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        service.close()

    app = FastAPI(
        title="VocalSieve Local API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.session_token = token
    app.state.service = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-VocalSieve-Token"],
    )

    def require_token(x_vocalsieve_token: str = Header(default="")) -> None:
        if not secrets.compare_digest(x_vocalsieve_token, token):
            raise HTTPException(status_code=401, detail="Invalid session token")

    def make_worker(job_id: str, resume: bool = False) -> threading.Thread:
        def target() -> None:
            try:
                if resume:
                    service.resume_job(job_id)
                else:
                    service.run_job(job_id)
            finally:
                with workers_lock:
                    workers.pop(job_id, None)

        return threading.Thread(target=target, name=f"vocalsieve-{job_id[:8]}", daemon=True)

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

    @app.post(
        "/api/v1/jobs",
        response_model=JobResponse,
        status_code=202,
        dependencies=[Depends(require_token)],
    )
    def create_job(request: ConfigRequest) -> JobResponse:
        try:
            with workers_lock:
                if workers:
                    raise HTTPException(status_code=409, detail="Another job is already active")
                job = service.create_job(request.to_domain())
                worker = make_worker(job.id)
                workers[job.id] = worker
            worker.start()
            return JobResponse.from_domain(job)
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
            with workers_lock:
                if workers:
                    raise HTTPException(status_code=409, detail="Another job is already active")
                worker = make_worker(job.id, resume=True)
                workers[job.id] = worker
            worker.start()
            return JobResponse.from_domain(job)
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
