import { useCallback, useEffect, useState } from "react";

import { fetchScenario, runSimulation } from "./api";
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

  return (
    <main className="app">
      <header className="app__header">
        <p className="app__eyebrow">LEANVİSER</p>
        <h1 className="app__title">ARENA</h1>
        <p className="app__tagline">Yalın üretim simülasyon arenası — sürüm 0.3</p>
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
            <button className="btn" onClick={() => run(values)} disabled={busy}>
              {busy ? "Simüle ediliyor…" : "Simüle Et"}
            </button>
          </div>

          <div className="panel panel--score">
            {result ? <ScoreCard score={result.score} /> : <p className="muted">Yükleniyor…</p>}
          </div>

          <div className="panel panel--wide">
            {result && (
              <FlowTimeDebrief
                valueAddedMean={result.value_added_mean}
                waitingMean={result.waiting_mean}
                leadTimes={result.lead_times}
                onTime={result.on_time}
                taktTime={scenario.takt_time}
                metrics={result.metrics}
              />
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
