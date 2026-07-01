import type { Insight } from "../types";

// Turkish copy for the language-neutral insight codes from the backend.
const COPY: Record<string, { title: string; tip: string }> = {
  overpaced: {
    title: "Hattı starve ediyorsun",
    tip: "Salım takt'tan yavaş — talebe yetişemiyorsun. Salım aralığını takt'a indir.",
  },
  flooding: {
    title: "Aşırı salım (overproduction)",
    tip: "İşi talepten hızlı salıyorsun; WIP şişiyor. Salımı takt'a çek.",
  },
  large_batch: {
    title: "Parti çok büyük",
    tip: "Erken biten parçalar batch arkadaşlarını bekliyor. Partiyi küçült (ideal: 1).",
  },
  missed_demand: {
    title: "Talebe yetişemiyorsun",
    tip: "Siparişler takt programının gerisinde kalıyor.",
  },
  balanced_flow: {
    title: "Dengeli akış",
    tip: "Takt'a yakın salım ve küçük parti — yalın akışın özü bu.",
  },
  keep_tuning: {
    title: "Ayarlamaya devam",
    tip: "Kaldıraçlarla oyna: partiyi küçült, salımı takt'a yaklaştır.",
  },
};

interface Props {
  insights: Insight[];
}

export function CoachingPanel({ insights }: Props) {
  return (
    <div className="coaching">
      <h3 className="coaching__title">FATİH USTA diyor ki</h3>
      <ul className="coaching__list">
        {insights.map((insight, index) => {
          const copy = COPY[insight.code] ?? { title: insight.code, tip: "" };
          return (
            <li key={index} className={`coach coach--${insight.severity}`}>
              <strong className="coach__title">{copy.title}</strong>
              <span className="coach__tip">{copy.tip}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
