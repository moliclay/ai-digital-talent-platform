import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldX } from "lucide-react";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { DataTable, type Column } from "../../components/ui/data-table";
import { EmptyState } from "../../components/ui/empty-state";
import { ErrorState } from "../../components/ui/error-state";
import { FormField } from "../../components/ui/form-field";
import { Input } from "../../components/ui/input";
import { Modal } from "../../components/ui/modal";
import { PageHeader } from "../../components/ui/page-header";
import { Skeleton } from "../../components/ui/skeleton";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import { formatCount, formatDateTime } from "../../lib/format";
import { hasPermission } from "../../lib/permission";
import { useAuth } from "../../lib/auth";
import type {
  MyTrainingLedgerResult,
  MyTrainingLedgerRow,
  MyTrainingPlan,
  MyTrainingPlansResult,
  MyTrainingSummary,
  MyTrainingTask,
} from "../../lib/api-types";
import styles from "./my-training.module.css";

const text = copy.training.my;
const statusText = copy.training.status;

const LEDGER_COLUMNS: Column<MyTrainingLedgerRow>[] = [
  {
    key: "time",
    header: text.ledgerColumns.time,
    width: "calc(var(--space-5xl) * 3)",
    render: (row) => (
      <time dateTime={row.created_at.replace(" ", "T")}>{formatDateTime(row.created_at)}</time>
    ),
  },
  {
    key: "dimension",
    header: text.ledgerColumns.dimension,
    render: (row) => <span className={styles.strong}>{row.dimension}</span>,
  },
  {
    key: "change",
    header: text.ledgerColumns.change,
    render: (row) => (
      <span className={styles.change}>
        {row.before_score} → {row.after_score}
      </span>
    ),
  },
  {
    key: "delta",
    header: text.ledgerColumns.delta,
    width: "calc(var(--space-5xl) - var(--space-md))",
    render: (row) => (
      <Badge tone={row.delta > 0 ? "success" : "neutral"}>
        {row.delta > 0 ? `+${row.delta}` : row.delta}
      </Badge>
    ),
  },
  {
    key: "source",
    header: text.ledgerColumns.source,
    render: (row) =>
      text.ledgerSources[row.source as keyof typeof text.ledgerSources] ?? row.source,
  },
  {
    key: "note",
    header: text.ledgerColumns.note,
    render: (row) => row.note || copy.common.empty,
  },
];

function statusTone(task: MyTrainingTask) {
  if (task.status === "done") return "success" as const;
  if (task.status === "failed") return "error" as const;
  if (task.status === "learning") return "warning" as const;
  return "neutral" as const;
}

