"""Entry point for the Chopan API gateway."""
from __future__ import annotations

from fastapi import FastAPI

from .routes import router

app = FastAPI(title="Chopan Outreach Gateway", version="1.0.0")
app.include_router(router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "chopan-api-gateway"}
