"""FastAPI application entrypoint (adapter-layer boundary).

Exposes the HTTP surface of LeanViser ARENA. For v0.1 this is intentionally
minimal — only a liveness probe. Simulation/scoring endpoints are wired in a
later slice; the pure domain engine already lives under
``app.domain.simulation`` and the ``RunSimulation`` use case under
``app.application``.
"""

from fastapi import FastAPI

from app.adapters.http.routes import router as arena_router

app = FastAPI(title="LeanViser ARENA", version="0.2.0")
app.include_router(arena_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by CI and Cloud Run."""
    return {"status": "ok"}