export function MyTrainingView() {
  const { me } = useAuth();
  const queryClient = useQueryClient();
  const [recording, setRecording] = useState<MyTrainingTask | null>(null);
  const [minutes, setMinutes] = useState("30");
  const [progress, setProgress] = useState("0");
  const [actionError, setActionError] = useState("");

  const canView = hasPermission(me, "train:view");
  const canEdit = hasPermission(me, "train:edit");

  const summary = useQuery({
    queryKey: ["my-training-summary"],
    queryFn: () => request<MyTrainingSummary>("/my/training/summary"),
    enabled: canView,
  });
  const onboarded = Boolean(summary.data?.onboarded);

  const plans = useQuery({
    queryKey: ["my-training-plans"],
    queryFn: () => request<MyTrainingPlansResult>("/my/training/plans"),
    enabled: canView && onboarded,
  });

  const ledger = useQuery({
    queryKey: ["my-training-ledger"],
    queryFn: () => request<MyTrainingLedgerResult>("/my/training/ledger"),
    enabled: canView && onboarded,
  });

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["my-training-summary"] });
    void queryClient.invalidateQueries({ queryKey: ["my-training-plans"] });
    void queryClient.invalidateQueries({ queryKey: ["my-training-ledger"] });
  }

  function fail(error: unknown) {
    setActionError(error instanceof ApiError ? error.message : text.actionError);
  }

  const recordMutation = useMutation({
    mutationFn: (payload: { taskId: number; minutes: number; progress: number }) =>
      request<MyTrainingTask>(`/prejob-plans/tasks/${payload.taskId}/progress`, {
        method: "POST",
        body: { minutes: payload.minutes, progress: payload.progress },
      }),
    onSuccess: () => {
      setRecording(null);
      setActionError("");
      refresh();
    },
    onError: fail,
  });

  const completeMutation = useMutation({
    mutationFn: (taskId: number) =>
      request<MyTrainingTask>(`/prejob-plans/tasks/${taskId}/complete`, { method: "POST" }),
    onSuccess: () => {
      setActionError("");
      refresh();
    },
    onError: fail,
  });

  if (!canView) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <EmptyState
          icon={<ShieldX size={20} strokeWidth={1.75} />}
          title={copy.training.noPermissionTitle}
          hint={copy.training.noPermissionHint}
        />
      </div>
    );
  }

  if (summary.isError) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <ErrorState
          title={text.loadError}
          detail={summary.error instanceof ApiError ? summary.error.message : text.loadErrorHint}
          retryLabel={text.retry}
          onRetry={() => void summary.refetch()}
        />
      </div>
    );
  }

  if (summary.isPending) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <div className={styles.skeletonGrid}>
          {Array.from({ length: 4 }).map((_, index) => (
            <div className={styles.summaryCard} key={index}>
              <Skeleton width="short" />
              <Skeleton width="half" height="title" />
            </div>
          ))}
        </div>
        <div className={styles.block}>
          <Skeleton width="full" />
          <Skeleton width="wide" />
          <Skeleton width="full" />
        </div>
      </div>
    );
  }

  if (!onboarded) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <EmptyState title={text.noPlan} hint={text.noPlanHint} />
      </div>
    );
  }

  const planItems = plans.data?.items ?? [];
  const busy = recordMutation.isPending || completeMutation.isPending;

  function openRecord(task: MyTrainingTask) {
    setRecording(task);
    setMinutes("30");
    setProgress(String(task.progress));
    setActionError("");
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader title={text.title} sub={text.sub} />
      </div>

      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>{text.summary.plans}</span>
          <span className={styles.summaryValue}>{formatCount(summary.data?.plans ?? 0)}</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>{text.summary.tasks}</span>
          <span className={styles.summaryValue}>{formatCount(summary.data?.tasks ?? 0)}</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>{text.summary.done}</span>
          <span className={styles.summaryValue}>{formatCount(summary.data?.done_tasks ?? 0)}</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>{text.summary.pending}</span>
          <span className={styles.summaryValue}>{formatCount(summary.data?.pending_tasks ?? 0)}</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>{text.summary.ledger}</span>
          <span className={styles.summaryValue}>{formatCount(summary.data?.ledger ?? 0)}</span>
        </div>
      </div>

      <div className={styles.progressBand}>
        <span className={styles.progressLabel}>{text.summary.progress}</span>
        <span className={styles.progressTrack} aria-hidden>
          <span className={styles.progressFill} style={{ width: `${Math.min(100, Math.max(0, summary.data?.progress_pct ?? 0))}%` }} />
        </span>
        <span className={styles.progressValue}>{summary.data?.progress_pct ?? 0}%</span>
      </div>

      <section className={styles.block} aria-labelledby="my-plans-title">
        <div className={styles.blockHead}>
          <div>
            <h2 className={styles.blockTitle} id="my-plans-title">{text.plansTitle}</h2>
            <p className={styles.blockMeta}>{text.plansMeta}</p>
          </div>
          <span className={styles.muted}>{text.summaryNote}</span>
        </div>

        {plans.isError ? (
          <ErrorState
            title={text.loadError}
            detail={plans.error instanceof ApiError ? plans.error.message : text.loadErrorHint}
            retryLabel={text.retry}
            onRetry={() => void plans.refetch()}
          />
        ) : plans.isPending ? (
          <div className={styles.planSkeleton}>
            <Skeleton width="full" />
            <Skeleton width="wide" />
            <Skeleton width="full" />
          </div>
        ) : planItems.length === 0 ? (
          <EmptyState title={text.noPlan} hint={text.noPlanHint} />
        ) : (
          <div className={styles.plans}>
            {planItems.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                busy={busy}
                canEdit={canEdit}
                actionError={actionError}
                onRecord={openRecord}
                onComplete={(taskId) => completeMutation.mutate(taskId)}
              />
            ))}
          </div>
        )}
      </section>

      <section className={styles.block} aria-labelledby="my-ledger-title">
        <div className={styles.blockHead}>
          <div>
            <h2 className={styles.blockTitle} id="my-ledger-title">{text.ledgerTitle}</h2>
            <p className={styles.blockMeta}>{text.ledgerMeta}</p>
          </div>
        </div>
        {ledger.isError ? (
          <ErrorState
            title={text.loadError}
            detail={ledger.error instanceof ApiError ? ledger.error.message : text.loadErrorHint}
            retryLabel={text.retry}
            onRetry={() => void ledger.refetch()}
          />
        ) : (
          <DataTable
            caption={text.ledgerTitle}
            columns={LEDGER_COLUMNS}
            rows={ledger.data?.items ?? []}
            rowKey={(row) => row.id}
            loading={ledger.isPending}
            skeletonRows={3}
            empty={
              <div className={styles.emptyWrap}>
                <EmptyState title={text.ledgerEmpty} hint={text.ledgerEmptyHint} />
              </div>
            }
          />
        )}
      </section>

      <Modal
        open={recording !== null}
        onClose={() => setRecording(null)}
        title={text.recordTitle}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setRecording(null)} disabled={recordMutation.isPending}>
              {copy.common.cancel}
            </Button>
            <Button
              variant="primary"
              loading={recordMutation.isPending}
              disabled={!recording}
              onClick={() => {
                if (!recording) return;
                recordMutation.mutate({
                  taskId: recording.id,
                  minutes: Math.max(0, Number(minutes) || 0),
                  progress: Math.max(0, Math.min(100, Number(progress) || 0)),
                });
              }}
            >
              {text.save}
            </Button>
          </>
        }
      >
        <div className={styles.form}>
          <FormField id="my-task-minutes" label={text.minutes}>
            <Input
              id="my-task-minutes"
              type="number"
              min={0}
              value={minutes}
              onChange={(event) => setMinutes(event.target.value)}
            />
          </FormField>
          <FormField id="my-task-progress" label={text.progressLabel}>
            <Input
              id="my-task-progress"
              type="number"
              min={0}
              max={100}
              value={progress}
              onChange={(event) => setProgress(event.target.value)}
            />
          </FormField>
        </div>
        {actionError ? <p className={styles.error} role="alert">{actionError}</p> : null}
      </Modal>
    </div>
  );
}

