import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Drawer } from "../../components/ui/drawer";
import { ErrorState } from "../../components/ui/error-state";
import { FormField } from "../../components/ui/form-field";
import { Input } from "../../components/ui/input";
import { Modal } from "../../components/ui/modal";
import { Select } from "../../components/ui/select";
import { Skeleton } from "../../components/ui/skeleton";
import { copy } from "../../content/copy";
import { ApiError, request } from "../../lib/api";
import styles from "./dialogs.module.css";
import type { PlanDetail, PlanTask, Submission } from "./types";

const text = copy.training;
const planText = text.plans;

type Props = {
  planId: number | null;
  onClose: () => void;
};

export function PlanDrawer({ planId, onClose }: Props) {
  const queryClient = useQueryClient();
  const [recording, setRecording] = useState<PlanTask | null>(null);
  const [minutes, setMinutes] = useState("30");
  const [progress, setProgress] = useState("0");
  const [actionError, setActionError] = useState("");
  const [assessPick, setAssessPick] = useState("");

  const plan = useQuery({
    queryKey: ["training-plan", planId],
    queryFn: () => request<PlanDetail>(`/prejob-plans/${planId}`),
    enabled: planId !== null,
  });

  const submissions = useQuery({
    queryKey: ["training-submissions", plan.data?.candidate_name],
    queryFn: () =>
      request<Submission[]>(
        `/exam-submissions?candidate_name=${encodeURIComponent(plan.data?.candidate_name ?? "")}&page_size=100`,
      ),
    enabled: Boolean(plan.data?.candidate_name),
  });

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["training-plan", planId] });
    void queryClient.invalidateQueries({ queryKey: ["training-plans"] });
  }

  function fail(error: unknown) {
    setActionError(error instanceof ApiError ? error.message : planText.actionError);
  }

  const progressMutation = useMutation({
    mutationFn: (payload: { taskId: number; minutes: number; progress: number }) =>
      request<PlanTask>(`/prejob-plans/tasks/${payload.taskId}/progress`, {
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
      request<PlanTask>(`/prejob-plans/tasks/${taskId}/complete`, { method: "POST" }),
    onSuccess: () => {
      setActionError("");
      refresh();
    },
    onError: fail,
  });

  const assessMutation = useMutation({
    mutationFn: (payload: { taskId: number; submissionId: number }) =>
      request<PlanTask>(`/prejob-plans/tasks/${payload.taskId}/assess`, {
        method: "POST",
        body: { submission_id: payload.submissionId },
      }),
    onSuccess: () => {
      setAssessPick("");
      setActionError("");
      refresh();
    },
    onError: fail,
  });

  function openRecord(task: PlanTask) {
    setRecording(task);
    setMinutes("30");
    setProgress(String(task.progress));
    setActionError("");
  }

  function submitRecord() {
    if (!recording) return;
    progressMutation.mutate({
      taskId: recording.id,
      minutes: Math.max(0, Number(minutes) || 0),
      progress: Math.max(0, Math.min(100, Number(progress) || 0)),
    });
  }

  const busy = progressMutation.isPending || completeMutation.isPending || assessMutation.isPending;

  return (
    <>
      <Drawer
        open={planId !== null}
        onClose={onClose}
        title={plan.data?.plan_title ?? planText.detailTasks}
        meta={
          plan.data ? (
            <span className={styles.drawerMeta}>
              {plan.data.candidate_name} · {plan.data.position_name || copy.common.empty} ·{" "}
              {planText.weeksText(plan.data.total_weeks)} · {plan.data.mentor || copy.common.empty}
            </span>
          ) : undefined
        }
      >
        {plan.isError ? (
          <ErrorState
            title={planText.loadError}
            detail={plan.error instanceof ApiError ? plan.error.message : planText.loadError}
            retryLabel={planText.retry}
            onRetry={() => void plan.refetch()}
          />
        ) : plan.isPending || !plan.data ? (
          <div className={styles.drawerLoading}>
            <Skeleton />
            <Skeleton width="wide" />
            <Skeleton />
            <Skeleton width="half" />
          </div>
        ) : (
          <div className={styles.drawerBody}>
            <section className={styles.block}>
              <h3 className={styles.blockTitle}>{planText.detailGoal}</h3>
              <p className={styles.blockText}>{plan.data.goal}</p>
            </section>

            <section className={styles.block}>
              <h3 className={styles.blockTitle}>{planText.detailPhases}</h3>
              <ol className={styles.phases}>
                {plan.data.phases.map((phase) => (
                  <li className={styles.phase} key={phase.week}>
                    <span className={styles.phaseWeek}>{planText.phaseWeek(phase.week)}</span>
                    <span className={styles.phaseGoal}>{phase.goal}</span>
                  </li>
                ))}
              </ol>
            </section>

            <section className={styles.block}>
              <h3 className={styles.blockTitle}>{planText.detailTasks}</h3>
              {actionError ? <p className={styles.formError} role="alert">{actionError}</p> : null}
              {plan.data.tasks.length === 0 ? (
                <p className={styles.blockText}>{planText.noTasks}</p>
              ) : (
                <ul className={styles.tasks}>
                  {plan.data.tasks.map((task) => {
                    const eligible = (submissions.data ?? []).filter(
                      (submission) =>
                        submission.candidate_name === plan.data?.candidate_name &&
                        submission.exam_id === task.exam_id,
                    );
                    const done = task.status === "done";
                    return (
                      <li className={styles.task} key={task.id}>
                        <div className={styles.taskHead}>
                          <span className={styles.taskTitle}>{task.title}</span>
                          <Badge
                            tone={
                              done
                                ? "success"
                                : task.status === "failed"
                                  ? "error"
                                  : task.status === "learning"
                                    ? "warning"
                                    : "neutral"
                            }
                          >
                            {text.status[task.status as keyof typeof text.status] ?? task.status}
                          </Badge>
                        </div>
                        <div className={styles.taskMeta}>
                          <span>{task.dimension}</span>
                          <span>{planText.minutesText(task.study_minutes, task.required_minutes)}</span>
                          <span>{task.progress}%</span>
                        </div>
                        <div className={styles.track} aria-hidden>
                          <span className={styles.fill} style={{ width: `${Math.min(100, Math.max(0, task.progress))}%` }} />
                        </div>
                        {!done ? (
                          <div className={styles.taskActions}>
                            <Button size="md" variant="secondary" onClick={() => openRecord(task)} disabled={busy}>
                              {planText.record}
                            </Button>
                            <Button
                              size="md"
                              variant="primary"
                              loading={completeMutation.isPending}
                              disabled={busy}
                              onClick={() => completeMutation.mutate(task.id)}
                            >
                              {planText.complete}
                            </Button>
                            {task.exam_id ? (
                              eligible.length ? (
                                <div className={styles.assessRow}>
                                  <Select
                                    value={assessPick}
                                    options={[
                                      { value: "", label: planText.assessHint },
                                      ...eligible.map((submission) => ({
                                        value: String(submission.id),
                                        label: `提交 #${submission.id} · ${submission.score} 分 · ${submission.result}`,
                                      })),
                                    ]}
                                    onChange={setAssessPick}
                                    ariaLabel={planText.assessHint}
                                  />
                                  <Button
                                    variant="secondary"
                                    disabled={!assessPick || busy}
                                    loading={assessMutation.isPending}
                                    onClick={() =>
                                      assessMutation.mutate({ taskId: task.id, submissionId: Number(assessPick) })
                                    }
                                  >
                                    {planText.assess}
                                  </Button>
                                </div>
                              ) : (
                                <span className={styles.taskHint}>{planText.noSubmission}</span>
                              )
                            ) : null}
                          </div>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          </div>
        )}
      </Drawer>

      <Modal
        open={recording !== null}
        onClose={() => setRecording(null)}
        title={planText.recordTitle}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setRecording(null)} disabled={progressMutation.isPending}>
              {copy.common.cancel}
            </Button>
            <Button variant="primary" onClick={submitRecord} loading={progressMutation.isPending}>
              {planText.save}
            </Button>
          </>
        }
      >
        <div className={styles.formGrid}>
          <FormField id="task-minutes" label={planText.minutes}>
            <Input type="number" min={0} value={minutes} onChange={(event) => setMinutes(event.target.value)} />
          </FormField>
          <FormField id="task-progress" label={planText.progressLabel}>
            <Input
              type="number"
              min={0}
              max={100}
              value={progress}
              onChange={(event) => setProgress(event.target.value)}
            />
          </FormField>
        </div>
      </Modal>
    </>
  );
}
