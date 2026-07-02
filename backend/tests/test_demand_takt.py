"""Demand/takt invariants: starving the line can no longer win.

With a takt-paced demand schedule and a delivery-gated score, the only winning
strategy is matching demand with good flow — neither flooding (overproduction)
nor starving (over-pacing) scores well.

These are DOMAIN-level physics guards: they run the engine/score directly
(``build_config`` does not enforce the kaizen budget), because the guarded
configs — over-pacing costs 28 credits — are deliberately priced out of the
playable game. The budget closes them in play; these tests keep them closed in
the physics too.
"""

from app.domain.scenario.scenario import baseline_scenario
from app.domain.scoring.score import Score, compute_score
from app.domain.simulation.engine import simulate
from app.domain.simulation.metrics import SimulationMetrics, compute_metrics


def _run_domain(batch_size: float, release_interval: float) -> tuple[SimulationMetrics, Score]:
    scenario = baseline_scenario()
    config = scenario.build_config({"batch_size": batch_size, "release_interval": release_interval})
    log = simulate(config)
    metrics = compute_metrics(log, config.takt_time, config.delivery_window)
    score = compute_score(metrics, scenario.ideal_lead_time, scenario.weights)
    return metrics, score


def test_takt_matched_flow_beats_flood_and_overpacing() -> None:
    takt = baseline_scenario().takt_time
    _, lean = _run_domain(batch_size=1, release_interval=takt)
    _, flood = _run_domain(batch_size=5, release_interval=0.0)
    _, overpace = _run_domain(batch_size=1, release_interval=takt * 2)
    assert lean.composite > flood.composite
    assert lean.composite > overpace.composite


def test_overpacing_no_longer_wins() -> None:
    takt = baseline_scenario().takt_time
    _, lean = _run_domain(batch_size=1, release_interval=takt)
    overpace_metrics, overpace = _run_domain(batch_size=1, release_interval=takt * 2)
    # Starving yields near-perfect flow (no queue) but misses demand, so the
    # delivery gate collapses the score — the old degenerate strategy is closed.
    assert overpace_metrics.flow_efficiency > 0.9
    assert overpace.composite < 20.0
    assert lean.composite > 3 * overpace.composite


def test_overpacing_misses_demand() -> None:
    takt = baseline_scenario().takt_time
    lean_metrics, _ = _run_domain(batch_size=1, release_interval=takt)
    overpace_metrics, _ = _run_domain(batch_size=1, release_interval=takt * 2)
    assert overpace_metrics.delivery_reliability < lean_metrics.delivery_reliability
    assert lean_metrics.delivery_reliability > 0.9
