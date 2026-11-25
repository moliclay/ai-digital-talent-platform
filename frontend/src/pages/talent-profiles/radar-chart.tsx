import styles from "./radar-chart.module.css";

export type RadarDatum = {
  label: string;
  value: number;
};

type RadarChartProps = {
  data: RadarDatum[];
  ariaLabel: string;
  compact?: boolean;
};

export function radarLabel(name: string, data: RadarDatum[]) {
  const scores = data.map((item) => `${item.label} ${Math.round(item.value)} 分`).join("，");
  return `${name}的能力雷达图：${scores}`;
}

const CENTER_X = 170;
const CENTER_Y = 150;
const RADIUS = 86;
const LABEL_RADIUS = 112;
const RINGS = [0.25, 0.5, 0.75, 1];

function clamp(value: number) {
  return Math.min(100, Math.max(0, value));
}

function pointAt(index: number, count: number, radius: number) {
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / count;
  return {
    x: CENTER_X + Math.cos(angle) * radius,
    y: CENTER_Y + Math.sin(angle) * radius,
  };
}

function polygonPoints(count: number, radius: number) {
  return Array.from({ length: count }, (_, index) => {
    const point = pointAt(index, count, radius);
    return `${point.x.toFixed(1)},${point.y.toFixed(1)}`;
  }).join(" ");
}

export function RadarChart({ data, ariaLabel, compact = false }: RadarChartProps) {
  const values = data.filter((item) => Number.isFinite(item.value));
  if (values.length < 3) return null;

  const count = values.length;
  const max = Math.max(...values.map((item) => item.value));
  const areaPoints = values
    .map((item, index) => {
      const point = pointAt(index, count, (RADIUS * clamp(item.value)) / 100);
      return `${point.x.toFixed(1)},${point.y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      className={compact ? `${styles.chart} ${styles.compact}` : styles.chart}
      viewBox="0 0 340 300"
      role="img"
      aria-label={ariaLabel}
    >
      <title>{ariaLabel}</title>

      <g className={styles.grid}>
        {RINGS.map((ratio) => (
          <polygon
            key={ratio}
            points={polygonPoints(count, RADIUS * ratio)}
            className={ratio === 1 ? styles.ringOuter : styles.ring}
          />
        ))}
      </g>

      <g className={styles.axes}>
        {values.map((item, index) => {
          const end = pointAt(index, count, RADIUS);
          return (
            <line
              key={item.label}
              x1={CENTER_X}
              y1={CENTER_Y}
              x2={end.x}
              y2={end.y}
              className={styles.axis}
            />
          );
        })}
      </g>

      <polygon points={areaPoints} className={styles.area} />

      <g>
        {values.map((item, index) => {
          const point = pointAt(index, count, (RADIUS * clamp(item.value)) / 100);
          const isPeak = item.value === max;
          return (
            <g key={item.label}>
              {isPeak ? (
                <circle
                  cx={point.x}
                  cy={point.y}
                  r={7}
                  className={styles.pointHalo}
                  aria-hidden="true"
                />
              ) : null}
              <circle
                cx={point.x}
                cy={point.y}
                r={isPeak ? 5 : 3}
                className={isPeak ? styles.pointPeak : styles.point}
              />
            </g>
          );
        })}
      </g>

      <g>
        {values.map((item, index) => {
          const angle = -Math.PI / 2 + (index * 2 * Math.PI) / count;
          const cos = Math.cos(angle);
          const x = CENTER_X + cos * LABEL_RADIUS;
          const y = CENTER_Y + Math.sin(angle) * LABEL_RADIUS;
          const anchor = cos > 0.25 ? "start" : cos < -0.25 ? "end" : "middle";
          const isPeak = item.value === max;
          return (
            <g key={item.label}>
              <text
                x={x}
                y={y - 3}
                textAnchor={anchor}
                className={isPeak ? styles.labelPeak : styles.label}
              >
                {item.label}
              </text>
              <text x={x} y={y + 12} textAnchor={anchor} className={styles.value}>
                {Math.round(item.value)}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
