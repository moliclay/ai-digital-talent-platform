import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, Link } from "react-router-dom";
import { ShieldX } from "lucide-react";

import { AudienceFilter, type AudienceValue } from "../components/audience-filter";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { DataTable, type Column } from "../components/ui/data-table";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { PageHeader } from "../components/ui/page-header";
import { Pagination } from "../components/ui/pagination";
import { Panel } from "../components/ui/panel";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { formatDateTime } from "../lib/format";
import { hasPermission } from "../lib/permission";
import { BankDialog } from "./exams/bank-dialog";
import { AssignmentDialog } from "./exams/assignment-dialog";
import { ExamDialog } from "./exams/exam-dialog";
import styles from "./exams.module.css";
import { QuestionDialog } from "./exams/question-dialog";
import { QuestionImportDialog } from "./exams/question-import-dialog";
import type {
  AssignmentsResult,
  Bank,
  Exam,
  ExamAssignment,
  PageData,
  Question,
  Submission,
} from "./exams/types";

const text = copy.exams;
const QUESTION_PAGE_SIZE = 50;

const TYPE_LABEL: Record<string, string> = {
  single_choice: "单选",
  multi_choice: "多选",
  fill_blank: "填空",
  essay: "简答",
};
const DIFFICULTY_LABEL: Record<string, string> = { easy: "简单", medium: "中等", hard: "困难" };

