import type { ReactNode } from "react";

import { cx } from "../../lib/cx";
import styles from "./badge.module.css";

type BadgeTone = "neutral" | "success" | "error" | "warning" | "info";

type BadgeProps = {
  tone?: BadgeTone;
  children: ReactNode;
};

export function Badge({ tone = "neutral", children }: BadgeProps) {
  return <span className={cx(styles.badge, styles[tone])}>{children}</span>;
}
