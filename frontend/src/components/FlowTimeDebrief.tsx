import type { MetricsDto } from "../types";

interface Props {
  valueAddedMean: number;
  waitingMean: number;
  leadTimes: number[];
  onTime: boolean[];
  taktTime: number;
  metrics: MetricsDto;
}

// Hero flow-time debrief: makes waiting visible (value-adding vs waiting share
// of lead time) and shows each order's lead time colored by whether it met the
// takt-paced demand schedule. Short-but-late bars are the tell-tale of starving
// the line: fast per order, yet unable to keep up with demand.
export function FlowTimeDebrief({
  valueAddedMean,
  waitingMean,
  leadTimes,
  onTime,
  taktTime,
  metrics,
}: Props) {
  const total = valueAddedMean + waitingMean;
  const valueAddedPct = total > 0 ? (valueAddedMean / total) * 100 : 0;
  const waitingPct = 100 - valueAddedPct;
  const maxLead = Math.max(...leadTimes, 1);
  const deliveryPct = Math.round(metrics.delivery_reliability * 100);

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
        Akış verimliliği <strong>%{Math.round(valueAddedPct)}</strong> — kalan %
        {Math.round(waitingPct)} beklemede geçiyor (israf).
      </p>

      <h4 className="debrief__striptitle">
        Sipariş bazında temin süresi · talep temposu (takt) {taktTime}
      </h4>
      <svg
        className="strip"
        viewBox={`0 0 ${leadTimes.length} 100`}
        preserveAspectRatio="none"
        role="img"
        aria-label="Sipariş temin süreleri; renk talebe yetişme durumunu gösterir"
      >
        {leadTimes.map((leadTime, index) => {
          const height = (leadTime / maxLead) * 100;
          return (
            <rect
              key={index}
              x={index}
              y={100 - height}
              width={0.88}
              height={height}
              className={onTime[index] ? "strip__ok" : "strip__late"}
            />
          );
        })}
      </svg>

      <div className="strip__legend">
        <span>
          <i className="dot dot--ok" /> talebe yetişti (%{deliveryPct})
        </span>
        <span>
          <i className="dot dot--late" /> geç kaldı
        </span>
      </div>

      <div className="debrief__note">
        Çıktı hızı (throughput): {metrics.throughput.toFixed(3)} · ortalama WIP:{" "}
        {metrics.average_wip.toFixed(1)} — <em>çıktı skoru artırmaz</em>. Skor,
        akış kalitesinin talebe teslim edildiği oranla çarpımıdır.
      </div>
    </div>
  );
}
