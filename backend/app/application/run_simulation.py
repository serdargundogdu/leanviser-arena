"""RunSimulation use case — thin orchestration over the pure domain.

Composes: ``LineConfig`` → DES engine → flow metrics. This is the seam where a
later slice adds persistence, a proper Run aggregate, composite scoring and the
HTTP adapter. For forward-compat with multi-tenant / benchmark work, the command
already carries optional actor/company identity (unused in v0.1 — no auth, no
storage, no personal data).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.simulation.engine import simulate
from app.domain.simulation.line import LineConfig
from app.domain.simulation.metrics import SimulationMetrics, compute_metrics


@dataclass(frozen=True)
class RunSimulationCommand:
    """Input to the use case. ``actor_id`` / ``company_id`` are placeholders for
    a future Run aggregate; they are role/identity seams, never personal data.
    """

    config: LineConfig
    actor_id: str | None = None
    company_id: str | None = None


def run_simulation(command: RunSimulationCommand) -> SimulationMetrics:
    """Execute the deterministic simulation and return its flow metrics."""
    log = simulate(command.config)
    return compute_metrics(log, command.config.due_date)
