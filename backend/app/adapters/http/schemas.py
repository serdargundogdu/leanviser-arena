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


class ScenarioDescriptor(BaseModel):
    scenario_id: str
    order_count: int
    delivery_window: float
    takt_time: float
    ideal_lead_time: float
    levers: list[LeverDescriptor]


class SimulateRequest(BaseModel):
    batch_size: float = Field(description="transfer batch size lever value")
    release_interval: float = Field(description="release interval lever value")


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


class SimulateResponse(BaseModel):
    score: ScoreDto
    metrics: MetricsDto
    lead_times: list[float]
    on_time: list[bool]
    value_added_mean: float
    waiting_mean: float
    applied_batch_size: int
    applied_release_interval: float
