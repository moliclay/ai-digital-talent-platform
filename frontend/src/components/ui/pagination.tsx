import { ChevronLeft, ChevronRight } from "lucide-react";

import { copy } from "../../content/copy";
import { Button } from "./button";
import styles from "./pagination.module.css";

type PaginationProps = {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
  label: string;
};

export function Pagination({ page, pageSize, total, onChange, label }: PaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className={styles.root}>
      <span className={styles.label}>{label}</span>
      <div className={styles.actions}>
        <Button
          variant="secondary"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label={copy.pagination.prev}
        >
          <ChevronLeft size={16} strokeWidth={1.75} aria-hidden="true" />
        </Button>
        <span className={styles.page}>
          {page} / {pageCount}
        </span>
        <Button
          variant="secondary"
          disabled={page >= pageCount}
          onClick={() => onChange(page + 1)}
          aria-label={copy.pagination.next}
        >
          <ChevronRight size={16} strokeWidth={1.75} aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
