import { cx } from "../../lib/cx";
import styles from "./skeleton.module.css";

type SkeletonProps = {
  width?: "full" | "wide" | "half" | "short";
  height?: "line" | "title";
  className?: string;
};

export function Skeleton({ width = "full", height = "line", className }: SkeletonProps) {
  return <span className={cx(styles.base, styles[width], styles[height], className)} aria-hidden="true" />;
}
