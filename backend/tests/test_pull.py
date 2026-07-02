"""Pull-challenge thesis: in a chaotic plant, backlog + WIP cap (CONWIP) beats
careful takt-paced push — cheaply. Standard work also works, but only on top
of pacing; and the cap tunes like a real system (too tight starves).
"""

import pytest

from app.application.run_scenario import RunScenarioCommand, run_scenario
from app.domain.scenario.scenario import (
    KaizenBudgetExceededError,
    pull_line_scenario,
)


def _run(levers: dict[str, float]):
    return run_scenario(RunScenarioCommand(scenario=pull_line_scenario(), lever_values=levers))


def test_lever_set_includes_the_wip_cap() -> None:
    keys = {lever.key for lever in pull_line_scenario().levers()}
    assert keys == {"batch_size", "release_interval", "variance_factor", "wip_cap"}


def test_rescheduling_is_free_and_cap_is_cheap() -> None:
    scenario = pull_line_scenario()
    # Moving the release schedule costs nothing; tightening the cap is cheap.
    assert scenario.credit_cost({"release_interval": 0.0}) == 0.0
    assert scenario.credit_cost({"wip_cap": 3}) == pytest.approx(4.5)


def test_pull_beats_careful_push_in_a_chaotic_plant() -> None:
    careful_push = _run({})  # defaults: takt-paced, no cap, full noise
    pull = _run({"release_interval": 0.0, "wip_cap": 3})  # backlog + cap
    assert pull.score.composite > careful_push.score.composite + 30
    assert pull.metrics.delivery_reliability > 0.95


def test_the_cap_tunes_like_a_real_system() -> None:
    # Too tight starves the bottleneck; too loose lets WIP pile up.
    starved = _run({"release_interval": 0.0, "wip_cap": 2})
    tuned = _run({"release_interval": 0.0, "wip_cap": 3})
    loose = _run({"release_interval": 0.0, "wip_cap": 5})
    assert tuned.score.composite > starved.score.composite
    assert tuned.score.composite > loose.score.composite


def test_standard_work_needs_pacing_to_pay() -> None:
    # Root-cause removal works at takt pacing, but cannot rescue an uncapped flood.
    standardized_paced = _run({"variance_factor": 0.25})
    standardized_flood = _run({"variance_factor": 0.25, "release_interval": 0.0})
    careful_push = _run({})
    assert standardized_paced.score.composite > 70.0
    assert standardized_flood.score.composite < careful_push.score.composite


def test_batch_fiddling_stays_punished() -> None:
    pull = _run({"release_interval": 0.0, "wip_cap": 3})
    batched_pull = _run({"release_interval": 0.0, "wip_cap": 3, "batch_size": 2})
    assert batched_pull.score.composite < pull.score.composite / 2


def test_everything_at_once_exceeds_the_budget() -> None:
    # Pull AND full standard work together cost 10.5 > 8 — pick a strategy.
    with pytest.raises(KaizenBudgetExceededError):
        _run({"release_interval": 0.0, "wip_cap": 3, "variance_factor": 0.25})
