"""FastAPI entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import parameters, simulations

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

app.include_router(simulations.router, prefix="/api/simulations", tags=["simulations"])
app.include_router(parameters.router, prefix="/api/parameters", tags=["parameters"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