type PlanCardProps = {
  plan: MyTrainingPlan;
  busy: boolean;
  canEdit: boolean;
  actionError: string;
  onRecord: (task: MyTrainingTask) => void;
  onComplete: (taskId: number) => void;
};

function PlanCard({ plan, busy, canEdit, actionError, onRecord, onComplete }: PlanCardProps) {
  return (
    <article className={styles.plan}>
      <div className={styles.planHead}>
        <div className={styles.planTitleWrap}>
          <h3 className={styles.planTitle}>{plan.plan_title}</h3>
          <p className={styles.planMeta}>
            {plan.position_name || copy.common.empty} · {text.weeks(plan.total_weeks)} ·{" "}
            {text.taskProgress(plan.done_tasks, plan.total_tasks)}
          </p>
        </div>
        <Badge tone={plan.status === "done" ? "success" : "info"}>
          {plan.progress_pct}%
        </Badge>
      </div>

      <div className={styles.planProgress}>
        <span className={styles.progressTrack} aria-hidden>
          <span className={styles.progressFill} style={{ width: `${Math.min(100, plan.progress_pct)}%` }} />
        </span>
      </div>

      {plan.goal ? (
        <div className={styles.goal}>
          <span className={styles.goalLabel}>{text.goal}</span>
          <p className={styles.goalText}>{plan.goal}</p>
        </div>
      ) : null}

      {plan.tasks.length === 0 ? (
        <p className={styles.muted}>{text.noTasks}</p>
      ) : (
        <ul className={styles.tasks}>
          {plan.tasks.map((task) => {
            const done = task.status === "done";
            const canComplete = task.progress >= 100 && task.study_minutes >= task.required_minutes;
            return (
              <li className={styles.task} key={task.id}>
                <div className={styles.taskHead}>
                  <span className={styles.taskTitle}>{task.title}</span>
                  <Badge tone={statusTone(task)}>{statusText[task.status as keyof typeof statusText] ?? task.status}</Badge>
                </div>
                <div className={styles.taskMeta}>
                  <span>{task.dimension}</span>
                  <span>{text.minutesText(task.study_minutes, task.required_minutes)}</span>
                  <span>{task.progress}%</span>
                  {task.exam_id ? <span className={styles.examHint}>{text.examHint}</span> : null}
                </div>
                <div className={styles.taskProgress}>
                  <span className={styles.progressTrack} aria-hidden>
                    <span className={styles.progressFill} style={{ width: `${Math.min(100, Math.max(0, task.progress))}%` }} />
                  </span>
                </div>
                {!done && canEdit ? (
                  <div className={styles.taskActions}>
                    <Button variant="secondary" onClick={() => onRecord(task)} disabled={busy}>
                      {text.record}
                    </Button>
                    <Button
                      variant="primary"
                      onClick={() => onComplete(task.id)}
                      disabled={busy || !canComplete}
                      title={!canComplete ? text.completeHint : undefined}
                    >
                      {text.complete}
                    </Button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
      {actionError ? <p className={styles.error} role="alert">{actionError}</p> : null}
    </article>
  );
}
