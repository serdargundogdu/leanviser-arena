import type { MetricsDto } from "../types";

interface Props {
  valueAddedMean: number;
  waitingMean: number;
  leadTimes: number[];
  deliveryWindow: number;
  metrics: MetricsDto;
}

// Hero flow-time debrief: makes waiting visible (value-adding vs waiting share
// of lead time) and shows each order's lead time against the delivery window.
export function FlowTimeDebrief({
  valueAddedMean,
  waitingMean,
  leadTimes,
  deliveryWindow,
  metrics,
}: Props) {
  const total = valueAddedMean + waitingMean;
  const valueAddedPct = total > 0 ? (valueAddedMean / total) * 100 : 0;
  const waitingPct = 100 - valueAddedPct;
  const maxLead = Math.max(...leadTimes, deliveryWindow);
  const windowY = 100 - (deliveryWindow / maxLead) * 100;

  return (
    <div className="debrief">
      <h3 className="debrief__title">Akış Zamanı Röntgeni</h3>
      <p className="debrief__sub">
        Ortalama temin süresinin ne kadarı gerçekten değer üretiyor?
      </p>

      <div className="flowbar">
        <div className="flowbar__va" style={{ width: `${valueAddedPct}%` }}>
          <span>Değer {valueAddedMean.toFixed(1)}</span>
        </div>
        <div className="flowbar__wait" style={{ width: `${waitingPct}%` }}>
          <span>Bekleme {waitingMean.toFixed(1)}</span>
        </div>
      </div>
      <p className="debrief__fe">
        Akış verimliliği <strong>%{Math.round(valueAddedPct)}</strong> — kalan
        %{Math.round(waitingPct)} beklemede geçiyor (israf).
      </p>

      <h4 className="debrief__striptitle">Sipariş bazında temin süresi</h4>
      <svg
        className="strip"
        viewBox={`0 0 ${leadTimes.length} 100`}
        preserveAspectRatio="none"
        role="img"
        aria-label="Sipariş temin süreleri ve teslim penceresi"
      >
        {leadTimes.map((leadTime, index) => {
          const height = (leadTime / maxLead) * 100;
          const onTime = leadTime <= deliveryWindow;
          return (
            <rect
              key={index}
              x={index}
              y={100 - height}
              width={0.88}
              height={height}
              className={onTime ? "strip__ok" : "strip__late"}
            />
          );
        })}
        <line
          x1={0}
          x2={leadTimes.length}
          y1={windowY}
          y2={windowY}
          className="strip__window"
        />
      </svg>

      <div className="strip__legend">
        <span>
          <i className="dot dot--ok" /> pencerede (%
          {Math.round(metrics.delivery_reliability * 100)})
        </span>
        <span>
          <i className="dot dot--late" /> geç
        </span>
        <span>
          <i className="dash" /> hedef {deliveryWindow}
        </span>
      </div>

      <div className="debrief__note">
        Çıktı hızı (throughput): {metrics.throughput.toFixed(3)} ·
        ortalama WIP: {metrics.average_wip.toFixed(1)} —{" "}
        <em>çıktı skoru artırmaz</em>.
      </div>
    </div>
  );
}
