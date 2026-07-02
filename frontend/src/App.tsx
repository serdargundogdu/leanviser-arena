import { useCallback, useEffect, useState } from "react";

import { fetchScenario, runSimulation } from "./api";
import { CoachingPanel } from "./components/CoachingPanel";
import { CumulativeFlowDiagram } from "./components/CumulativeFlowDiagram";
import { FlowTimeDebrief } from "./components/FlowTimeDebrief";
import { LeverControls } from "./components/LeverControls";
import { ScoreCard } from "./components/ScoreCard";
import type { ScenarioDescriptor, SimulateResponse } from "./types";

export function App() {
  const [scenario, setScenario] = useState<ScenarioDescriptor | null>(null);
  const [values, setValues] = useState<Record<string, number>>({});
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (levers: Record<string, number>) => {
    setBusy(true);
    setError(null);
    try {
      setResult(
        await runSimulation({
          batch_size: levers.batch_size,
          release_interval: levers.release_interval,
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    fetchScenario()
      .then((descriptor) => {
        if (!alive) return;
        const defaults: Record<string, number> = {};
        descriptor.levers.forEach((lever) => {
          defaults[lever.key] = lever.default;
        });
        setScenario(descriptor);
        setValues(defaults);
        void run(defaults);
      })
      .catch((caught) => {
        if (alive) setError(caught instanceof Error ? caught.message : String(caught));
      });
    return () => {
      alive = false;
    };
  }, [run]);

  const onChange = (key: string, value: number) =>
    setValues((previous) => ({ ...previous, [key]: value }));

  // Live kaizen cost of the current lever positions (mirrors the server's
  // pricing; the server remains the authority and rejects over-budget runs).
  const creditCost = scenario
    ? scenario.levers.reduce((total, lever) => {
        const value = values[lever.key] ?? lever.default;
        return total + (Math.abs(value - lever.default) / lever.step) * lever.cost_per_step;
      }, 0)
    : 0;
  const overBudget = scenario !== null && creditCost > scenario.kaizen_budget;

  return (
    <main className="app">
      <header className="app__header">
        <p className="app__eyebrow">LEANVİSER</p>
        <h1 className="app__title">ARENA</h1>
        <p className="app__tagline">Yalın üretim simülasyon arenası — sürüm 0.6</p>
      </header>

      {error && (
        <div className="app__error">
          Hata: {error}. Backend çalışıyor mu?{" "}
          <code>uv run uvicorn app.main:app --port 8000</code>
        </div>
      )}

      {scenario && (
        <section className="app__grid">
          <div className="panel">
            <h2 className="panel__title">Kaldıraçlar</h2>
            <p className="panel__hint">
              Talep temposu (takt) {scenario.takt_time} · hedef temin ≤{" "}
              {scenario.delivery_window} · ideal {scenario.ideal_lead_time} ·{" "}
              {scenario.order_count} sipariş
            </p>
            <LeverControls
              levers={scenario.levers}
              values={values}
              onChange={onChange}
              disabled={busy}
            />
            <div className="budget">
              <div className="budget__head">
                <span>Kaizen bütçesi</span>
                <span className={overBudget ? "budget__value budget__value--over" : "budget__value"}>
                  {creditCost} / {scenario.kaizen_budget} kredi
                </span>
              </div>
              <div className="budget__bar">
                <div
                  className={overBudget ? "budget__fill budget__fill--over" : "budget__fill"}
                  style={{
                    width: `${Math.min(100, (creditCost / scenario.kaizen_budget) * 100)}%`,
                  }}
                />
              </div>
              {overBudget && (
                <p className="budget__warn">
                  Bütçe aşıldı — iyileştirme bedava değil; kaldıraçları geri çek.
                </p>
              )}
            </div>
            <button className="btn" onClick={() => run(values)} disabled={busy || overBudget}>
              {busy ? "Simüle ediliyor…" : "Simüle Et"}
            </button>
          </div>

          <div className="panel panel--score">
            {result ? <ScoreCard score={result.score} /> : <p className="muted">Yükleniyor…</p>}
          </div>

          {result && (
            <div className="panel panel--wide">
              <CoachingPanel insights={result.insights} />
            </div>
          )}

          <div className="panel panel--wide">
            {result && (
              <>
                <FlowTimeDebrief
                  valueAddedMean={result.value_added_mean}
                  waitingMean={result.waiting_mean}
                  leadTimes={result.lead_times}
                  onTime={result.on_time}
                  taktTime={scenario.takt_time}
                  metrics={result.metrics}
                />
                <CumulativeFlowDiagram
                  releaseTimes={result.release_times}
                  completionTimes={result.completion_times}
                  makespan={result.metrics.makespan}
                  orderCount={result.metrics.order_count}
                />
              </>
            )}
          </div>
        </section>
      )}

      <footer className="app__footer">
        Ödül akışın kendisidir: temin süresi, akış verimliliği ve teslim
        güvenilirliği — çıktı miktarı değil.
      </footer>
    </main>
  );
}
