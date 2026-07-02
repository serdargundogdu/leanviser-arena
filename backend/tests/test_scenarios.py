"""Scenario registry + the unstable-line thesis: diagnose before you prescribe.

The unstable line is structurally lean (one-piece at takt) but CV≈1 noisy —
its queues are variability-driven, so ONLY standard work pays. Misallocating
the budget on structure is worse than doing nothing.
"""

import pytest
from fastapi.testclient import TestClient

from app.application.run_scenario import RunScenarioCommand, run_scenario
from app.domain.scenario.scenario import (
    UnknownScenarioError,
    get_scenario,
    scenarios,
    unstable_line_scenario,
)
from app.main import app

client = TestClient(app)


def _run(scenario_id: str, batch_size: float, release_interval: float, vf: float):
    return run_scenario(
        RunScenarioCommand(
            scenario=get_scenario(scenario_id),
            lever_values={
                "batch_size": batch_size,
                "release_interval": release_interval,
                "variance_factor": vf,
            },
        )
    )


def test_registry_lists_unique_playable_scenarios() -> None:
    ids = [scenario.scenario_id for scenario in scenarios()]
    assert ids == ["baseline", "unstable_line"]
    assert len(set(ids)) == len(ids)


def test_get_scenario_unknown_id_raises() -> None:
    with pytest.raises(UnknownScenarioError):
        get_scenario("no_such_line")


def test_unstable_full_fix_is_exactly_the_budget() -> None:
    scenario = unstable_line_scenario()
    assert scenario.credit_cost({}) == 0.0
    # Standard work 1.0→0.25 is the whole fix: 6 credits = the whole budget.
    assert scenario.credit_cost({"variance_factor": 0.25}) == pytest.approx(6.0)
    assert scenario.kaizen_budget == pytest.approx(6.0)


def test_unstable_standard_work_is_the_only_fix_that_pays() -> None:
    takt = unstable_line_scenario().takt_time
    defaults = _run("unstable_line", 1, takt, 1.0)
    standardized = _run("unstable_line", 1, takt, 0.25)
    batch_fiddling = _run("unstable_line", 2, takt, 0.5)  # 5 credits misspent
    speeding_up = _run("unstable_line", 1, takt - 1.0, 0.5)  # 6 credits misspent

    # Standard work transforms the line ...
    assert standardized.score.composite > defaults.score.composite + 20
    # ... while structural fiddling is WORSE than doing nothing.
    assert batch_fiddling.score.composite < defaults.score.composite
    assert speeding_up.score.composite < defaults.score.composite


def test_api_lists_both_scenarios() -> None:
    body = client.get("/api/scenarios").json()
    assert [entry["scenario_id"] for entry in body] == ["baseline", "unstable_line"]


def test_api_simulate_accepts_scenario_id() -> None:
    response = client.post(
        "/api/simulate",
        json={"scenario_id": "unstable_line", "levers": {"variance_factor": 0.25}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["credit_cost"] == pytest.approx(6.0)
    assert body["score"]["composite"] > 70.0


def test_api_unknown_scenario_returns_404() -> None:
    response = client.post(
        "/api/simulate",
        json={"scenario_id": "no_such_line", "levers": {}},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "unknown_scenario"
