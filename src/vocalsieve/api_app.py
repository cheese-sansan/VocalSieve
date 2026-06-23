"""FastAPI app assembly for the loopback local API."""

from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from . import __version__
from .api_auth import ALLOWED_WEB_ORIGINS, make_token_dependency
from .api_events import register_event_routes
from .api_jobs import register_job_routes
from .api_models import EventResponse
from .api_runtime import register_runtime_routes
from .api_workers import WorkerState
from .service import VocalSieveService


def create_app(
    database_path: str | Path | None = None,
    session_token: str | None = None,
) -> FastAPI:
    token = session_token or secrets.token_urlsafe(32)
    service = VocalSieveService(database_path)
    workers = WorkerState(service)

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
    app.state.workers = workers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(ALLOWED_WEB_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-VocalSieve-Token"],
    )

    require_token = make_token_dependency(token)
    register_runtime_routes(app, require_token)
    register_job_routes(app, require_token, service, workers)
    register_event_routes(app, token, service)

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        schema.setdefault("components", {}).setdefault("schemas", {})[
            "EventResponse"
        ] = EventResponse.model_json_schema(ref_template="#/components/schemas/{model}")
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app
