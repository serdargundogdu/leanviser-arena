"""Coaching rules: guidance is actionable and matches the run's failure mode.

Runs at DOMAIN level (engine → metrics → score → diagnose) so rules can be
probed on configs the kaizen budget prices out of play (e.g. over-pacing).
"""

from app.domain.coaching.coach import Insight, InsightCode, Severity, diagnose
from app.domain.scenario.scenario import baseline_scenario
from app.domain.scoring.score import Score, compute_score
from app.domain.simulation.engine import simulate
from app.domain.simulation.metrics import SimulationMetrics, compute_metrics


def _codes(
    batch_size: float, release_interval: float, variance_factor: float = 1.0
) -> set[InsightCode]:
    scenario = baseline_scenario()
    lever_values = {
        "batch_size": batch_size,
        "release_interval": release_interval,
        "variance_factor": variance_factor,
    }
    config = scenario.build_config(lever_values)
    applied = scenario.applied_values(lever_values)
    log = simulate(config)
    metrics = compute_metrics(log, config.takt_time, config.delivery_window)
    score = compute_score(metrics, scenario.ideal_lead_time, scenario.weights)
    insights = diagnose(
        metrics=metrics,
        score=score,
        batch_size=config.batch_size,
        release_interval=config.release_interval,
        takt_time=config.takt_time,
        variance_factor=applied["variance_factor"],
    )
    return {insight.code for insight in insights}


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


def test_variability_hint_fires_when_flow_is_sane_but_unsteady() -> None:
    # Takt-paced one-piece flow with untouched variance: the remaining waste is
    # cycle-time noise — the coach should point at standard work.
    takt = baseline_scenario().takt_time
    codes = _codes(batch_size=1, release_interval=takt, variance_factor=1.0)
    assert InsightCode.HIGH_VARIABILITY in codes


def test_variability_hint_silent_after_standard_work_investment() -> None:
    takt = baseline_scenario().takt_time
    codes = _codes(batch_size=1, release_interval=takt, variance_factor=0.25)
    assert InsightCode.HIGH_VARIABILITY not in codes


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
        metrics=metrics,
        score=score,
        batch_size=1,
        release_interval=6.0,
        takt_time=6.0,
        # Standard work already invested, so the variability rule stays silent.
        variance_factor=0.25,
    )
    assert insights == [Insight(InsightCode.KEEP_TUNING, Severity.WARNING)]
