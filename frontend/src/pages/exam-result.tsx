import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ShieldX } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { PageHeader } from "../components/ui/page-header";
import { Panel } from "../components/ui/panel";
import { Skeleton } from "../components/ui/skeleton";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { formatDateTime } from "../lib/format";
import styles from "./exam-result.module.css";

const text = copy.examResult;
const TYPE_LABEL: Record<string, string> = {
  single_choice: "单选",
  multi_choice: "多选",
  fill_blank: "填空",
  essay: "简答",
};

type DetailRow = {
  question_id: number;
  type: string;
  content: string;
  score: number;
  max_score: number;
  answer: string;
  standard: string;
  comment: string;
  analysis: string;
};

type SubmissionDetail = {
  id: number;
  exam_name: string;
  candidate_name: string;
  parsed_resume_id?: number | null;
  audience?: string;
  score: number;
  max_score: number;
  pass_score: number;
  result: string;
  recommendation: string;
  detail: DetailRow[];
};

type WrongRow = {
  id: number;
  candidate_name: string;
  content: string;
  type: string;
  user_answer: string;
  standard_answer: string;
  score: number;
  max_score: number;
  analysis: string;
};

type ReviewPlan = {
  id: number;
  candidate_name: string;
  content: string;
  type: string;
  review_time: string;
  status: string;
};

