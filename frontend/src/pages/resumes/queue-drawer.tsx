import { useState } from "react";

import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Drawer } from "../../components/ui/drawer";
import { EmptyState } from "../../components/ui/empty-state";
import { ErrorState } from "../../components/ui/error-state";
import { Skeleton } from "../../components/ui/skeleton";
import { copy } from "../../content/copy";
import { formatDateTime } from "../../lib/format";
import type { QueueData, QueueTask } from "./types";
import styles from "./queue-drawer.module.css";

const text = copy.resumes;

const STATUS_ORDER = ["waiting", "parsing", "need_ocr", "failed", "completed"];

function toneFor(status: string) {
  if (status === "completed") return "success" as const;
  if (status === "failed") return "error" as const;
  if (status === "need_ocr") return "warning" as const;
  if (status === "parsing") return "info" as const;
  return "neutral" as const;
}

type QueueDrawerProps = {
  open: boolean;
  onClose: () => void;
  data?: QueueData;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  pending: number;
  canProcess: boolean;
  processing: boolean;
  onProcess: () => void;
  canDelete: boolean;
  removingId: number | null;
  onRemove: (task: QueueTask) => void;
};

export function QueueDrawer({
  open,
  onClose,
  data,
  loading,
  error,
  onRetry,
  pending,
  canProcess,
  processing,
  onProcess,
  canDelete,
  removingId,
  onRemove,
}: QueueDrawerProps) {
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const tasks = data?.tasks ?? [];

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={text.queueTitle}
      meta={text.queueMeta(pending)}
      footer={
        canProcess ? (
          <Button
            variant="secondary"
            loading={processing}
            disabled={pending === 0}
            onClick={onProcess}
          >
            {processing ? text.processing : text.processNext}
          </Button>
        ) : null
      }
    >
      <div className={styles.counts}>
        {STATUS_ORDER.map((status) => (
          <div className={styles.count} key={status}>
            <span className={styles.countValue}>{data?.counts[status] ?? 0}</span>
            <span className={styles.countLabel}>{text.status[status]}</span>
          </div>
        ))}
      </div>

      {error ? (
        <ErrorState title={text.queueError} retryLabel={text.retry} onRetry={onRetry} />
      ) : loading ? (
        <div className={styles.skeleton}>
          <Skeleton width="full" />
          <Skeleton width="wide" />
          <Skeleton width="full" />
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState title={text.queueEmpty} hint={text.queueEmptyHint} />
      ) : (
        <ul className={styles.list}>
          {tasks.map((task) => (
            <li className={styles.item} key={task.task_id}>
              <div className={styles.itemHead}>
                <span className={styles.file} title={task.filename}>
                  {task.filename}
                </span>
                <Badge tone={toneFor(task.status)}>{text.status[task.status] ?? task.status}</Badge>
              </div>
              <div className={styles.itemMeta}>
                <span>
                  {copy.resumes.queueColumns.attempts} {task.attempts}
                </span>
                <span>{formatDateTime(task.created_at)}</span>
              </div>
              {task.error ? <p className={styles.error}>{task.error}</p> : null}
              {canDelete ? (
                confirmId === task.task_id ? (
                  <div className={styles.confirm}>
                    <span>{text.removeHint(task.filename)}</span>
                    <div className={styles.confirmActions}>
                      <Button variant="ghost" onClick={() => setConfirmId(null)}>
                        {copy.common.cancel}
                      </Button>
                      <Button
                        variant="destructive"
                        loading={removingId === task.task_id}
                        onClick={() => {
                          onRemove(task);
                          setConfirmId(null);
                        }}
                      >
                        {text.confirmRemove}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className={styles.itemActions}>
                    <Button variant="ghost" onClick={() => setConfirmId(task.task_id)}>
                      {text.remove}
                    </Button>
                  </div>
                )
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Drawer>
  );
}
