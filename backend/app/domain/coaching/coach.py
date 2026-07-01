"""Rule-based coaching: diagnose a run and suggest the next lever move.

Pure function over the run's metrics, score and applied levers. Emits
language-neutral ``Insight`` codes (the UI supplies Turkish text). Rules are
tied to the two levers so guidance is actionable: "release slower than takt →
you are starving the line", "batch too large → early finishers wait", etc.

This layer is advisory only — it reads the outcome, it never changes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.scoring.score import Score
from app.domain.simulation.metrics import SimulationMetrics

# Thresholds. Kept as named constants so the rules read like sentences.
_ELEVATED_WIP = 6.0  # ~2x the one-piece-at-takt steady state (≈ station count)
_LOW_FLOW_EFFICIENCY = 0.6
_POOR_DELIVERY = 0.9
_MISSED_DEMAND = 0.5
_BALANCED_COMPOSITE = 70.0


class Severity(StrEnum):
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"


class InsightCode(StrEnum):
    OVERPACED = "overpaced"  # releasing slower than takt → starving the line
    FLOODING = "flooding"  # releasing faster than demand → WIP piles up
    LARGE_BATCH = "large_batch"  # transfer batch too big → early finishers wait
    MISSED_DEMAND = "missed_demand"  # behind the takt schedule (any cause)
    BALANCED_FLOW = "balanced_flow"  # takt-paced, small batch → reward
    KEEP_TUNING = "keep_tuning"  # no dominant signal; nudge to keep adjusting


@dataclass(frozen=True)
class Insight:
    code: InsightCode
    severity: Severity


def diagnose(
    *,
    metrics: SimulationMetrics,
    score: Score,
    batch_size: int,
    release_interval: float,
    takt_time: float,
) -> list[Insight]:
    """Return coaching insights, most actionable first. Never empty."""
    insights: list[Insight] = []

    # Starving the line: releasing slower than demand → cannot keep up.
    if release_interval > takt_time and metrics.delivery_reliability < _POOR_DELIVERY:
        insights.append(Insight(InsightCode.OVERPACED, Severity.CRITICAL))

    # Overproduction: releasing faster than demand → work-in-process piles up.
    if release_interval < takt_time and metrics.average_wip > _ELEVATED_WIP:
        insights.append(Insight(InsightCode.FLOODING, Severity.WARNING))

    # Large transfer batch: early finishers wait for their batchmates.
    if batch_size > 1 and metrics.flow_efficiency < _LOW_FLOW_EFFICIENCY:
        insights.append(Insight(InsightCode.LARGE_BATCH, Severity.WARNING))

    # Behind the takt schedule for a reason other than over-pacing.
    if metrics.delivery_reliability < _MISSED_DEMAND and release_interval <= takt_time:
        insights.append(Insight(InsightCode.MISSED_DEMAND, Severity.CRITICAL))

    # Reward: balanced, takt-paced flow.
    if score.composite >= _BALANCED_COMPOSITE:
        insights.append(Insight(InsightCode.BALANCED_FLOW, Severity.GOOD))

    if not insights:
        insights.append(Insight(InsightCode.KEEP_TUNING, Severity.WARNING))
    return insights
