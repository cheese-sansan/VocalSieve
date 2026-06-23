"""Authentication helpers for the loopback API."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from typing import Annotated

from fastapi import Header, HTTPException, WebSocket

ALLOWED_WEB_ORIGINS = {"http://127.0.0.1:5173", "http://localhost:5173"}


def make_token_dependency(session_token: str) -> Callable[[str], None]:
    def require_token(x_vocalsieve_token: Annotated[str, Header()] = "") -> None:
        if not secrets.compare_digest(x_vocalsieve_token, session_token):
            raise HTTPException(status_code=401, detail="Invalid session token")

    return require_token


async def validate_websocket(websocket: WebSocket, session_token: str) -> bool:
    websocket_token = websocket.query_params.get("token", "")
    origin = websocket.headers.get("origin", "")
    if not secrets.compare_digest(websocket_token, session_token):
        await websocket.close(code=4401, reason="Invalid session token")
        return False
    if origin not in ALLOWED_WEB_ORIGINS:
        await websocket.close(code=4403, reason="Origin not allowed")
        return False
    return True
