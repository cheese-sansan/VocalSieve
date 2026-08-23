"""FastAPI app assembly for the loopback local API."""

from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from . import __version__
from .api_auth import ALLOWED_WEB_ORIGINS, make_token_dependency
from .api_events import register_event_routes
from .api_jobs import register_job_routes
from .api_models import ErrorResponse, EventResponse
from .api_runtime import register_runtime_routes
from .api_workers import WorkerState
from .domain import RuntimePolicy
from .logging_config import configure_file_logging
from .service import VocalSieveService


def _register_error_handlers(app: FastAPI) -> None:
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


def create_app(
    database_path: str | Path | None = None,
    session_token: str | None = None,
    runtime_policy: RuntimePolicy | None = None,
) -> FastAPI:
    configure_file_logging()
    token = session_token or secrets.token_urlsafe(32)
    service = VocalSieveService(database_path, runtime_policy)
    workers = WorkerState(service)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        workers.shutdown()
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
    app.state.workers = workers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(ALLOWED_WEB_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-VocalSieve-Token"],
    )
    _register_error_handlers(app)

    require_token = make_token_dependency(token)
    register_runtime_routes(app, require_token, service)
    register_job_routes(app, require_token, service, workers)
    register_event_routes(app, token, service)

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        schema.setdefault("components", {}).setdefault("schemas", {})["EventResponse"] = (
            EventResponse.model_json_schema(ref_template="#/components/schemas/{model}")
        )
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app
