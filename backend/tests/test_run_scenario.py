"""RunScenario use case: deterministic, thesis-aligned, and lever-clamping."""

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


def test_deterministic_for_same_levers() -> None:
    assert _run(1, 6.0) == _run(1, 6.0)


def test_result_shape() -> None:
    result = _run(1, 6.0)
    assert len(result.lead_times) == baseline_scenario().order_count
    assert result.waiting_mean >= 0.0
    assert 0.0 <= result.score.composite <= 100.0


def test_lean_flow_beats_push_batching() -> None:
    # One-piece flow + levelled release should beat large-batch flooding.
    lean = _run(batch_size=1, release_interval=6.0)
    push = _run(batch_size=5, release_interval=0.0)
    assert lean.score.composite > push.score.composite


def test_applied_lever_values_are_clamped() -> None:
    scenario = baseline_scenario()
    result = _run(batch_size=1000, release_interval=999.0)
    assert result.applied_batch_size == int(scenario.batch_size_lever.maximum)
    assert result.applied_release_interval == scenario.release_interval_lever.maximum


def test_arrival_and_departure_times_for_cfd() -> None:
    n = baseline_scenario().order_count
    result = _run(batch_size=1, release_interval=6.0)
    assert len(result.release_times) == n
    assert len(result.completion_times) == n
    # Each order completes no earlier than it was released.
    assert all(
        completion >= release
        for release, completion in zip(result.release_times, result.completion_times, strict=True)
    )
