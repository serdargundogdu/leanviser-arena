"""Kaizen credit invariants: improvement costs, staying put is free, and the
budget is enforced server-side at the game boundary (use case + API).
"""

import pytest
from fastapi.testclient import TestClient

from app.application.run_scenario import RunScenarioCommand, run_scenario
from app.domain.scenario.scenario import KaizenBudgetExceededError, baseline_scenario
from app.main import app

client = TestClient(app)


def test_default_levers_are_free() -> None:
    # An empty mapping means "touch nothing" — every lever at its default.
    assert baseline_scenario().credit_cost({}) == 0.0


def test_full_fix_costs_exactly_the_budget() -> None:
    scenario = baseline_scenario()
    # batch 5→1 = 4, release 0→6 = 12, variance 1.0→0.25 = 6 → 22 credits.
    two_lever = {"batch_size": 1, "release_interval": 6.0}
    assert scenario.credit_cost(two_lever) == pytest.approx(16.0)
    assert scenario.credit_cost({**two_lever, "variance_factor": 0.25}) == pytest.approx(22.0)
    assert scenario.kaizen_budget == pytest.approx(22.0)


def test_cost_is_priced_on_applied_values() -> None:
    scenario = baseline_scenario()
    # 1000 clamps to the lever maximum (20) → 15 steps, not 995.
    assert scenario.credit_cost({"batch_size": 1000}) == pytest.approx(15.0)
    # 3.6 rounds to a whole batch of 4 → 1 step.
    assert scenario.credit_cost({"batch_size": 3.6}) == pytest.approx(1.0)


def test_run_scenario_rejects_over_budget() -> None:
    # Over-pacing (release 12) costs 24 + 4 = 28 credits — priced out.
    with pytest.raises(KaizenBudgetExceededError) as excinfo:
        run_scenario(
            RunScenarioCommand(
                scenario=baseline_scenario(),
                lever_values={"batch_size": 1, "release_interval": 12.0},
            )
        )
    assert excinfo.value.cost == pytest.approx(28.0)
    assert excinfo.value.budget == pytest.approx(22.0)


def test_run_scenario_reports_spent_credits() -> None:
    result = run_scenario(
        RunScenarioCommand(
            scenario=baseline_scenario(),
            lever_values={"batch_size": 1, "release_interval": 6.0},
        )
    )
    assert result.credit_cost == pytest.approx(16.0)


def test_api_rejects_over_budget_with_422() -> None:
    response = client.post(
        "/api/simulate",
        json={"levers": {"batch_size": 1, "release_interval": 12.0}},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "budget_exceeded"
    assert detail["cost"] == pytest.approx(28.0)
    assert detail["budget"] == pytest.approx(22.0)


def test_api_exposes_budget_and_costs() -> None:
    descriptor = next(
        entry for entry in client.get("/api/scenarios").json() if entry["scenario_id"] == "baseline"
    )
    assert descriptor["kaizen_budget"] == pytest.approx(22.0)
    assert all(lever["cost_per_step"] > 0 for lever in descriptor["levers"])

    body = client.post(
        "/api/simulate",
        json={"levers": {"batch_size": 1, "release_interval": 6.0, "variance_factor": 0.25}},
    ).json()
    assert body["credit_cost"] == pytest.approx(22.0)
    assert body["applied_levers"]["variance_factor"] == pytest.approx(0.25)
