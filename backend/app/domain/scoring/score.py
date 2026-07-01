"""Composite Arena score — the reward thesis made executable. Pure functions.

The score rewards FLOW, gated by demand. Three sub-scores, each in [0, 1]:

  * lead time      — ideal (one-piece-flow floor) / realized median, capped at 1;
  * flow efficiency — value-added time / lead time (already in (0, 1]);
  * delivery       — share of orders meeting the takt-paced demand schedule.

Flow quality is the weighted mean of the first two; the composite is then

    composite = 100 * flow_quality * delivery_reliability

so delivery GATES the score: flowing beautifully counts only to the extent you
delivered to demand. This closes the degenerate strategy of starving the line
(near-perfect lead time / flow efficiency, but missed demand → delivery → 0).

Throughput is NOT a term. Overproduction raises WIP and lead time (lowering
flow quality); starving misses demand (lowering the gate). Neither is rewarded.
Guarded by ``tests/test_scoring.py`` and ``tests/test_demand_takt.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.simulation.metrics import SimulationMetrics


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class ScoreWeights:
    """Weights for the two flow-quality pillars; must sum to 1.0.

    Delivery reliability is not weighted here — it gates the composite as a
    multiplier (see ``compute_score``).
    """

    lead_time: float
    flow_efficiency: float

    def __post_init__(self) -> None:
        total = self.lead_time + self.flow_efficiency
        if abs(total - 1.0) > 1e-9:
            raise ValueError("flow-quality weights must sum to 1.0")


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
    cycle-time means); the lead-time pillar rewards approaching it. Delivery
    reliability gates the weighted flow quality.
    """
    lead_time_score = _clamp01(ideal_lead_time / metrics.lead_time_median)
    flow_efficiency_score = _clamp01(metrics.flow_efficiency)
    delivery_score = _clamp01(metrics.delivery_reliability)
    flow_quality = (
        weights.lead_time * lead_time_score + weights.flow_efficiency * flow_efficiency_score
    )
    composite = 100.0 * flow_quality * delivery_score
    return Score(
        composite=composite,
        lead_time_score=lead_time_score,
        flow_efficiency_score=flow_efficiency_score,
        delivery_score=delivery_score,
    )
