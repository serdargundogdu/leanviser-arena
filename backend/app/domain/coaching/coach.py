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
_VARIABILITY_HEADROOM_FE = 0.85  # flow otherwise sane, yet waiting persists
_UNINVESTED_VARIANCE = 0.5  # standard-work lever mostly untouched
_SMALL_BATCH = 2
_NEAR_TAKT = 0.9  # release within ~10% of takt counts as takt-paced
_LOOSE_CAP = 8.0  # a cap at/above this is not really pulling yet
_STARVED_DELIVERY = 0.7  # good flow but late vs takt: the cap starves the line


class Severity(StrEnum):
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"


class InsightCode(StrEnum):
    OVERPACED = "overpaced"  # releasing slower than takt → starving the line
    FLOODING = "flooding"  # releasing faster than demand → WIP piles up
    LARGE_BATCH = "large_batch"  # transfer batch too big → early finishers wait
    MISSED_DEMAND = "missed_demand"  # behind the takt schedule (any cause)
    HIGH_VARIABILITY = "high_variability"  # remaining waste is cycle-time noise
    TRY_PULL = "try_pull"  # cap lever available but unused while flow suffers
    CAP_TOO_TIGHT = "cap_too_tight"  # tight cap starves the takt schedule
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
    variance_factor: float = 1.0,
    wip_cap: float | None = None,
) -> list[Insight]:
    """Return coaching insights, most actionable first. Never empty.

    ``wip_cap`` is the applied cap when the scenario exposes that lever, else
    None — the pull rules only speak where pull is actually playable.
    """
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

    # Flow is otherwise sane (small batch, takt-paced) yet waiting persists:
    # the remaining waste is cycle-time variability — invest in standard work.
    if (
        batch_size <= _SMALL_BATCH
        and release_interval >= takt_time * _NEAR_TAKT
        and metrics.flow_efficiency < _VARIABILITY_HEADROOM_FE
        and variance_factor > _UNINVESTED_VARIANCE
    ):
        insights.append(Insight(InsightCode.HIGH_VARIABILITY, Severity.WARNING))

    # Pull opportunity: the cap lever exists but sits loose while flow suffers —
    # pull is the cheap containment (manage WIP, not the schedule).
    if (
        wip_cap is not None
        and wip_cap >= _LOOSE_CAP
        and metrics.flow_efficiency < _VARIABILITY_HEADROOM_FE
    ):
        insights.append(Insight(InsightCode.TRY_PULL, Severity.WARNING))

    # Over-pulled: a tight cap with decent flow but poor delivery starves the
    # takt schedule — loosen a notch or keep the backlog fed.
    if (
        wip_cap is not None
        and wip_cap < _LOOSE_CAP
        and metrics.delivery_reliability < _STARVED_DELIVERY
        and metrics.flow_efficiency >= _LOW_FLOW_EFFICIENCY
    ):
        insights.append(Insight(InsightCode.CAP_TOO_TIGHT, Severity.CRITICAL))

    # Reward: balanced, takt-paced flow.
    if score.composite >= _BALANCED_COMPOSITE:
        insights.append(Insight(InsightCode.BALANCED_FLOW, Severity.GOOD))

    if not insights:
        insights.append(Insight(InsightCode.KEEP_TUNING, Severity.WARNING))
    return insights
