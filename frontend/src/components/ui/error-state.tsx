import type { ReactNode } from "react";
import { CircleAlert } from "lucide-react";

import { Button } from "./button";
import styles from "./error-state.module.css";

type ErrorStateProps = {
  title: string;
  detail?: ReactNode;
  retryLabel?: string;
  onRetry?: () => void;
};

export function ErrorState({ title, detail, retryLabel = "重试", onRetry }: ErrorStateProps) {
  return (
    <div className={styles.root} role="alert">
      <CircleAlert className={styles.icon} size={18} strokeWidth={1.75} aria-hidden="true" />
      <div className={styles.text}>
        <p className={styles.title}>{title}</p>
        {detail ? <p className={styles.detail}>{detail}</p> : null}
      </div>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}
