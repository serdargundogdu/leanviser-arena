"""Composite Arena score — the reward thesis made executable. Pure functions.

The score rewards FLOW, not output. Three pillars, each normalized to [0, 1]:

  * lead time      — ideal (one-piece-flow floor) / realized median, capped at 1;
  * flow efficiency — value-added time / lead time (already in (0, 1]);
  * delivery       — share of orders inside the promised delivery window.

They are combined by a weighted mean and scaled to [0, 100]. Throughput is NOT a
term: overproduction raises WIP and lead time, which LOWERS the score — it can
never raise it. This property is guarded by ``tests/test_scoring.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.simulation.metrics import SimulationMetrics


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class ScoreWeights:
    """Weights for the three composite pillars; must sum to 1.0."""

    lead_time: float
    flow_efficiency: float
    delivery_reliability: float

    def __post_init__(self) -> None:
        total = self.lead_time + self.flow_efficiency + self.delivery_reliability
        if abs(total - 1.0) > 1e-9:
            raise ValueError("score weights must sum to 1.0")


@dataclass(frozen=True)
class Score:
    """Composite score in [0, 100] plus its three pillar sub-scores in [0, 1]."""

    composite: float
    lead_time_score: float
    flow_efficiency_score: float
    delivery_score: float


def compute_score(
    metrics: SimulationMetrics,
    ideal_lead_time: float,
    weights: ScoreWeights,
) -> Score:
    """Combine flow metrics into the composite Arena score.

    ``ideal_lead_time`` is the theoretical one-piece-flow floor (sum of station
    cycle-time means); the lead-time pillar rewards approaching it.
    """
    lead_time_score = _clamp01(ideal_lead_time / metrics.lead_time_median)
    flow_efficiency_score = _clamp01(metrics.flow_efficiency)
    delivery_score = _clamp01(metrics.delivery_reliability)
    composite = 100.0 * (
        weights.lead_time * lead_time_score
        + weights.flow_efficiency * flow_efficiency_score
        + weights.delivery_reliability * delivery_score
    )
    return Score(
        composite=composite,
        lead_time_score=lead_time_score,
        flow_efficiency_score=flow_efficiency_score,
        delivery_score=delivery_score,
    )