export default function ExamResultPage() {
  const { sid } = useParams();
  const navigate = useNavigate();

  const detail = useQuery({
    queryKey: ["exam-submission", sid],
    queryFn: () => request<SubmissionDetail>(`/exam-submissions/${sid}`),
    enabled: Boolean(sid),
  });

  const candidate = detail.data?.candidate_name ?? "";

  const wrong = useQuery({
    queryKey: ["wrong-questions", candidate],
    queryFn: () => request<WrongRow[]>(`/wrong-questions?candidate_name=${encodeURIComponent(candidate)}`),
    enabled: Boolean(candidate),
  });

  const reviews = useQuery({
    queryKey: ["review-plans", candidate],
    queryFn: () => request<ReviewPlan[]>(`/review-plans?candidate_name=${encodeURIComponent(candidate)}`),
    enabled: Boolean(candidate),
  });

  useEffect(() => {
    track("page_view", { page: "exam-result" });
  }, []);

  if (detail.isError) {
    const error = detail.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <div className={styles.page}>
          <div className={styles.pageHead}>
            <PageHeader title={text.loadingTitle} actions={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
          </div>
          <EmptyState title={text.notFoundTitle} hint={text.notFoundHint} action={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
        </div>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <div className={styles.page}>
          <div className={styles.pageHead}>
            <PageHeader title={text.loadingTitle} actions={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
          </div>
          <EmptyState icon={<ShieldX size={20} strokeWidth={1.75} />} title={text.forbiddenTitle} hint={text.forbiddenHint} />
        </div>
      );
    }
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.loadingTitle} actions={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
        </div>
        <ErrorState title={text.loadError} detail={error instanceof ApiError ? error.message : text.loadErrorHint} retryLabel={text.retry} onRetry={() => void detail.refetch()} />
      </div>
    );
  }

  if (detail.isPending || !detail.data) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.loadingTitle} actions={<Button variant="secondary" onClick={() => navigate("/exams")}>{text.back}</Button>} />
        </div>
        <div className={styles.skeletonStack}>
          <Skeleton width="full" height="title" />
          <Skeleton width="full" />
          <Skeleton width="wide" />
        </div>
      </div>
    );
  }

  const data = detail.data;
  const passed = data.result === "passed" || data.score >= data.pass_score;
  const wrongRows = (data.detail ?? []).filter((row) => row.score < row.max_score);
  const wrongContents = new Set(wrongRows.map((row) => row.content));
  const paperPlans = (reviews.data ?? []).filter((plan) => wrongContents.has(plan.content));
  const cumulative = wrong.data?.length ?? 0;

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader
          title={text.title(data.candidate_name || copy.common.unknown)}
          sub={text.sub(data.exam_name, data.max_score, data.pass_score)}
          actions={
            <>
              {data.parsed_resume_id ? (
                <Button
                  variant="secondary"
                  onClick={() => navigate(`/resumes?resume=${data.parsed_resume_id}`)}
                >
                  {text.viewResume}
                </Button>
              ) : null}
              <Button variant="secondary" onClick={() => navigate("/exams")}>
                <ArrowLeft size={16} strokeWidth={1.75} aria-hidden="true" />
                {text.back}
              </Button>
            </>
          }
        />
      </div>

      <div className={styles.body}>
        <Panel title={text.summaryTitle} className={styles.glassPanel}>
          <div className={styles.verdict}>
            <span className={passed ? styles.scorePass : styles.scoreFail}>{data.score}</span>
            <span className={styles.scoreMax}>/ {data.max_score}</span>
            <Badge tone={passed ? "success" : "neutral"}>{passed ? copy.exams.passed : copy.exams.failed}</Badge>
          </div>
          <p className={styles.line}>{text.conclusion(data.score, data.max_score, data.pass_score, passed)}</p>
          {data.recommendation ? (
            <p className={styles.recommendation}>
              <span className={styles.recommendationLabel}>{text.recommendation}</span>
              {data.recommendation}
            </p>
          ) : null}
          {cumulative > 0 ? <p className={styles.cumulative}>{text.cumulativeWrong(cumulative)}</p> : null}
        </Panel>

        <Panel title={text.wrongTitle} meta={text.wrongCount(wrongRows.length)} className={styles.glassTable} flush>
          {wrongRows.length === 0 ? (
            <div className={styles.emptyWrap}>
              <EmptyState title={text.wrongEmpty} />
            </div>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col" className={styles.colQuestion}>{text.wrongColumns.question}</th>
                    <th scope="col">{text.wrongColumns.yours}</th>
                    <th scope="col" className={styles.hideTablet}>{text.wrongColumns.standard}</th>
                    <th scope="col" className={styles.alignEnd}>{text.wrongColumns.score}</th>
                    <th scope="col" className={styles.hideTablet}>{text.wrongColumns.analysis}</th>
                  </tr>
                </thead>
                <tbody>
                  {wrongRows.map((row) => (
                    <tr key={row.question_id}>
                      <td className={styles.colQuestion}>
                        <p className={styles.qContent}>{row.content}</p>
                        <span className={styles.qMeta}>
                          {TYPE_LABEL[row.type] ?? row.type}
                        </span>
                      </td>
                      <td className={styles.answer}>{row.answer.trim() ? row.answer : text.noAnswer}</td>
                      <td className={`${styles.answer} ${styles.hideTablet}`}>{row.standard}</td>
                      <td className={`${styles.alignEnd} ${styles.scoreCell}`}>{text.scoreOf(row.score, row.max_score)}</td>
                      <td className={`${styles.analysis} ${styles.hideTablet}`}>
                        {row.analysis || row.comment || text.noAnalysis}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className={styles.standardNote}>{text.standardNote}</p>
            </div>
          )}
        </Panel>

        <Panel title={text.reviewTitle} meta={text.reviewMeta} className={styles.glassTable} flush>
          {paperPlans.length === 0 ? (
            <div className={styles.emptyWrap}>
              <EmptyState title={text.reviewEmpty} />
            </div>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th scope="col">{text.reviewColumns.time}</th>
                    <th scope="col">{text.reviewColumns.question}</th>
                    <th scope="col" className={styles.alignEnd}>{text.reviewColumns.status}</th>
                  </tr>
                </thead>
                <tbody>
                  {paperPlans.map((plan) => (
                    <tr key={plan.id}>
                      <td className={styles.nowrap}>{formatDateTime(plan.review_time)}</td>
                      <td>{plan.content}</td>
                      <td className={styles.alignEnd}>
                        <Badge tone="info">{plan.status === "scheduled" ? text.statusScheduled : plan.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
