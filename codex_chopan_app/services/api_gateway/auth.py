"""Lightweight API key authentication utilities."""
from __future__ import annotations

import os
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _expected_key() -> str:
    return os.getenv("CHOPAN_API_KEY", "test-key")


async def require_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str:
    if not api_key or api_key != _expected_key():
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key
