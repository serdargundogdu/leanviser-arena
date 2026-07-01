import type { LeverDescriptor } from "../types";

// Turkish labels/hints for the language-neutral lever keys from the API.
const LABELS: Record<string, { label: string; hint: string }> = {
  batch_size: {
    label: "Parti Büyüklüğü",
    hint: "Transfer partisi — küçük değer tek-parça akışa yaklaşır.",
  },
  release_interval: {
    label: "Salım Aralığı",
    hint: "0 = flood (aşırı üretim); artırınca salım dengelenir.",
  },
};

interface Props {
  levers: LeverDescriptor[];
  values: Record<string, number>;
  onChange: (key: string, value: number) => void;
  disabled?: boolean;
}

export function LeverControls({ levers, values, onChange, disabled }: Props) {
  return (
    <div className="levers">
      {levers.map((lever) => {
        const meta = LABELS[lever.key] ?? { label: lever.key, hint: "" };
        return (
          <label key={lever.key} className="lever">
            <div className="lever__head">
              <span className="lever__label">{meta.label}</span>
              <span className="lever__value">{values[lever.key]}</span>
            </div>
            <input
              type="range"
              min={lever.minimum}
              max={lever.maximum}
              step={lever.step}
              value={values[lever.key]}
              disabled={disabled}
              onChange={(event) => onChange(lever.key, Number(event.target.value))}
            />
            <span className="lever__hint">{meta.hint}</span>
          </label>
        );
      })}
    </div>
  );
}
