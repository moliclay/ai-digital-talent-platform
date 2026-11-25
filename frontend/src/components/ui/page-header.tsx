import type { ReactNode } from "react";

import styles from "./page-header.module.css";

type PageHeaderProps = {
  title: string;
  sub?: ReactNode;
  actions?: ReactNode;
};

export function PageHeader({ title, sub, actions }: PageHeaderProps) {
  return (
    <div className={styles.root}>
      <div className={styles.text}>
        <h1 className={styles.title}>{title}</h1>
        {sub ? <p className={styles.sub}>{sub}</p> : null}
      </div>
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </div>
  );
}
