"""RunScenario use case — the v0.2 game loop, server-authoritative.

Given a scenario and the player's lever values, it builds the effective line
config (seed stays server-side), runs the deterministic DES, computes flow
metrics and the composite score, and assembles a debrief for the UI. No
persistence, no auth (both deferred).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.coaching.coach import Insight, diagnose
from app.domain.scenario.scenario import Scenario
from app.domain.scoring.score import Score, compute_score
from app.domain.simulation.engine import simulate
from app.domain.simulation.metrics import SimulationMetrics, compute_metrics


@dataclass(frozen=True)
class RunScenarioCommand:
    """Player input. ``actor_id`` / ``company_id`` are forward-compat identity
    seams (no auth/storage in v0.2); never personal data.
    """

    scenario: Scenario
    batch_size: float
    release_interval: float
    actor_id: str | None = None
    company_id: str | None = None


@dataclass(frozen=True)
class DebriefResult:
    """Everything the debrief UI needs from one run.

    ``value_added_mean`` + ``waiting_mean`` decompose the mean lead time for the
    hero flow-time chart (value-adding vs waiting). ``applied_*`` echo the
    clamped lever values actually used.
    """

    metrics: SimulationMetrics
    score: Score
    insights: tuple[Insight, ...]
    lead_times: tuple[float, ...]
    on_time: tuple[bool, ...]
    release_times: tuple[float, ...]
    completion_times: tuple[float, ...]
    value_added_mean: float
    waiting_mean: float
    applied_batch_size: int
    applied_release_interval: float
    credit_cost: float


def run_scenario(command: RunScenarioCommand) -> DebriefResult:
    scenario = command.scenario
    # Game rule: lever moves must fit the kaizen budget (raises if exceeded).
    credit_cost = scenario.validate_budget(command.batch_size, command.release_interval)
    config = scenario.build_config(command.batch_size, command.release_interval)
    log = simulate(config)
    metrics = compute_metrics(log, config.takt_time, config.delivery_window)
    score = compute_score(metrics, scenario.ideal_lead_time, scenario.weights)
    insights = tuple(
        diagnose(
            metrics=metrics,
            score=score,
            batch_size=config.batch_size,
            release_interval=config.release_interval,
            takt_time=config.takt_time,
        )
    )

    order_count = len(log.orders)
    value_added_mean = sum(o.value_added_time for o in log.orders) / order_count
    waiting_mean = metrics.lead_time_mean - value_added_mean
    return DebriefResult(
        metrics=metrics,
        score=score,
        insights=insights,
        lead_times=tuple(o.lead_time for o in log.orders),
        on_time=tuple(o.is_on_time(config.takt_time, config.delivery_window) for o in log.orders),
        release_times=tuple(o.release_time for o in log.orders),
        completion_times=tuple(o.completion_time for o in log.orders),
        value_added_mean=value_added_mean,
        waiting_mean=waiting_mean,
        applied_batch_size=config.batch_size,
        applied_release_interval=config.release_interval,
        credit_cost=credit_cost,
    )
