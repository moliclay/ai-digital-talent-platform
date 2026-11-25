import { copy } from "../content/copy";
import type { Audience } from "../lib/api-types";
import styles from "./audience-filter.module.css";

export type AudienceValue = Audience | "all";

type AudienceFilterProps = {
  value: AudienceValue;
  onChange: (value: AudienceValue) => void;
  label?: string;
};

const OPTIONS: Array<{ value: AudienceValue; label: string }> = [
  { value: "all", label: copy.common.audience.all },
  { value: "candidate", label: copy.common.audience.candidate },
  { value: "employee", label: copy.common.audience.employee },
];

export function AudienceFilter({ value, onChange, label = copy.common.audienceLabel }: AudienceFilterProps) {
  return (
    <div className={`${styles.group} glass-segmented`} role="group" aria-label={label}>
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          className={
            value === option.value
              ? `${styles.option} glass-segmented-option glass-segmented-active`
              : `${styles.option} glass-segmented-option`
          }
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
