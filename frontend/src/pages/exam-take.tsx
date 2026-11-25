import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ShieldX } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { FormField } from "../components/ui/form-field";
import { Input } from "../components/ui/input";
import { PageHeader } from "../components/ui/page-header";
import { Panel } from "../components/ui/panel";
import { Skeleton } from "../components/ui/skeleton";
import { Textarea } from "../components/ui/textarea";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import styles from "./exam-take.module.css";

const text = copy.examTake;
const TYPE_LABEL: Record<string, string> = {
  single_choice: "单选",
  multi_choice: "多选",
  fill_blank: "填空",
  essay: "简答",
};

type Question = {
  id: number;
  type: string;
  content: string;
  options: string[];
  score: number;
  difficulty: string;
};

type Paper = {
  id: number;
  name: string;
  total_score: number;
  pass_score: number;
  duration_minutes: number;
  questions: Question[];
};

type SubmitResult = {
  submission_id: number;
  score: number;
  max_score: number;
  pass_score: number;
  passed: boolean;
  wrong_count: number;
};

type Draft = {
  candidateName: string;
  answers: Record<number, string | string[]>;
  startedAt: number;
};

export default function ExamTakePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [params] = useSearchParams();
  const assignmentParam = params.get("assignment_id");
  const assignmentId = assignmentParam && /^\d+$/.test(assignmentParam) ? Number(assignmentParam) : null;
  const candidateParam = params.get("candidate") ?? "";
  const draftKey = assignmentId ? `tl.exam.${id}.${assignmentId}` : `tl.exam.${id}`;
  const [draft] = useState<Draft | null>(() => {
    try {
      const raw = localStorage.getItem(draftKey);
      return raw ? (JSON.parse(raw) as Draft) : null;
    } catch {
      return null;
    }
  });
  const [name, setName] = useState(draft?.candidateName ?? candidateParam);
  const [answers, setAnswers] = useState<Record<number, string | string[]>>(draft?.answers ?? {});
  const [startedAt] = useState(draft?.startedAt ?? Date.now());
  const [now, setNow] = useState(() => Date.now());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [error, setError] = useState("");
  const autoRef = useRef(false);

  const paper = useQuery({
    queryKey: ["exam-paper", id],
    queryFn: () => request<Paper>(`/exams/${id}`),
    enabled: Boolean(id),
  });

  useEffect(() => {
    track("page_view", { page: "exam-take" });
  }, []);

  useEffect(() => {
    if (!startedAt || result) return;
    localStorage.setItem(draftKey, JSON.stringify({ candidateName: name, answers, startedAt } satisfies Draft));
  }, [name, answers, startedAt, result, draftKey]);

  useEffect(() => {
    if (!paper.data || result) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [paper.data, result]);

  const data = paper.data;
  const total = data?.questions.length ?? 0;
  const answered = data
    ? data.questions.filter((q) => {
        const value = answers[q.id];
        return Array.isArray(value) ? value.length > 0 : Boolean(String(value ?? "").trim());
      }).length
    : 0;
  const unanswered = Math.max(0, total - answered);

  const remainingMs = data && startedAt ? Math.max(0, data.duration_minutes * 60_000 - (now - startedAt)) : 0;
  const expired = data && startedAt ? remainingMs <= 0 : false;
  const mm = String(Math.floor(remainingMs / 60_000)).padStart(2, "0");
  const ss = String(Math.floor((remainingMs % 60_000) / 1000)).padStart(2, "0");
  const warn = !expired && remainingMs <= 300_000;

  useEffect(() => {
    if (!expired || result || submitting || autoRef.current) return;
    if (!name.trim()) {
      setError(text.errorName);
      return;
    }
    autoRef.current = true;
    void doSubmit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expired, result, submitting, name]);

  async function doSubmit() {
    if (!data) return;
    if (!name.trim()) {
      setError(text.errorName);
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const payload = data.questions.map((q) => {
        const value = answers[q.id];
        const answerText = Array.isArray(value) ? value.join(",") : String(value ?? "");
        return { question_id: q.id, answer: answerText };
      });
      const res = await request<SubmitResult>(`/exams/${data.id}/submit`, {
        method: "POST",
        body: {
          candidate_name: name.trim(),
          answers: payload,
          ...(assignmentId ? { assignment_id: assignmentId } : {}),
        },
      });
      localStorage.removeItem(draftKey);
      setResult(res);
      void queryClient.invalidateQueries({ queryKey: ["resumes"] });
      void queryClient.invalidateQueries({ queryKey: ["exam-assignments"] });
      void queryClient.invalidateQueries({ queryKey: ["exam-submissions"] });
      track("exam_submit_done", {
        page: "exam-take",
        exam_id: data.id,
        passed: res.passed,
        score: res.score,
      });
    } catch (submitError) {
      const message =
        submitError instanceof ApiError
          ? `${text.errorSubmit}${submitError.message} ${text.errorSubmitHint}`
          : `${text.errorSubmit}${text.errorSubmitHint}`;
      setError(message);
      track("exam_submit_failed", {
        page: "exam-take",
        exam_id: data.id,
        status: submitError instanceof ApiError ? submitError.status : 0,
      });
    } finally {
      setSubmitting(false);
    }
  }

  function setSingle(qid: number, option: string) {
    setAnswers((prev) => ({ ...prev, [qid]: option }));
  }

  function setMulti(qid: number, option: string) {
    setAnswers((prev) => {
      const current = Array.isArray(prev[qid]) ? (prev[qid] as string[]) : [];
      const next = current.includes(option) ? current.filter((o) => o !== option) : [...current, option];
      return { ...prev, [qid]: next };
    });
  }

  if (paper.isError) {
    const err = paper.error;
    if (err instanceof ApiError && err.status === 403) {
      return (
        <div className={styles.page}>
          <div className={styles.pageHead}>
            <PageHeader title={text.titleFallback} actions={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
          </div>
          <EmptyState icon={<ShieldX size={20} strokeWidth={1.75} />} title={text.forbiddenTitle} hint={text.forbiddenHint} />
        </div>
      );
    }
    if (err instanceof ApiError && err.status === 404) {
      return (
        <div className={styles.page}>
          <div className={styles.pageHead}>
            <PageHeader title={text.titleFallback} actions={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
          </div>
          <EmptyState title={text.notFoundTitle} hint={text.notFoundHint} action={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
        </div>
      );
    }
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.titleFallback} actions={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
        </div>
        <ErrorState title={text.loadError} detail={err instanceof ApiError ? err.message : text.loadErrorHint} retryLabel={text.retry} onRetry={() => void paper.refetch()} />
      </div>
    );
  }

  if (paper.isPending || !data) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.titleFallback} actions={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
        </div>
        <div className={styles.skeletonStack}>
          <Skeleton width="full" height="title" />
          <Skeleton width="full" />
          <Skeleton width="wide" />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader
          title={data.name}
          sub={text.meta(total, data.duration_minutes, data.pass_score, data.total_score)}
          actions={
            <>
              <Button variant="secondary" onClick={() => navigate("/exams")} disabled={submitting}>
                <ArrowLeft size={16} strokeWidth={1.75} aria-hidden="true" />
                {text.back}
              </Button>
              {!result ? (
                <Button variant="primary" loading={submitting} onClick={() => setConfirmOpen(true)}>
                  {submitting ? text.submitting : text.submit}
                </Button>
              ) : null}
            </>
          }
        />
      </div>

      <div className={styles.body}>
      {assignmentId ? (
        <p className={styles.assignmentBanner} role="status">
          {text.assignmentBanner}
        </p>
      ) : (
        <p className={styles.assignmentBannerMuted} role="status">
          {text.assignmentNoBinding}
        </p>
      )}
      {result ? (
        <Panel title={text.doneTitle} className={styles.glassPanel}>
          <div className={styles.resultRow}>
            <div className={styles.resultScore}>
              <span className={styles.resultValue}>{result.score}</span>
              <span className={styles.resultUnit}>/ {result.max_score}</span>
            </div>
            <Badge tone={result.passed ? "success" : "neutral"}>
              {result.passed ? text.donePassed : text.doneFailed}
            </Badge>
            <span className={styles.resultMeta}>{text.doneWrong(result.wrong_count)}</span>
            <Button variant="secondary" onClick={() => navigate("/exams")}>
              {text.back}
            </Button>
          </div>
        </Panel>
      ) : null}

      <Panel title={text.candidatePanel} className={styles.glassPanel}>
        <div className={styles.candidateRow}>
          <div className={styles.candidateField}>
            <FormField
              id="candidate"
              label={text.candidate}
              hint={assignmentId ? text.assignmentCandidateLocked : text.candidateHint}
            >
              <Input
                value={name}
                placeholder={text.candidatePlaceholder}
                onChange={(event) => setName(event.target.value)}
                disabled={Boolean(result) || assignmentId !== null}
              />
            </FormField>
          </div>
          <div className={styles.status}>
            <div className={styles.statusBlock}>
              <span className={styles.statusLabel}>{text.timeLabel}</span>
              <span
                className={warn ? styles.timerWarn : expired ? styles.timerExpired : styles.timer}
                role="timer"
                aria-live="polite"
              >
                {expired ? text.timeUp : text.remaining(mm, ss)}
              </span>
            </div>
            <div className={styles.statusBlock}>
              <span className={styles.statusLabel}>{text.progressLabel}</span>
              <span className={styles.progress}>{text.progress(answered, total)}</span>
            </div>
          </div>
        </div>
        <p className={styles.candidateNote}>{text.candidateNote}</p>
      </Panel>

      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}

      {total === 0 ? (
        <EmptyState title={text.emptyTitle} hint={text.emptyHint} />
      ) : (
        <div className={styles.questions}>
          {data.questions.map((q, index) => {
            const value = answers[q.id];
            const multi = q.type === "multi_choice";
            return (
              <section className={styles.question} key={q.id} aria-labelledby={`q-${q.id}`}>
                <div className={styles.qHead}>
                  <span className={styles.qIndex}>{text.question(index + 1)}</span>
                  <Badge tone={q.type === "essay" ? "info" : "neutral"}>{TYPE_LABEL[q.type] ?? q.type}</Badge>
                  <span className={styles.points}>{text.points(q.score)}</span>
                </div>
                <p className={styles.qText} id={`q-${q.id}`}>
                  {q.content}
                </p>

                {q.type === "single_choice" || multi ? (
                  <fieldset className={styles.options}>
                    <legend className={styles.visuallyHidden}>{text.question(index + 1)}</legend>
                    {q.options.map((option, oi) => {
                      const checked = multi
                        ? Array.isArray(value) && value.includes(option)
                        : value === option;
                      return (
                        <label key={option} className={checked ? `${styles.option} ${styles.optionActive}` : styles.option}>
                          <input
                            type={multi ? "checkbox" : "radio"}
                            name={`q-${q.id}`}
                            checked={Boolean(checked)}
                            disabled={Boolean(result)}
                            onChange={() => (multi ? setMulti(q.id, option) : setSingle(q.id, option))}
                          />
                          <span className={styles.letter} aria-hidden="true">
                            {String.fromCharCode(65 + oi)}
                          </span>
                          <span className={styles.optionText}>{option}</span>
                        </label>
                      );
                    })}
                  </fieldset>
                ) : q.type === "essay" ? (
                  <Textarea
                    value={String(value ?? "")}
                    placeholder={text.essayPlaceholder}
                    aria-label={text.question(index + 1)}
                    disabled={Boolean(result)}
                    onChange={(event) => setAnswers((prev) => ({ ...prev, [q.id]: event.target.value }))}
                  />
                ) : (
                  <Input
                    value={String(value ?? "")}
                    placeholder={text.fillPlaceholder}
                    aria-label={text.question(index + 1)}
                    disabled={Boolean(result)}
                    onChange={(event) => setAnswers((prev) => ({ ...prev, [q.id]: event.target.value }))}
                  />
                )}
              </section>
            );
          })}
        </div>
      )}

      {!result && total > 0 ? (
        <div className={styles.footRow}>
          <span className={styles.progress}>{text.progress(answered, total)}</span>
          <span className={styles.autoNote}>{text.autoSubmitNote}</span>
          <Button variant="primary" loading={submitting} onClick={() => setConfirmOpen(true)}>
            {submitting ? text.submitting : text.submit}
          </Button>
        </div>
      ) : null}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title={text.confirmTitle}
        description={unanswered > 0 ? text.confirmWithMissing(unanswered) : text.confirmAllAnswered}
        confirmLabel={text.confirm}
        busy={submitting}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false);
          void doSubmit();
        }}
      />
    </div>
  );
}
