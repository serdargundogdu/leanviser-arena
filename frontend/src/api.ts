// HTTP client for the Arena API. Same-origin in dev via the Vite proxy.

import type { ScenarioDescriptor, SimulateRequest, SimulateResponse } from "./types";

export async function fetchScenarios(): Promise<ScenarioDescriptor[]> {
  const response = await fetch("/api/scenarios");
  if (!response.ok) {
    throw new Error(`Senaryolar alınamadı (HTTP ${response.status})`);
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
    let message = `Simülasyon başarısız (HTTP ${response.status})`;
    try {
      const body = await response.json();
      if (body?.detail?.code === "budget_exceeded") {
        message = `Kaizen bütçesi aşıldı (${body.detail.cost} / ${body.detail.budget} kredi)`;
      }
    } catch {
      // yanıt gövdesi JSON değilse genel mesajla devam et
    }
    throw new Error(message);
  }
  return response.json();
}
