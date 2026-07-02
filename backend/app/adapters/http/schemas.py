"""Pydantic transport DTOs for the HTTP API.

These mirror application results for the wire; they intentionally expose only
what the debrief UI needs and keep domain objects out of the transport layer.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LeverDescriptor(BaseModel):
    key: str
    minimum: float
    maximum: float
    step: float
    default: float
    cost_per_step: float


class ScenarioDescriptor(BaseModel):
    scenario_id: str
    order_count: int
    delivery_window: float
    takt_time: float
    ideal_lead_time: float
    kaizen_budget: float
    levers: list[LeverDescriptor]


class SimulateRequest(BaseModel):
    scenario_id: str = Field(default="baseline", description="which scenario to run")
    levers: dict[str, float] = Field(
        default_factory=dict,
        description="lever values keyed by lever key; missing keys use defaults",
    )


class ScoreDto(BaseModel):
    composite: float
    lead_time_score: float
    flow_efficiency_score: float
    delivery_score: float


class MetricsDto(BaseModel):
    lead_time_median: float
    lead_time_mean: float
    average_wip: float
    flow_efficiency: float
    throughput: float
    delivery_reliability: float
    order_count: int
    makespan: float


class InsightDto(BaseModel):
    code: str
    severity: str


class SimulateResponse(BaseModel):
    score: ScoreDto
    metrics: MetricsDto
    insights: list[InsightDto]
    lead_times: list[float]
    on_time: list[bool]
    release_times: list[float]
    completion_times: list[float]
    value_added_mean: float
    waiting_mean: float
    applied_levers: dict[str, float]
    credit_cost: float
