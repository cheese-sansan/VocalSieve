"""Runtime and environment endpoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

from fastapi import Depends, FastAPI, Query

from . import __version__
from .api_models import CheckResponse, HealthResponse, ModelResponse, RuntimeStatusResponse
from .doctor import run_diagnostics
from .service import VocalSieveService

MODELS = (
    ModelResponse(id="tiny", label="Tiny", approximate_vram_mb=1000),
    ModelResponse(id="base", label="Base", approximate_vram_mb=1200),
    ModelResponse(id="small", label="Small", approximate_vram_mb=2000),
    ModelResponse(id="medium", label="Medium", approximate_vram_mb=5000),
    ModelResponse(id="large-v3", label="Large v3", approximate_vram_mb=10000),
)


def register_runtime_routes(
    app: FastAPI,
    require_token: Callable[[str], None],
    service: VocalSieveService,
) -> None:
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
