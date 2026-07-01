// HTTP client for the Arena API. Same-origin in dev via the Vite proxy.

import type { ScenarioDescriptor, SimulateRequest, SimulateResponse } from "./types";

export async function fetchScenario(): Promise<ScenarioDescriptor> {
  const response = await fetch("/api/scenario");
  if (!response.ok) {
    throw new Error(`Senaryo alınamadı (HTTP ${response.status})`);
  }
  return response.json();
}

export async function runSimulation(
  request: SimulateRequest,
): Promise<SimulateResponse> {
  const response = await fetch("/api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Simülasyon başarısız (HTTP ${response.status})`);
  }
  return response.json();
}
