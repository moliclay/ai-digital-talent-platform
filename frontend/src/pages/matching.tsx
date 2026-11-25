import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, ShieldX, X } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { DataTable, type Column } from "../components/ui/data-table";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { PageHeader } from "../components/ui/page-header";
import { Pagination } from "../components/ui/pagination";
import { Panel } from "../components/ui/panel";
import { ScoreBar } from "../components/ui/score-bar";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { formatCount, formatScore } from "../lib/format";
import { hasPermission } from "../lib/permission";
import styles from "./matching.module.css";

const text = copy.matching;
const PAGE_SIZE = 20;

type JobOption = {
  id: number;
  name: string;
  status: string;
  passing_threshold: number;
};

type Summary = {
  job_profile_id: number;
  total: number;
  passed: number;
  failed: number;
  avg_score: number;
  max_score: number;
  min_score: number;
};

type MatchRow = {
  id: number;
  parsed_resume_id: number;
  job_profile_id: number;
  name: string;
  education: string;
  major: string;
  skills: string[];
  years_experience: number;
  total_score: number;
  passing_threshold: number;
  passed: boolean;
  reason: string;
  skill_hit: number;
  skill_required: number;
};

type MatchPage = {
  items: MatchRow[];
  total: number;
  page: number;
  page_size: number;
};

type RunResult = {
  job_profile_id: number;
  job_profile_name: string;
  scanned: number;
  passed: number;
  failed: number;
  threshold: number;
};

type Filter = "all" | "passed" | "failed";

