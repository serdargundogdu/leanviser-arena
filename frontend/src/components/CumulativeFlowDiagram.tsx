interface Props {
  releaseTimes: number[];
  completionTimes: number[];
  makespan: number;
  orderCount: number;
}

// The iconic lean flow chart. Two cumulative step curves — released (arrivals)
// and completed (departures) — over time. The vertical gap between them is WIP,
// the horizontal gap is lead time, and the enclosed area is total lead time.
// Flooding shows a fat band (WIP piled up); takt-paced flow shows a thin one.
function cumulative(times: number[], makespan: number, n: number): [number, number][] {
  const sorted = [...times].sort((a, b) => a - b);
  const points: [number, number][] = [[0, 0]];
  sorted.forEach((time, index) => points.push([time, index + 1]));
  points.push([makespan, n]);
  return points;
}

export function CumulativeFlowDiagram({
  releaseTimes,
  completionTimes,
  makespan,
  orderCount,
}: Props) {
  const width = 100;
  const height = 100;
  const maxTime = makespan > 0 ? makespan : 1;
  const toXY = ([time, count]: [number, number]): [number, number] => [
    (time / maxTime) * width,
    height - (count / orderCount) * height,
  ];
  const released = cumulative(releaseTimes, makespan, orderCount).map(toXY);
  const completed = cumulative(completionTimes, makespan, orderCount).map(toXY);
  const format = (points: [number, number][]) =>
    points.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
  const band = [...released, ...[...completed].reverse()];

  return (
    <div className="cfd-wrap">
      <h4 className="debrief__striptitle">
        Kümülatif akış (CFD) — salınan vs tamamlanan
      </h4>
      <svg
        className="cfd"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        role="img"
        aria-label="Kümülatif akış diyagramı: salınan ve tamamlanan siparişler"
      >
        <polygon className="cfd__band" points={format(band)} />
        <polyline className="cfd__released" points={format(released)} />
        <polyline className="cfd__completed" points={format(completed)} />
      </svg>
      <div className="strip__legend">
        <span>
          <i className="dot dot--released" /> salınan
        </span>
        <span>
          <i className="dot dot--completed" /> tamamlanan
        </span>
        <span>dikey mesafe = WIP · yatay = temin süresi</span>
      </div>
    </div>
  );
}
