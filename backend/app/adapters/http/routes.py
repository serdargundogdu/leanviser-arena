"""HTTP routes for scenario discovery and running a simulation.

Both endpoints are stateless and server-authoritative: the scenario (seed
included) lives on the server; the client only supplies lever values.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from app.adapters.http.schemas import (
    InsightDto,
    LeverDescriptor,
    MetricsDto,
    ScenarioDescriptor,
    ScoreDto,
    SimulateRequest,
    SimulateResponse,
)
from app.application.run_scenario import RunScenarioCommand, run_scenario
from app.domain.scenario.scenario import (
    KaizenBudgetExceededError,
    Scenario,
    UnknownScenarioError,
    get_scenario,
    scenarios,
)

router = APIRouter(prefix="/api", tags=["arena"])


def _descriptor(scenario: Scenario) -> ScenarioDescriptor:
    return ScenarioDescriptor(
        scenario_id=scenario.scenario_id,
        order_count=scenario.order_count,
        delivery_window=scenario.delivery_window,
        takt_time=scenario.takt_time,
        ideal_lead_time=scenario.ideal_lead_time,
        kaizen_budget=scenario.kaizen_budget,
        levers=[
            LeverDescriptor(
                key=lever.key,
                minimum=lever.minimum,
                maximum=lever.maximum,
                step=lever.step,
                default=lever.default,
                cost_per_step=lever.cost_per_step,
            )
            for lever in scenario.levers()
        ],
    )


@router.get("/scenarios", response_model=list[ScenarioDescriptor])
def list_scenarios() -> list[ScenarioDescriptor]:
    """All playable scenarios with their tunable levers (for the UI)."""
    return [_descriptor(scenario) for scenario in scenarios()]


@router.post("/simulate", response_model=SimulateResponse)
def post_simulate(request: SimulateRequest) -> SimulateResponse:
    """Run the deterministic simulation for the player's lever values.

    Rejects with 404 for an unknown scenario id and 422 when the requested
    lever moves exceed the scenario's kaizen budget (the UI prevents both; the
    server stays authoritative).
    """
    try:
        scenario = get_scenario(request.scenario_id)
    except UnknownScenarioError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "unknown_scenario", "scenario_id": error.scenario_id},
        ) from error
    try:
        result = run_scenario(RunScenarioCommand(scenario=scenario, lever_values=request.levers))
    except KaizenBudgetExceededError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "budget_exceeded",
                "cost": error.cost,
                "budget": error.budget,
            },
        ) from error
    return SimulateResponse(
        score=ScoreDto(**asdict(result.score)),
        metrics=MetricsDto(**asdict(result.metrics)),
        insights=[
            InsightDto(code=insight.code.value, severity=insight.severity.value)
            for insight in result.insights
        ],
        lead_times=list(result.lead_times),
        on_time=list(result.on_time),
        release_times=list(result.release_times),
        completion_times=list(result.completion_times),
        value_added_mean=result.value_added_mean,
        waiting_mean=result.waiting_mean,
        applied_levers=result.applied_levers,
        credit_cost=result.credit_cost,
    )
