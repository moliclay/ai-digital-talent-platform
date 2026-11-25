import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

import styles from "./empty-state.module.css";

type EmptyStateProps = {
  title: string;
  hint?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
};

export function EmptyState({ title, hint, action, icon }: EmptyStateProps) {
  return (
    <div className={styles.root}>
      <div className={styles.icon} aria-hidden="true">
        {icon ?? <Inbox size={20} strokeWidth={1.75} />}
      </div>
      <p className={styles.title}>{title}</p>
      {hint ? <p className={styles.hint}>{hint}</p> : null}
      {action ? <div className={styles.action}>{action}</div> : null}
    </div>
  );
}
