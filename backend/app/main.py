"""FastAPI application entrypoint (adapter-layer boundary).

Exposes the HTTP surface of LeanViser ARENA. For v0.1 this is intentionally
minimal — only a liveness probe. Simulation/scoring endpoints are wired in a
later slice; the pure domain engine already lives under
``app.domain.simulation`` and the ``RunSimulation`` use case under
``app.application``.
"""

from fastapi import FastAPI

app = FastAPI(title="LeanViser ARENA", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by CI and Cloud Run."""
    return {"status": "ok"}
