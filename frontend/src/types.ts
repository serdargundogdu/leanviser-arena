// Transport types mirroring the backend HTTP DTOs (app/adapters/http/schemas.py).

export interface LeverDescriptor {
  key: string;
  minimum: number;
  maximum: number;
  step: number;
  default: number;
  cost_per_step: number;
}

export interface ScenarioDescriptor {
  scenario_id: string;
  order_count: number;
  delivery_window: number;
  takt_time: number;
  ideal_lead_time: number;
  kaizen_budget: number;
  levers: LeverDescriptor[];
}

export interface SimulateRequest {
  batch_size: number;
  release_interval: number;
  variance_factor: number;
}

export interface ScoreDto {
  composite: number;
  lead_time_score: number;
  flow_efficiency_score: number;
  delivery_score: number;
}

export interface MetricsDto {
  lead_time_median: number;
  lead_time_mean: number;
  average_wip: number;
  flow_efficiency: number;
  throughput: number;
  delivery_reliability: number;
  order_count: number;
  makespan: number;
}

export interface Insight {
  code: string;
  severity: "good" | "warning" | "critical";
}

export interface SimulateResponse {
  score: ScoreDto;
  metrics: MetricsDto;
  insights: Insight[];
  lead_times: number[];
  on_time: boolean[];
  release_times: number[];
  completion_times: number[];
  value_added_mean: number;
  waiting_mean: number;
  applied_batch_size: number;
  applied_release_interval: number;
  applied_variance_factor: number;
  credit_cost: number;
}
