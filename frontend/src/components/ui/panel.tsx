import type { ReactNode } from "react";

import { cx } from "../../lib/cx";
import styles from "./panel.module.css";

type PanelProps = {
  title: string;
  meta?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  flush?: boolean;
  className?: string;
  id?: string;
};

export function Panel({ title, meta, actions, children, flush = false, className, id }: PanelProps) {
  return (
    <section className={cx(styles.panel, className)} id={id} aria-labelledby={id ? `${id}-title` : undefined}>
      <header className={styles.head}>
        <div className={styles.heading}>
          <h2 className={styles.title} id={id ? `${id}-title` : undefined}>
            {title}
          </h2>
          {meta ? <p className={styles.meta}>{meta}</p> : null}
        </div>
        {actions ? <div className={styles.actions}>{actions}</div> : null}
      </header>
      <div className={cx(styles.body, flush && styles.flush)}>{children}</div>
    </section>
  );
}
