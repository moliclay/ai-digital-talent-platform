import { copy } from "../../content/copy";
import { formatScore } from "../../lib/format";
import styles from "./score-bar.module.css";

type ScoreBarProps = {
  value: number | null;
  threshold?: number | null;
  label?: string;
  ariaLabel?: string;
  unit?: string;
  size?: "md" | "sm";
};

export function ScoreBar({ value, threshold, label, ariaLabel, unit = "分", size = "md" }: ScoreBarProps) {
  const safeValue = value === null ? 0 : Math.min(Math.max(value, 0), 100);
  const safeThreshold =
    threshold === null || threshold === undefined ? null : Math.min(Math.max(threshold, 0), 100);

  return (
    <div className={size === "sm" ? styles.small : styles.root}>
      {label ? <p className={styles.label}>{label}</p> : null}
      <div className={styles.head}>
        <span className={styles.value}>{value === null ? copy.common.empty : formatScore(value)}</span>
        {value === null ? null : <span className={styles.unit}>{unit}</span>}
      </div>
      <div
        className={styles.track}
        role="progressbar"
        aria-label={ariaLabel ?? label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={safeValue}
        aria-valuetext={`${formatScore(value)} ${unit}`}
      >
        <div className={styles.fill} style={{ width: `${safeValue}%` }} />
        {safeThreshold !== null ? (
          <span
            className={styles.tick}
            style={{ left: `${safeThreshold}%` }}
            title={copy.score.threshold(safeThreshold)}
            aria-hidden="true"
          />
        ) : null}
        {safeThreshold !== null && size === "md" ? (
          <span
            className={styles.tickLabel}
            style={{
              left: `${safeThreshold}%`,
              transform: safeThreshold > 75 ? "translateX(-100%)" : "translateX(-50%)",
            }}
            aria-hidden="true"
          >
            {copy.score.threshold(safeThreshold)}
          </span>
        ) : null}
      </div>
    </div>
  );
}
