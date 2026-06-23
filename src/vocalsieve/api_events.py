"""Persisted event WebSocket endpoint."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .api_auth import validate_websocket
from .api_models import EventResponse
from .domain import JobStatus
from .errors import JobNotFoundError
from .service import VocalSieveService


def register_event_routes(app: FastAPI, session_token: str, service: VocalSieveService) -> None:
    @app.websocket("/api/v1/jobs/{job_id}/events")
    async def events(websocket: WebSocket, job_id: str, after: int = 0) -> None:
        if not await validate_websocket(websocket, session_token):
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
