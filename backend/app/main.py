"""FastAPI entrypoint."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes import auth, parameters, simulations

app = FastAPI(
    title="Real World Sim API",
    description="Discrete-event simulation API for cytopathology and histopathology workflows.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(simulations.router, prefix="/api/simulations", tags=["simulations"])
app.include_router(parameters.router, prefix="/api/parameters", tags=["parameters"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_STATIC_DIR = Path(os.getenv("STATIC_DIR", "")).expanduser()
if _STATIC_DIR.is_dir():
    _assets = _STATIC_DIR / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/")
    def spa_index() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        candidate = _STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_STATIC_DIR / "index.html")
