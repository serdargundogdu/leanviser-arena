"""Coaching rules: guidance is actionable and matches the run's failure mode."""

from app.application.run_scenario import RunScenarioCommand, run_scenario
from app.domain.coaching.coach import Insight, InsightCode, Severity, diagnose
from app.domain.scenario.scenario import baseline_scenario
from app.domain.scoring.score import Score
from app.domain.simulation.metrics import SimulationMetrics


def _codes(batch_size: float, release_interval: float) -> set[InsightCode]:
    result = run_scenario(
        RunScenarioCommand(
            scenario=baseline_scenario(),
            batch_size=batch_size,
            release_interval=release_interval,
        )
    )
    return {insight.code for insight in result.insights}


def test_balanced_flow_is_praised_not_scolded() -> None:
    takt = baseline_scenario().takt_time
    codes = _codes(batch_size=1, release_interval=takt)
    assert InsightCode.BALANCED_FLOW in codes
    assert InsightCode.OVERPACED not in codes
    assert InsightCode.MISSED_DEMAND not in codes


def test_overpacing_is_flagged() -> None:
    takt = baseline_scenario().takt_time
    codes = _codes(batch_size=1, release_interval=takt * 2)
    assert InsightCode.OVERPACED in codes


def test_flooding_with_large_batch_is_flagged() -> None:
    codes = _codes(batch_size=5, release_interval=0.0)
    assert InsightCode.FLOODING in codes
    assert InsightCode.LARGE_BATCH in codes


def test_diagnose_never_returns_empty() -> None:
    # A middling run that trips no specific rule still gets a nudge to keep going.
    metrics = SimulationMetrics(
        lead_time_median=25.0,
        lead_time_mean=25.0,
        average_wip=4.0,
        flow_efficiency=0.7,
        throughput=0.15,
        delivery_reliability=0.95,
        order_count=60,
        makespan=400.0,
    )
    score = Score(
        composite=55.0,
        lead_time_score=0.6,
        flow_efficiency_score=0.7,
        delivery_score=0.95,
    )
    insights = diagnose(
        metrics=metrics, score=score, batch_size=1, release_interval=6.0, takt_time=6.0
    )
    assert insights == [Insight(InsightCode.KEEP_TUNING, Severity.WARNING)]