export default function MatchingPage() {
  const { me } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [jobId, setJobId] = useState(searchParams.get("job") ?? "");
  const [filter, setFilter] = useState<Filter>("all");
  const [page, setPage] = useState(1);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [banner, setBanner] = useState<{ tone: "ok" | "error"; message: string } | null>(null);

  const canRun = hasPermission(me, "match:create");

  useEffect(() => {
    track("page_view", { page: "matching" });
  }, []);

  const jobs = useQuery({
    queryKey: ["job-options", "matching"],
    queryFn: () => request<{ items: JobOption[] }>("/job-profiles?page_size=200"),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!jobId && jobs.data?.items.length) {
      setJobId(String(jobs.data.items[0].id));
    }
  }, [jobs.data, jobId]);

  useEffect(() => {
    if (!jobId || !jobs.data) return;
    if (jobs.data.items.some((item) => String(item.id) === jobId)) return;
    const fallback = jobs.data.items[0];
    if (fallback) {
      setJobId(String(fallback.id));
      setSearchParams({ job: String(fallback.id) }, { replace: true });
    }
  }, [jobs.data, jobId, setSearchParams]);

  const job = jobs.data?.items.find((item) => String(item.id) === jobId) ?? null;

  const summary = useQuery({
    queryKey: ["match-summary", jobId],
    queryFn: () => request<Summary>(`/matching/summary?job_profile_id=${jobId}`),
    enabled: Boolean(jobId),
  });

  const lists = useQuery({
    queryKey: ["match-list", jobId, filter, page],
    queryFn: () => {
      const passed = filter === "all" ? "" : `&passed=${filter === "passed"}`;
      return request<MatchPage>(
        `/matching/lists?job_profile_id=${jobId}&page=${page}&page_size=${PAGE_SIZE}${passed}`,
      );
    },
    enabled: Boolean(jobId),
  });

  const run = useMutation({
    mutationFn: () =>
      request<RunResult>("/matching/run", {
        method: "POST",
        body: { job_profile_id: Number(jobId) },
      }),
    onSuccess: (result) => {
      track("match_run_done", {
        page: "matching",
        scanned: result.scanned,
        passed: result.passed,
      });
      setBanner({ tone: "ok", message: text.runDone(result.scanned, result.passed) });
      setPage(1);
      void summary.refetch();
      void lists.refetch();
    },
    onError: (error) => {
      track("match_run_failed", {
        page: "matching",
        status: error instanceof ApiError ? error.status : 0,
      });
      const message =
        error instanceof ApiError && error.status === 400
          ? text.runNoResume
          : error instanceof ApiError
            ? `${text.runFailed}${error.message}`
            : text.runFailed;
      setBanner({ tone: "error", message });
    },
  });

  if (jobs.error instanceof ApiError && jobs.error.status === 403) {
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

  const jobOptions = (jobs.data?.items ?? []).map((item) => ({
    value: String(item.id),
    label: item.name,
  }));
  const rows = lists.data?.items ?? [];
  const total = lists.data?.total ?? 0;
  const summaryData = summary.data;
  const filterLabel =
    filter === "passed" ? text.filter.passed : filter === "failed" ? text.filter.failed : text.filter.all;

  const summaryItems = [
    { key: "scanned", label: text.summary.scanned, value: summaryData?.total ?? 0, unit: text.summary.unit },
    { key: "passed", label: text.summary.passed, value: summaryData?.passed ?? 0, unit: text.summary.unit },
    { key: "failed", label: text.summary.failed, value: summaryData?.failed ?? 0, unit: text.summary.unit },
    {
      key: "avg",
      label: text.summary.avg,
      value: summaryData?.avg_score ?? 0,
      unit: text.summary.scoreUnit,
      score: true,
    },
    {
      key: "threshold",
      label: text.summary.threshold,
      value: job?.passing_threshold ?? 0,
      unit: text.summary.scoreUnit,
    },
  ];

  const columns: Column<MatchRow>[] = [
    {
      key: "name",
      header: text.columns.name,
      width: "calc(var(--space-5xl) * 2)",
      render: (row) => (
        <Link
          className={styles.nameLink}
          to={`/matching/${row.id}?job=${row.job_profile_id}`}
          title={text.viewDetail}
        >
          {row.name || copy.common.unknown}
        </Link>
      ),
    },
    {
      key: "education",
      header: text.columns.education,
      width: "calc(var(--space-5xl) + var(--space-md))",
      hideOnTablet: true,
      render: (row) => row.education || copy.common.unknown,
    },
    {
      key: "years",
      header: text.columns.years,
      width: "calc(var(--space-5xl) + var(--space-md))",
      hideOnTablet: true,
      render: (row) => text.years(row.years_experience ?? 0),
    },
    {
      key: "skill",
      header: text.columns.skillHit,
      width: "calc(var(--space-5xl) + var(--space-2xl))",
      hideOnTablet: true,
      render: (row) =>
        row.skill_required > 0
          ? text.skillHit(row.skill_hit, row.skill_required)
          : text.noSkill,
    },
    {
      key: "score",
      header: text.columns.score,
      width: "calc(var(--space-5xl) * 3)",
      render: (row) => (
        <ScoreBar
          value={row.total_score}
          threshold={row.passing_threshold}
          size="sm"
          ariaLabel={text.columns.score}
        />
      ),
    },
    {
      key: "result",
      header: text.columns.result,
      width: "calc(var(--space-5xl) + var(--space-2xl))",
      render: (row) => (
        <Badge tone={row.passed ? "success" : "neutral"}>
          {row.passed ? (
            <Check size={12} strokeWidth={2} aria-hidden="true" />
          ) : (
            <X size={12} strokeWidth={2} aria-hidden="true" />
          )}
          {row.passed ? text.pass : text.fail}
        </Badge>
      ),
    },
    {
      key: "reason",
      header: text.columns.reason,
      render: (row) => (
        <span className={styles.reason} title={row.reason}>
          {row.reason || copy.common.empty}
        </span>
      ),
    },
  ];

  if (jobs.isError && !(jobs.error instanceof ApiError && jobs.error.status === 403)) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <ErrorState
          title={text.loadError}
          detail={jobs.error instanceof ApiError ? jobs.error.message : text.loadErrorHint}
          retryLabel={text.retry}
          onRetry={() => void jobs.refetch()}
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

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader
          title={text.title}
          sub={text.sub}
          actions={
            <>
              <div className={styles.jobPicker}>
              <Select
                value={jobId}
                options={jobOptions}
                onChange={(value) => {
                  setJobId(value);
                  setSearchParams(value ? { job: value } : {}, { replace: true });
                  setFilter("all");
                  setPage(1);
                  setBanner(null);
                }}
                ariaLabel={text.jobLabel}
                disabled={jobs.isPending}
              />
            </div>
            {canRun ? (
              <Button
                variant="primary"
                loading={run.isPending}
                disabled={!jobId}
                onClick={() => {
                  track("match_run_start", { page: "matching" });
                  if ((summary.data?.total ?? 0) > 0) setConfirmOpen(true);
                  else run.mutate();
                }}
              >
                {run.isPending
                  ? (summary.data?.total ?? 0) > 0
                    ? text.runningCount(summary.data?.total ?? 0)
                    : text.running
                  : text.run}
              </Button>
            ) : null}
            </>
          }
        />
      </div>

      {banner ? (
        <p className={banner.tone === "ok" ? styles.bannerOk : styles.bannerError} role="status">
          {banner.message}
        </p>
      ) : null}

      {jobs.isPending ? (
        <div className={styles.skeletonStack}>
          <Skeleton width="full" height="title" />
          <Skeleton width="wide" />
        </div>
      ) : jobOptions.length === 0 ? (
        <EmptyState
          title={text.emptyNoJobTitle}
          hint={text.emptyNoJobHint}
          action={
            <Button variant="secondary" onClick={() => navigate("/job-profiles")}>
              {text.goJobs}
            </Button>
          }
        />
      ) : !jobId ? (
        <div className={styles.skeletonStack}>
          <Skeleton width="full" height="title" />
          <Skeleton width="wide" />
        </div>
      ) : (
        <>
          <div className={styles.summaryWrap}>
          <dl className={styles.summary} aria-busy={summary.isPending || undefined}>
            {summaryItems.map((item) => (
              <div className={styles.summaryCell} key={item.key}>
                <dt className={styles.summaryLabel}>{item.label}</dt>
                <dd className={styles.summaryValue}>
                  {summary.isPending ? (
                    <Skeleton width="short" />
                  ) : (
                    <>
                      <span>{item.score ? formatScore(item.value) : formatCount(item.value)}</span>
                      <span className={styles.summaryUnit}>{item.unit}</span>
                    </>
                  )}
                </dd>
              </div>
            ))}
          </dl>
          <p className={styles.summaryNote}>{text.summary.note}</p>
          </div>

          <Panel
            title={text.listTitle}
            meta={job?.name ?? undefined}
            className={styles.glassTable}
            flush
          >
            <div className={styles.toolbar}>
              <div className={styles.filters} role="group" aria-label={text.filter.label}>
                {(
                  [
                    ["all", text.filter.all, summaryData?.total ?? 0],
                    ["passed", text.filter.passed, summaryData?.passed ?? 0],
                    ["failed", text.filter.failed, summaryData?.failed ?? 0],
                  ] as Array<[Filter, string, number]>
                ).map(([key, label, count]) => (
                  <button
                    key={key}
                    type="button"
                    className={filter === key ? `${styles.filterButton} ${styles.filterActive}` : styles.filterButton}
                    aria-pressed={filter === key}
                    onClick={() => {
                      setFilter(key);
                      setPage(1);
                      track("match_filter", { page: "matching", filter: key });
                    }}
                  >
                    {label}
                    <span className={styles.filterCount}>{formatCount(count)}</span>
                  </button>
                ))}
              </div>
            </div>

            {lists.isError ? (
              <div className={styles.stateWrap}>
                <ErrorState
                  title={text.loadError}
                  detail={lists.error instanceof ApiError ? lists.error.message : text.loadErrorHint}
                  retryLabel={text.retry}
                  onRetry={() => void lists.refetch()}
                />
              </div>
            ) : (
              <>
                <DataTable
                  caption={text.title}
                  columns={columns}
                  rows={rows}
                  rowKey={(row) => row.id}
                  loading={lists.isPending}
                  skeletonRows={8}
                  empty={
                    <div className={styles.emptyWrap}>
                      {summaryData && summaryData.total > 0 && filter !== "all" ? (
                        <EmptyState
                          title={text.emptyFilter(filterLabel)}
                          action={
                            <Button
                              variant="secondary"
                              onClick={() => {
                                setFilter("all");
                                setPage(1);
                              }}
                            >
                              {text.filter.all}
                            </Button>
                          }
                        />
                      ) : (
                        <EmptyState
                          title={text.emptyJobTitle}
                          hint={text.emptyJobHint}
                          action={
                            canRun ? (
                              <Button variant="primary" onClick={() => run.mutate()}>
                                {text.run}
                              </Button>
                            ) : undefined
                          }
                        />
                      )}
                    </div>
                  }
                />
                {total > 0 ? (
                  <div className={styles.pagination}>
                    <Pagination
                      page={page}
                      pageSize={PAGE_SIZE}
                      total={total}
                      onChange={setPage}
                      label={text.totalLabel(total)}
                    />
                  </div>
                ) : null}
              </>
            )}
          </Panel>
        </>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title={text.confirmTitle}
        description={text.confirmHint(job?.name ?? "", summary.data?.total ?? 0)}
        confirmLabel={text.confirm}
        busy={run.isPending}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false);
          run.mutate();
        }}
      />
    </div>
  );
}
