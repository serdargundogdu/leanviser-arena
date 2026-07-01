"""Composite score invariants — bounds, weight validity, and the reward thesis:
throughput is not a term, and better flow always scores higher.
"""

import pytest

from app.domain.scoring.score import Score, ScoreWeights, compute_score
from app.domain.simulation.metrics import SimulationMetrics

WEIGHTS = ScoreWeights(lead_time=0.4, flow_efficiency=0.3, delivery_reliability=0.3)
IDEAL_LEAD_TIME = 15.0


def _metrics(
    *,
    lead_median: float,
    flow_efficiency: float,
    delivery: float,
    throughput: float,
    lead_mean: float | None = None,
) -> SimulationMetrics:
    return SimulationMetrics(
        lead_time_median=lead_median,
        lead_time_mean=lead_mean if lead_mean is not None else lead_median,
        average_wip=10.0,
        flow_efficiency=flow_efficiency,
        throughput=throughput,
        delivery_reliability=delivery,
        order_count=60,
        makespan=400.0,
    )


def test_score_within_bounds() -> None:
    score = compute_score(
        _metrics(lead_median=30.0, flow_efficiency=0.5, delivery=0.8, throughput=0.16),
        IDEAL_LEAD_TIME,
        WEIGHTS,
    )
    assert isinstance(score, Score)
    assert 0.0 <= score.composite <= 100.0
    for sub in (score.lead_time_score, score.flow_efficiency_score, score.delivery_score):
        assert 0.0 <= sub <= 1.0


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        ScoreWeights(lead_time=0.5, flow_efficiency=0.3, delivery_reliability=0.3)


def test_throughput_is_not_a_term() -> None:
    # Two runs identical on every flow pillar but with very different throughput
    # must score identically — throughput cannot move the score.
    low_output = _metrics(lead_median=20.0, flow_efficiency=0.6, delivery=0.9, throughput=0.10)
    high_output = _metrics(lead_median=20.0, flow_efficiency=0.6, delivery=0.9, throughput=0.99)
    assert compute_score(low_output, IDEAL_LEAD_TIME, WEIGHTS) == compute_score(
        high_output, IDEAL_LEAD_TIME, WEIGHTS
    )


def test_better_flow_scores_higher() -> None:
    good = _metrics(lead_median=18.0, flow_efficiency=0.8, delivery=1.0, throughput=0.16)
    bad = _metrics(lead_median=120.0, flow_efficiency=0.12, delivery=0.3, throughput=0.16)
    assert (
        compute_score(good, IDEAL_LEAD_TIME, WEIGHTS).composite
        > compute_score(bad, IDEAL_LEAD_TIME, WEIGHTS).composite
    )


def test_lead_time_score_is_capped_at_one() -> None:
    # Median below the theoretical floor cannot yield a sub-score above 1.
    score = compute_score(
        _metrics(lead_median=5.0, flow_efficiency=0.9, delivery=1.0, throughput=0.2),
        IDEAL_LEAD_TIME,
        WEIGHTS,
    )
    assert score.lead_time_score == 1.0
