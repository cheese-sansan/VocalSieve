"""Authentication helpers for the loopback API."""

from __future__ import annotations

import base64
import secrets
from collections.abc import Callable
from typing import Annotated

from fastapi import Header, HTTPException, WebSocket

ALLOWED_WEB_ORIGINS = {"http://127.0.0.1:5173", "http://localhost:5173"}
TOKEN_PROTOCOL_PREFIX = "vocalsieve.token."


def make_token_dependency(session_token: str) -> Callable[[str], None]:
    def require_token(x_vocalsieve_token: Annotated[str, Header()] = "") -> None:
        if not secrets.compare_digest(x_vocalsieve_token, session_token):
            raise HTTPException(status_code=401, detail="Invalid session token")

    return require_token


def _websocket_token(websocket: WebSocket) -> tuple[str, str | None]:
    for protocol in websocket.headers.get("sec-websocket-protocol", "").split(","):
        protocol = protocol.strip()
        if not protocol.startswith(TOKEN_PROTOCOL_PREFIX):
            continue
        encoded = protocol.removeprefix(TOKEN_PROTOCOL_PREFIX)
        try:
            padding = "=" * (-len(encoded) % 4)
            token = base64.urlsafe_b64decode(f"{encoded}{padding}").decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return "", None
        return token, protocol
    return websocket.query_params.get("token", ""), None


async def validate_websocket(websocket: WebSocket, session_token: str) -> tuple[bool, str | None]:
    websocket_token, protocol = _websocket_token(websocket)
    origin = websocket.headers.get("origin", "")
    if not secrets.compare_digest(websocket_token, session_token):
        await websocket.close(code=4401, reason="Invalid session token")
        return False, None
    if origin not in ALLOWED_WEB_ORIGINS:
        await websocket.close(code=4403, reason="Origin not allowed")
        return False, None
    return True, protocol
