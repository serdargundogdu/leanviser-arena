import type { ScoreDto } from "../types";

const PILLARS = [
  { key: "lead_time_score", label: "Temin Süresi" },
  { key: "flow_efficiency_score", label: "Akış Verimliliği" },
  { key: "delivery_score", label: "Teslim Güvenilirliği" },
] as const;

interface Props {
  score: ScoreDto;
}

export function ScoreCard({ score }: Props) {
  return (
    <div className="score">
      <div className="score__composite">
        <span className="score__value">{Math.round(score.composite)}</span>
        <span className="score__max">/ 100</span>
      </div>
      <p className="score__caption">Arena Skoru</p>
      <div className="score__pillars">
        {PILLARS.map((pillar) => {
          const value = score[pillar.key];
          return (
            <div key={pillar.key} className="pillar">
              <div className="pillar__head">
                <span>{pillar.label}</span>
                <span>{Math.round(value * 100)}</span>
              </div>
              <div className="pillar__bar">
                <div className="pillar__fill" style={{ width: `${value * 100}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