export default function ExamsPage() {
  const { me } = useAuth();
  const navigate = useNavigate();
  const [selectedBank, setSelectedBank] = useState("");
  const [questionPage, setQuestionPage] = useState(1);
  const [bankOpen, setBankOpen] = useState(false);
  const [questionOpen, setQuestionOpen] = useState(false);
  const [examOpen, setExamOpen] = useState(false);
  const [bindOpen, setBindOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [audience, setAudience] = useState<AudienceValue>("all");
  const [assignmentStatus, setAssignmentStatus] = useState("");
  const [assignmentToCancel, setAssignmentToCancel] = useState<ExamAssignment | null>(null);
  const [banner, setBanner] = useState<{ tone: "ok" | "error"; message: string } | null>(null);
  const queryClient = useQueryClient();

  const canCreate = hasPermission(me, "exam:create");
  const audienceQuery = audience === "all" ? "" : `?audience=${audience}`;

  useEffect(() => {
    track("page_view", { page: "exams" });
  }, []);

  const banks = useQuery({
    queryKey: ["question-banks", audience],
    queryFn: () => request<Bank[]>(`/question-banks${audienceQuery}`),
  });

  const questions = useQuery({
    queryKey: ["questions", selectedBank, questionPage],
    queryFn: () =>
      request<PageData<Question>>(
        `/questions?bank_id=${selectedBank}&page=${questionPage}&page_size=${QUESTION_PAGE_SIZE}`,
      ),
    enabled: Boolean(selectedBank),
  });

  const exams = useQuery({
    queryKey: ["exams", audience],
    queryFn: () => request<Exam[]>(`/exams${audienceQuery}`),
  });

  const assignments = useQuery({
    queryKey: ["exam-assignments", assignmentStatus],
    queryFn: () =>
      request<AssignmentsResult>(
        `/exam-assignments${assignmentStatus ? `?status=${assignmentStatus}` : ""}`,
      ),
  });

  const submissions = useQuery({
    queryKey: ["exam-submissions"],
    queryFn: () => request<Submission[]>("/exam-submissions"),
  });

  const ai = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => request<{ available: boolean }>("/ai/status"),
  });

  useEffect(() => {
    const list = banks.data ?? [];
    if (!list.length) {
      if (selectedBank) setSelectedBank("");
      return;
    }
    if (!list.some((bank) => String(bank.id) === selectedBank)) {
      setSelectedBank(String(list[0].id));
      setQuestionPage(1);
    }
  }, [banks.data, selectedBank]);

  const cancelAssignment = useMutation({
    mutationFn: (id: number) => request(`/exam-assignments/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      setAssignmentToCancel(null);
      setBanner({ tone: "ok", message: text.cancelDone });
      void queryClient.invalidateQueries({ queryKey: ["exam-assignments"] });
      void queryClient.invalidateQueries({ queryKey: ["resumes"] });
    },
    onError: (error) => {
      setAssignmentToCancel(null);
      setBanner({
        tone: "error",
        message:
          error instanceof ApiError && error.status === 409
            ? text.cancelConflict
            : error instanceof ApiError
              ? error.message
              : text.cancelError,
      });
    },
  });

  if (banks.error instanceof ApiError && banks.error.status === 403) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <EmptyState
          icon={<ShieldX size={20} strokeWidth={1.75} />}
          title={text.noPermissionTitle}
          hint={text.noPermissionHint}
        />
      </div>
    );
  }

  const bankList = banks.data ?? [];
  const questionRows = questions.data?.items ?? [];
  const questionTotal = questions.data?.total ?? 0;
  const examList = exams.data ?? [];
  const submissionList = submissions.data ?? [];
  const allAssignments = assignments.data?.items ?? [];
  const assignmentList =
    audience === "all"
      ? allAssignments
      : allAssignments.filter((assignment) => assignment.audience === audience);

  const examColumns: Column<Exam>[] = [
    { key: "name", header: text.examColumns.name, render: (row) => <span className={styles.strong}>{row.name}</span> },
    { key: "category", header: text.examColumns.category, width: "calc(var(--space-5xl) + var(--space-md))", render: (row) => row.category, hideOnTablet: true },
    {
      key: "audience",
      header: text.audienceColumn,
      width: "calc(var(--space-5xl))",
      render: (row) => (
        <Badge tone={row.audience === "employee" ? "info" : "neutral"}>
          {copy.common.audience[row.audience] ?? row.audience}
        </Badge>
      ),
    },
    { key: "questions", header: text.examColumns.questions, width: "calc(var(--space-5xl))", render: (row) => row.total_questions, hideOnTablet: true },
    { key: "score", header: text.examColumns.score, width: "calc(var(--space-5xl))", render: (row) => row.total_score },
    { key: "pass", header: text.examColumns.pass, width: "calc(var(--space-5xl))", render: (row) => row.pass_score },
    { key: "duration", header: text.examColumns.duration, width: "calc(var(--space-5xl) + var(--space-md))", render: (row) => text.duration(row.duration_minutes), hideOnTablet: true },
    { key: "submissions", header: text.examColumns.submissions, width: "calc(var(--space-5xl))", render: (row) => text.submissionsCount(row.submissions) },
    {
      key: "action",
      header: text.examColumns.action,
      width: "calc(var(--space-5xl) * 2)",
      render: (row) => (
        <Button variant="secondary" onClick={() => navigate(`/exams/${row.id}/take`)}>
          {text.take}
        </Button>
      ),
    },
  ];
  const submissionColumns: Column<Submission>[] = [
    { key: "candidate", header: text.submissionColumns.candidate, render: (row) => <Link className={styles.nameLink} to={`/exams/result/${row.id}`}>{row.candidate_name}</Link> },
    { key: "exam", header: text.submissionColumns.exam, render: (row) => row.exam_name },
    { key: "score", header: text.submissionColumns.score, width: "calc(var(--space-5xl) + var(--space-2xl))", render: (row) => text.score(row.score, row.max_score) },
    {
      key: "result",
      header: text.submissionColumns.result,
      width: "calc(var(--space-5xl) + var(--space-2xl))",
      render: (row) => (
        <Badge tone={row.result === "passed" ? "success" : "neutral"}>
          {row.result === "passed" ? text.passed : text.failed}
        </Badge>
      ),
    },
    { key: "recommendation", header: text.submissionColumns.recommendation, render: (row) => <span className={styles.ellipsis} title={row.recommendation}>{row.recommendation}</span> },
  ];

  const questionColumns: Column<Question>[] = [
    {
      key: "type",
      header: text.questionColumns.type,
      width: "calc(var(--space-5xl) + var(--space-2xs))",
      render: (row) => <Badge tone={row.type === "essay" ? "info" : "neutral"}>{TYPE_LABEL[row.type] ?? row.type}</Badge>,
    },
    {
      key: "content",
      header: text.questionColumns.content,
      render: (row) => <span className={styles.ellipsis} title={row.content}>{row.content}</span>,
    },
    { key: "score", header: text.questionColumns.score, width: "calc(var(--space-5xl))", render: (row) => row.score },
    { key: "difficulty", header: text.questionColumns.difficulty, width: "calc(var(--space-5xl))", render: (row) => DIFFICULTY_LABEL[row.difficulty] ?? row.difficulty, hideOnTablet: true },
    {
      key: "knowledge",
      header: text.questionColumns.knowledge,
      width: "calc(var(--space-5xl) * 2)",
      render: (row) => row.knowledge_point || row.knowledge_category || copy.common.empty,
      hideOnTablet: true,
    },
    {
      key: "answer",
      header: text.questionColumns.answer,
      width: "calc(var(--space-5xl) * 2)",
      render: (row) => <span className={styles.ellipsis} title={row.answer}>{row.answer}</span>,
      hideOnTablet: true,
    },
  ];

  const assignmentColumns: Column<ExamAssignment>[] = [
    {
      key: "candidate",
      header: text.assignmentColumns.candidate,
      render: (row) => (
        <Link className={styles.nameLink} to={`/exams?resume=${row.parsed_resume_id}`}>
          {row.candidate_name}
        </Link>
      ),
    },
    {
      key: "exam",
      header: text.assignmentColumns.exam,
      render: (row) => (
        <span className={styles.assignmentExam}>
          {row.exam_name}
          <Badge tone={row.audience === "employee" ? "info" : "neutral"}>
            {copy.common.audience[row.audience] ?? row.audience}
          </Badge>
        </span>
      ),
    },
    {
      key: "status",
      header: text.assignmentColumns.status,
      width: "calc(var(--space-5xl) + var(--space-md))",
      render: (row) => (
        <Badge tone={row.status === "submitted" ? "success" : row.status === "cancelled" ? "neutral" : "info"}>
          {text.assignmentStatus[row.status] ?? row.status}
        </Badge>
      ),
    },
    {
      key: "deadline",
      header: text.assignmentColumns.deadline,
      width: "calc(var(--space-5xl) * 2)",
      render: (row) => (row.deadline ? formatDateTime(row.deadline) : copy.common.empty),
      hideOnTablet: true,
    },
    {
      key: "result",
      header: text.assignmentColumns.result,
      width: "calc(var(--space-5xl) * 2)",
      render: (row) =>
        row.result ? (
          <span className={styles.assignmentResult}>
            {row.result.score} / {row.result.max_score}
            <Badge tone={row.result.passed ? "success" : "neutral"}>
              {row.result.passed ? text.passed : text.failed}
            </Badge>
          </span>
        ) : (
          copy.common.empty
        ),
    },
    {
      key: "actions",
      header: text.assignmentColumns.actions,
      width: "calc(var(--space-5xl) * 4)",
      render: (row) => (
        <div className={styles.rowActions}>
          {row.status === "pending" ? (
            <>
              <Button
                variant="secondary"
                onClick={() =>
                  navigate(
                    `/exams/${row.exam_id}/take?assignment_id=${row.id}&candidate=${encodeURIComponent(row.candidate_name)}`,
                  )
                }
              >
                {text.takeAssignment}
              </Button>
              {canCreate ? (
                <Button variant="ghost" onClick={() => setAssignmentToCancel(row)}>
                  {text.cancelAssignment}
                </Button>
              ) : null}
            </>
          ) : null}
          {row.submission_id ? (
            <Button variant="ghost" onClick={() => navigate(`/exams/result/${row.submission_id}`)}>
              {text.resultLink}
            </Button>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader title={text.title} sub={text.sub} />
      </div>

      {ai.isSuccess && !ai.data.available ? (
        <p className={styles.aiBanner} role="status">
          {text.aiOnlyKeyword}
        </p>
      ) : null}

      {banner ? (
        <p className={banner.tone === "ok" ? styles.bannerOk : styles.bannerError} role="status">
          {banner.message}
        </p>
      ) : null}

      <section className={styles.section} aria-label={text.assignmentsTitle}>
        <Panel
          id="assignments"
          title={text.assignmentsTitle}
          meta={text.assignmentsMeta}
          className={styles.glassTable}
          actions={
            <>
              <Select
                value={assignmentStatus}
                options={[
                  { value: "", label: "全部状态" },
                  { value: "pending", label: text.assignmentStatus.pending },
                  { value: "submitted", label: text.assignmentStatus.submitted },
                  { value: "cancelled", label: text.assignmentStatus.cancelled },
                ]}
                onChange={setAssignmentStatus}
                ariaLabel={text.assignmentColumns.status}
              />
              {canCreate ? (
                <Button variant="primary" onClick={() => setBindOpen(true)}>
                  {text.bind}
                </Button>
              ) : null}
            </>
          }
          flush
        >
          {assignments.isError ? (
            <div className={styles.stateWrap}>
              <ErrorState
                title={text.loadError}
                detail={assignments.error instanceof ApiError ? assignments.error.message : text.loadErrorHint}
                retryLabel={text.retry}
                onRetry={() => void assignments.refetch()}
              />
            </div>
          ) : (
            <DataTable
              caption={text.assignmentsTitle}
              columns={assignmentColumns}
              rows={assignmentList}
              rowKey={(row) => row.id}
              loading={assignments.isPending}
              skeletonRows={3}
              empty={
                <div className={styles.emptyWrap}>
                  <EmptyState title={text.assignmentsEmpty} hint={text.assignmentsEmptyHint} />
                </div>
              }
            />
          )}
        </Panel>
      </section>

      <div className={styles.audienceBar}>
        <span className={styles.audienceLabel}>{text.audienceLabel}</span>
        <AudienceFilter value={audience} onChange={setAudience} />
      </div>

      {banks.isError && !(banks.error instanceof ApiError && banks.error.status === 403) ? (
        <ErrorState
          title={text.loadError}
          detail={banks.error instanceof ApiError ? banks.error.message : text.loadErrorHint}
          retryLabel={text.retry}
          onRetry={() => void banks.refetch()}
        />
      ) : banks.isPending ? (
        <div className={styles.skeletonStack}>
          <Skeleton width="full" height="title" />
          <Skeleton width="full" />
        </div>
      ) : (
        <>
          <section className={styles.section} aria-label={text.banksTitle}>
            <Panel
              id="banks"
              title={text.banksTitle}
              className={styles.glassTable}
              actions={
                canCreate ? (
                  <Button
                    variant="primary"
                    onClick={() => {
                      track("exam_bank_open", { page: "exams" });
                      setBankOpen(true);
                    }}
                  >
                    {text.newBank}
                  </Button>
                ) : undefined
              }
            >
              {bankList.length === 0 ? (
                <div className={styles.emptyWrap}>
                  <EmptyState title={text.banksEmpty} hint={text.banksEmptyHint} />
                </div>
              ) : (
                <ul className={styles.bankList}>
                  {bankList.map((bank) => (
                    <li key={bank.id}>
                      <button
                        type="button"
                        className={
                          selectedBank === String(bank.id)
                            ? `${styles.bank} ${styles.bankActive}`
                            : styles.bank
                        }
                        aria-pressed={selectedBank === String(bank.id)}
                        onClick={() => {
                          setSelectedBank(String(bank.id));
                          setQuestionPage(1);
                        }}
                      >
                        <span className={styles.bankHead}>
                          <span className={styles.strong}>{bank.name}</span>
                          <span className={styles.bankMeta}>
                            <Badge tone={bank.audience === "employee" ? "info" : "neutral"}>
                              {copy.common.audience[bank.audience] ?? bank.audience}
                            </Badge>
                            <span className={styles.bankCount}>{text.bankCount(bank.total_questions)}</span>
                          </span>
                        </span>
                        {bank.description ? (
                          <span className={styles.bankDesc}>{bank.description}</span>
                        ) : null}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            {selectedBank ? (
              <Panel
                id="questions"
                title={`${text.banksTitle} · ${bankList.find((bank) => String(bank.id) === selectedBank)?.name ?? ""}`}
                meta={text.questionCount(questionTotal)}
                className={styles.glassTable}
                actions={
                  canCreate ? (
                    <>
                      <Button variant="secondary" onClick={() => setImportOpen(true)}>
                        {text.importTitle}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => {
                          track("exam_question_open", { page: "exams" });
                          setQuestionOpen(true);
                        }}
                      >
                        {text.newQuestion}
                      </Button>
                    </>
                  ) : undefined
                }
                flush
              >
                {questions.isError ? (
                  <div className={styles.stateWrap}>
                    <ErrorState
                      title={text.loadError}
                      detail={questions.error instanceof ApiError ? questions.error.message : text.loadErrorHint}
                      retryLabel={text.retry}
                      onRetry={() => void questions.refetch()}
                    />
                  </div>
                ) : (
                  <>
                    <DataTable
                      caption={text.banksTitle}
                      columns={questionColumns}
                      rows={questionRows}
                      rowKey={(row) => row.id}
                      loading={questions.isPending}
                      skeletonRows={5}
                      empty={
                        <div className={styles.emptyWrap}>
                          <EmptyState title={text.questionsEmpty} hint={text.questionsEmptyHint} />
                        </div>
                      }
                    />
                    {questionTotal > QUESTION_PAGE_SIZE ? (
                      <div className={styles.pagination}>
                        <Pagination
                          page={questionPage}
                          pageSize={QUESTION_PAGE_SIZE}
                          total={questionTotal}
                          onChange={setQuestionPage}
                          label={text.questionCount(questionTotal)}
                        />
                      </div>
                    ) : null}
                  </>
                )}
              </Panel>
            ) : null}
          </section>

          <section className={styles.section} aria-label={text.examsTitle}>
            <Panel
              id="exams"
              title={text.examsTitle}
              className={styles.glassTable}
              actions={
                canCreate ? (
                  <Button
                    variant="primary"
                    onClick={() => {
                      track("exam_create_open", { page: "exams" });
                      setExamOpen(true);
                    }}
                  >
                    {text.newExam}
                  </Button>
                ) : undefined
              }
              flush
            >
              {exams.isError ? (
                <div className={styles.stateWrap}>
                  <ErrorState
                    title={text.loadError}
                    detail={exams.error instanceof ApiError ? exams.error.message : text.loadErrorHint}
                    retryLabel={text.retry}
                    onRetry={() => void exams.refetch()}
                  />
                </div>
              ) : (
                <DataTable
                  caption={text.examsTitle}
                  columns={examColumns}
                  rows={examList}
                  rowKey={(row) => row.id}
                  loading={exams.isPending}
                  skeletonRows={3}
                  empty={
                    <div className={styles.emptyWrap}>
                      <EmptyState title={text.examsEmpty} hint={text.examsEmptyHint} />
                    </div>
                  }
                />
              )}
            </Panel>
          </section>

          <section className={styles.section} aria-label={text.submissionsTitle}>
            <Panel
              id="submissions"
              title={text.submissionsTitle}
              meta={text.submissionsNote}
              className={styles.glassTable}
              flush
            >
              {submissions.isError ? (
                <div className={styles.stateWrap}>
                  <ErrorState
                    title={text.loadError}
                    detail={submissions.error instanceof ApiError ? submissions.error.message : text.loadErrorHint}
                    retryLabel={text.retry}
                    onRetry={() => void submissions.refetch()}
                  />
                </div>
              ) : (
                <DataTable
                  caption={text.submissionsTitle}
                  columns={submissionColumns}
                  rows={submissionList}
                  rowKey={(row) => row.id}
                  loading={submissions.isPending}
                  skeletonRows={3}
                  empty={
                    <div className={styles.emptyWrap}>
                      <EmptyState title={text.submissionsEmpty} hint={text.submissionsEmptyHint} />
                    </div>
                  }
                />
              )}
            </Panel>
          </section>
        </>
      )}

      <BankDialog
        open={bankOpen}
        initialAudience={audience === "all" ? "candidate" : audience}
        onClose={() => setBankOpen(false)}
        onCreated={() => {
          setBankOpen(false);
          setBanner({ tone: "ok", message: text.confirm + "。" });
          void banks.refetch();
        }}
      />
      <QuestionDialog
        open={questionOpen}
        banks={bankList}
        onClose={() => setQuestionOpen(false)}
        onCreated={() => {
          setQuestionOpen(false);
          void questions.refetch();
          void banks.refetch();
        }}
      />
      <ExamDialog
        open={examOpen}
        banks={bankList}
        initialAudience={audience === "all" ? "candidate" : audience}
        onClose={() => setExamOpen(false)}
        onCreated={(result) => {
          setExamOpen(false);
          setBanner({ tone: "ok", message: text.examDone(result.name, result.total_questions) });
          void exams.refetch();
        }}
      />

      <AssignmentDialog
        open={bindOpen}
        exams={examList.filter((exam) => exam.status === "published")}
        onClose={() => setBindOpen(false)}
        onCreated={(result) => {
          setBindOpen(false);
          setBanner({
            tone: "ok",
            message: text.bindResult(result.created_count, result.existed_count, result.failed_count),
          });
          void queryClient.invalidateQueries({ queryKey: ["exam-assignments"] });
          void queryClient.invalidateQueries({ queryKey: ["resumes"] });
        }}
      />

      <QuestionImportDialog
        open={importOpen}
        bankId={selectedBank ? Number(selectedBank) : null}
        bankName={bankList.find((bank) => String(bank.id) === selectedBank)?.name ?? ""}
        onClose={() => setImportOpen(false)}
        onConfirmed={() => {
          void questions.refetch();
          void banks.refetch();
        }}
      />

      <ConfirmDialog
        open={assignmentToCancel !== null}
        title={text.cancelTitle}
        description={
          assignmentToCancel
            ? text.cancelBody(assignmentToCancel.candidate_name)
            : undefined
        }
        confirmLabel={text.cancelAssignment}
        busy={cancelAssignment.isPending}
        onConfirm={() => {
          if (assignmentToCancel) cancelAssignment.mutate(assignmentToCancel.id);
        }}
        onClose={() => setAssignmentToCancel(null)}
      />
    </div>
  );
}
