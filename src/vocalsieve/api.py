"""Compatibility entry point for the loopback-only FastAPI adapter."""

from __future__ import annotations

from .api_app import create_app

__all__ = ["create_app"]
