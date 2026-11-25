import { formatCount } from "../../lib/format";
import { Skeleton } from "./skeleton";
import styles from "./kpi-strip.module.css";

export type KpiItem = {
  label: string;
  value: number;
  unit: string;
  note?: string;
};

type KpiStripProps = {
  items: KpiItem[];
  loading?: boolean;
  label?: string;
};

export function KpiStrip({ items, loading = false, label = "关键指标" }: KpiStripProps) {
  return (
    <dl className={`${styles.strip} glass-kpi`} aria-label={label} aria-busy={loading || undefined}>
      {items.map((item) => (
        <div className={styles.cell} key={item.label}>
          <dt className={styles.label}>{item.label}</dt>
          <dd className={styles.value}>
            {loading ? (
              <Skeleton width="half" />
            ) : (
              <>
                <span>{formatCount(item.value)}</span>
                <span className={styles.unit}>{item.unit}</span>
              </>
            )}
          </dd>
          {item.note ? <p className={styles.note}>{item.note}</p> : null}
        </div>
      ))}
    </dl>
  );
}
