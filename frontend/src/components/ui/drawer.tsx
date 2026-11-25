import { useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { useFocusTrap } from "../../lib/use-focus-trap";
import { IconButton } from "./icon-button";
import { copy } from "../../content/copy";
import styles from "./drawer.module.css";

type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  meta?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
};

export function Drawer({ open, onClose, title, meta, children, footer }: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useFocusTrap(panelRef, open, onClose);

  if (!open) return null;

  return createPortal(
    <div
      className={styles.overlay}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className={`${styles.panel} glass-drawer`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className={styles.head}>
          <div className={styles.heading}>
            <h2 className={styles.title} id={titleId}>
              {title}
            </h2>
            {meta ? <div className={styles.meta}>{meta}</div> : null}
          </div>
          <IconButton label={copy.common.close} onClick={onClose}>
            <X size={16} strokeWidth={1.75} aria-hidden="true" />
          </IconButton>
        </header>
        <div className={styles.body}>{children}</div>
        {footer ? <footer className={styles.foot}>{footer}</footer> : null}
      </div>
    </div>,
    document.body,
  );
}
