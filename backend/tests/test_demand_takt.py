"""Demand/takt invariants: starving the line can no longer win.

With a takt-paced demand schedule and a delivery-gated score, the only winning
strategy is matching demand with good flow — neither flooding (overproduction)
nor starving (over-pacing) scores well.
"""

from app.application.run_scenario import RunScenarioCommand, run_scenario
from app.domain.scenario.scenario import baseline_scenario


def _run(batch_size: float, release_interval: float):
    return run_scenario(
        RunScenarioCommand(
            scenario=baseline_scenario(),
            batch_size=batch_size,
            release_interval=release_interval,
        )
    )


def test_takt_matched_flow_beats_flood_and_overpacing() -> None:
    takt = baseline_scenario().takt_time
    lean = _run(batch_size=1, release_interval=takt)  # match demand, one-piece
    flood = _run(batch_size=5, release_interval=0.0)  # overproduction
    overpace = _run(batch_size=1, release_interval=takt * 2)  # starve the line
    assert lean.score.composite > flood.score.composite
    assert lean.score.composite > overpace.score.composite


def test_overpacing_no_longer_wins() -> None:
    takt = baseline_scenario().takt_time
    lean = _run(batch_size=1, release_interval=takt)
    overpace = _run(batch_size=1, release_interval=takt * 2)
    # Starving yields near-perfect flow (no queue) but misses demand, so the
    # delivery gate collapses the score — the old degenerate strategy is closed.
    assert overpace.metrics.flow_efficiency > 0.9
    assert overpace.score.composite < 20.0
    assert lean.score.composite > 3 * overpace.score.composite


def test_overpacing_misses_demand() -> None:
    takt = baseline_scenario().takt_time
    lean = _run(batch_size=1, release_interval=takt)
    overpace = _run(batch_size=1, release_interval=takt * 2)
    assert overpace.metrics.delivery_reliability < lean.metrics.delivery_reliability
    assert lean.metrics.delivery_reliability > 0.9
