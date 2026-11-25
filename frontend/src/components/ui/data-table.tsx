import type { ReactNode } from "react";

import { cx } from "../../lib/cx";
import { Skeleton } from "./skeleton";
import styles from "./data-table.module.css";

export type Column<T> = {
  key: string;
  header: ReactNode;
  align?: "left" | "right";
  width?: string;
  hideOnTablet?: boolean;
  render: (row: T) => ReactNode;
};

type DataTableProps<T> = {
  caption: string;
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  loading?: boolean;
  skeletonRows?: number;
  empty?: ReactNode;
  error?: ReactNode;
  selectedKey?: string | number | null;
  rowClassName?: (row: T) => string;
};

export function DataTable<T>({
  caption,
  columns,
  rows,
  rowKey,
  loading = false,
  skeletonRows = 5,
  empty,
  error,
  selectedKey = null,
  rowClassName,
}: DataTableProps<T>) {
  const columnCount = columns.length;

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={cx(styles.th, column.align === "right" && styles.right, column.hideOnTablet && styles.hideTablet)}
                style={column.width ? { width: column.width } : undefined}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {error ? (
            <tr>
              <td className={styles.stateCell} colSpan={columnCount}>
                {error}
              </td>
            </tr>
          ) : loading ? (
            Array.from({ length: skeletonRows }, (_, rowIndex) => (
              <tr key={`skeleton-${rowIndex}`}>
                {columns.map((column) => (
                  <td key={column.key} className={styles.td}>
                    <Skeleton width={column.align === "right" ? "short" : "wide"} />
                  </td>
                ))}
              </tr>
            ))
          ) : rows.length === 0 ? (
            <tr>
              <td className={styles.stateCell} colSpan={columnCount}>
                {empty ?? "暂无数据。"}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                className={cx(
                  styles.row,
                  selectedKey !== null && rowKey(row) === selectedKey && styles.selected,
                  rowClassName?.(row),
                )}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cx(styles.td, column.align === "right" && styles.right, column.hideOnTablet && styles.hideTablet)}
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
