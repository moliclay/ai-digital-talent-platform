import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Briefcase, CheckCircle2, Clock, FileText, ShieldX, Upload } from "lucide-react";

import { Panel } from "../components/ui/panel";
import { ScoreBar } from "../components/ui/score-bar";
import { DataTable, type Column } from "../components/ui/data-table";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { formatCount, formatDateTime, formatDuration, formatPercent, formatScore } from "../lib/format";
import { hasPermission } from "../lib/permission";
import styles from "./dashboard.module.css";

const text = copy.dashboard;

const KPI_ICONS = [FileText, CheckCircle2, Briefcase, Clock];

type Overview = {
  files: { total: number; by_status: Record<string, number> };
  parsed_total: number;
  queue: Record<string, number>;
  active_jobs: number;
  match: {
    job_profile_id: number | null;
    job_profile_name: string;
    passed: number;
    failed: number;
    avg_score: number;
  };
  recent_operations: Operation[];
};

type Operation = {
  id: number;
  username: string;
  module: string;
  action: string;
  status: string;
  duration_ms: number;
  created_at: string;
};

type ParseResult = {
  task_id: number | null;
  status: string;
  confidence?: number;
};

type MatchItem = {
  id: number;
  name: string;
  total_score: number;
  passed: boolean;
};

type StatusRow = { key: string; className: string };

function CountUp({ value }: { value: number }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setDisplay(value);
      return;
    }
    const raw = getComputedStyle(document.documentElement).getPropertyValue("--motion-count");
    const duration = Number.parseFloat(raw) || 900;
    const started = performance.now();
    let frame = 0;
    setDisplay(0);
    const tick = (now: number) => {
      const progress = Math.min(1, (now - started) / duration);
      const eased = 1 - (1 - progress) ** 4;
      setDisplay(Math.round(value * eased));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return <>{formatCount(display)}</>;
}

const STATUS_ROWS: StatusRow[] = [
  { key: "waiting", className: styles.waiting },
  { key: "parsing", className: styles.parsing },
  { key: "need_ocr", className: styles.needOcr },
  { key: "failed", className: styles.failed },
  { key: "completed", className: styles.completed },
];

export default function DashboardPage() {
  const { me } = useAuth();
  const navigate = useNavigate();
  const [parseNote, setParseNote] = useState<string | null>(null);

  useEffect(() => {
    track("page_view", { page: "dashboard" });
  }, []);

  const overview = useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: () => request<Overview>("/dashboard/overview"),
    staleTime: 30_000,
  });

  const data = overview.data;
  const jobId = data?.match.job_profile_id ?? null;
  const canCreate = hasPermission(me, "resume:create");
  const canViewMatch = hasPermission(me, "match:view");

  const job = useQuery({
    queryKey: ["job-profile", jobId],
    queryFn: () => request<{ passing_threshold: number }>(`/job-profiles/${jobId}`),
    enabled: jobId !== null && canViewMatch,
    staleTime: 60_000,
  });

  const parse = useMutation({
    mutationFn: () => request<ParseResult>("/resumes/parse-next", { method: "POST" }),
    onSuccess: (result) => {
      track("queue_process_result", {
        page: "dashboard",
        status: result.task_id ? result.status : "idle",
        confidence: result.confidence ?? null,
      });
      if (!result.task_id) {
        setParseNote(text.parseIdle);
      } else if (result.status === "completed") {
        setParseNote(text.parseDone(result.confidence ?? 0));
      } else {
        setParseNote(text.parseFailed);
      }
      void overview.refetch();
    },
    onError: (error) => {
      track("queue_process_result", { page: "dashboard", status: "error" });
      setParseNote(error instanceof Error ? `${text.parseError}${error.message}` : text.parseError);
    },
  });

  const topMatches = useQuery({
    queryKey: ["match-top", jobId],
    queryFn: () =>
      request<{ items: MatchItem[] }>(`/matching/lists?job_profile_id=${jobId}&page_size=3`),
    enabled: jobId !== null && canViewMatch,
    staleTime: 30_000,
  });

  if (overview.error instanceof ApiError && overview.error.status === 403) {
    return (
      <div className={styles.page}>
        <h1 className={styles.errorTitle}>{text.title}</h1>
        <EmptyState
          icon={<ShieldX size={20} strokeWidth={1.75} />}
          title={text.noPermissionTitle}
          hint={text.noPermissionHint}
        />
      </div>
    );
  }

  if (overview.isError) {
    return (
      <div className={styles.page}>
        <h1 className={styles.errorTitle}>{text.title}</h1>
        <div className={styles.errorWrap}>
          <ErrorState
            title={text.loadError}
            detail={overview.error instanceof ApiError ? overview.error.message : text.loadErrorHint}
            retryLabel={text.retry}
            onRetry={() => void overview.refetch()}
          />
        </div>
      </div>
    );
  }

  const loading = overview.isPending;
  const byStatus = data?.files.by_status ?? {};
  const total = data?.files.total ?? 0;
  const pending =
    (byStatus.waiting ?? 0) + (byStatus.parsing ?? 0) + (byStatus.need_ocr ?? 0);
  const failed = byStatus.failed ?? 0;
  const passed = data?.match.passed ?? 0;
  const failedMatch = data?.match.failed ?? 0;
  const hasMatch = Boolean(data?.match.job_profile_id);
  const avgScore = data?.match.avg_score ?? 0;
  const threshold = job.data?.passing_threshold ?? null;
  const gap = threshold === null ? "" : Math.abs(avgScore - threshold).toFixed(1);

  const showOps = Boolean(me && (me.user.roles.includes("admin") || me.user.roles.includes("hr")));

  const kpis = [
    { label: text.kpi.files, value: total, unit: "份", note: text.kpiNote.files },
    { label: text.kpi.parsed, value: data?.parsed_total ?? 0, unit: "份", note: text.kpiNote.parsed },
    { label: text.kpi.activeJobs, value: data?.active_jobs ?? 0, unit: "个", note: text.kpiNote.activeJobs },
    {
      label: text.kpi.pending,
      value: pending,
      unit: "份",
      note: failed > 0 ? text.kpiNote.pendingFailed(failed) : text.kpiNote.pendingClean,
    },
  ];

  function subtitle(): string {
    if (loading) return text.loading;
    if (total === 0) return canCreate ? text.sub.empty : text.sub.emptyNoPerm;
    if (pending > 0) {
      return hasMatch ? text.sub.queue(pending, passed, failedMatch) : text.sub.queueNoMatch(pending);
    }
    return hasMatch ? text.sub.clear(passed, failedMatch) : text.sub.clearNoMatch;
  }

  const maxCount = Math.max(1, ...STATUS_ROWS.map((row) => byStatus[row.key] ?? 0));

  const columns: Column<Operation>[] = [
    {
      key: "time",
      header: text.opsColumns.time,
      width: "calc(var(--space-5xl) * 2 + var(--space-lg))",
      render: (row) => <span className={styles.time}>{formatDateTime(row.created_at)}</span>,
    },
    {
      key: "username",
      header: text.opsColumns.user,
      render: (row) => row.username || text.opNoAccount,
    },
    {
      key: "module",
      header: text.opsColumns.module,
      render: (row) => row.module || copy.common.unknown,
    },
    {
      key: "action",
      header: text.opsColumns.action,
      render: (row) =>
        row.module === "认证" ? text.opAuthLogin : (text.opActions[row.action] ?? text.opOther),
    },
    {
      key: "status",
      header: text.opsColumns.status,
      render: (row) =>
        row.status === "success" ? (
          <Badge tone="success">{text.opSuccess}</Badge>
        ) : (
          <Badge tone="error">{text.opFailed}</Badge>
        ),
    },
    {
      key: "duration",
      header: text.opsColumns.duration,
      align: "right",
      width: "calc(var(--space-5xl) + var(--space-2xl) + var(--space-2xs))",
      render: (row) => formatDuration(row.duration_ms),
    },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div className={styles.headText}>
          <h1 className={styles.title}>{text.title}</h1>
          <p className={styles.sub}>{subtitle()}</p>
        </div>
        {canCreate ? (
          <Button
            variant="secondary"
            iconLeft={<Upload size={16} strokeWidth={1.75} aria-hidden="true" />}
            onClick={() => navigate("/resumes")}
          >
            {copy.resumes.upload}
          </Button>
        ) : null}
      </header>

      <div className={styles.stats}>
        {kpis.map((kpi, index) => {
          const Icon = KPI_ICONS[index];
          return (
            <article className={styles.statCard} key={kpi.label}>
              <span className={styles.statIcon} aria-hidden="true">
                <Icon size={18} strokeWidth={1.75} />
              </span>
              <p className={styles.statLabel}>{kpi.label}</p>
              <p className={styles.statValue}>
                {loading ? (
                  <Skeleton width="short" />
                ) : (
                  <>
                    <CountUp value={kpi.value} />
                    <span className={styles.statUnit}>{kpi.unit}</span>
                  </>
                )}
              </p>
              <p className={styles.statNote}>{kpi.note}</p>
            </article>
          );
        })}
      </div>

      <div className={canViewMatch ? styles.grid : styles.gridSingle}>
        <Panel
          title={text.queueTitle}
          meta={loading ? undefined : text.queueMeta(total)}
          className={styles.glassPanel}
        >
          {loading ? (
            <div className={styles.skeletonStack}>
              <Skeleton width="full" />
              <Skeleton width="wide" />
              <Skeleton width="full" />
              <Skeleton width="half" />
            </div>
          ) : total === 0 ? (
            <div className={styles.emptyWrap}>
              <EmptyState
                title={text.emptyQueueTitle}
                hint={canCreate ? text.emptyQueueHint : text.emptyQueueHintNoPerm}
                action={
                  canCreate ? (
                    <Button variant="secondary" onClick={() => navigate("/resumes")}>
                      {text.goResumes}
                    </Button>
                  ) : undefined
                }
              />
            </div>
          ) : (
            <>
              <div className={styles.queue}>
                {STATUS_ROWS.map((row) => {
                  const count = byStatus[row.key] ?? 0;
                  return (
                    <div className={`${styles.queueRow} ${row.className}`} key={row.key}>
                      <span className={styles.queueLabel}>{text.status[row.key]}</span>
                      <span className={styles.bar}>
                        <span
                          className={styles.barFill}
                          style={{ width: `${(count / maxCount) * 100}%` }}
                        />
                      </span>
                      <span className={styles.count}>{formatCount(count)}</span>
                    </div>
                  );
                })}
              </div>
              <div className={styles.queueFoot}>
                {canCreate ? (
                  <Button
                    variant="secondary"
                    loading={parse.isPending}
                    disabled={pending === 0}
                    onClick={() => {
                      setParseNote(null);
                      track("queue_process_click", { page: "dashboard", pending });
                      parse.mutate();
                    }}
                  >
                    {parse.isPending ? text.processing : text.processNext}
                  </Button>
                ) : null}
                <span className={styles.hint}>
                  {!canCreate
                    ? text.queueNoPermission
                    : parseNote ?? (pending === 0 ? text.parseIdle : text.queueHint)}
                </span>
              </div>
            </>
          )}
        </Panel>

        {canViewMatch ? (
          <Panel
            title={text.matchTitle}
            className={styles.glassPanel}
            meta={
              loading
                ? undefined
                : data?.match.job_profile_id
                  ? text.matchMeta(data.match.job_profile_name, passed + failedMatch)
                  : text.matchMetaEmpty
            }
            actions={
              hasMatch ? (
                <Button variant="ghost" onClick={() => navigate("/matching")}>
                  {text.matchLink}
                </Button>
              ) : undefined
            }
          >
          {loading ? (
            <div className={styles.skeletonStack}>
              <Skeleton width="short" height="title" />
              <Skeleton width="full" />
              <Skeleton width="half" />
            </div>
          ) : hasMatch ? (
            <div className={styles.matchBody}>
              <ScoreBar
                value={data?.match.avg_score ?? null}
                threshold={threshold}
                label={text.matchAvgLabel}
              />
              {threshold !== null ? (
                <p className={avgScore >= threshold ? styles.scoreGood : styles.scoreBad}>
                  {avgScore > threshold
                    ? text.matchAbove(Number(gap))
                    : avgScore < threshold
                      ? text.matchBelow(Number(gap))
                      : text.matchEqual}
                </p>
              ) : null}
              {job.isError ? <p className={styles.hint}>{text.thresholdUnknown}</p> : null}

              {canViewMatch ? (
                <div className={styles.topList}>
                  <div className={styles.topHead}>{text.matchTopTitle}</div>
                  {topMatches.isPending ? (
                    <div className={styles.topSkeleton}>
                      <Skeleton width="full" />
                      <Skeleton width="wide" />
                      <Skeleton width="half" />
                    </div>
                  ) : (topMatches.data?.items.length ?? 0) === 0 ? (
                    <p className={styles.hint}>{text.matchTopEmpty}</p>
                  ) : (
                    topMatches.data?.items.map((item) => (
                      <div className={styles.topRow} key={item.id}>
                        <span className={styles.topName}>{item.name}</span>
                        <Badge tone={item.passed ? "success" : "neutral"}>
                          {item.passed ? text.matchPassed : text.matchFailed}
                        </Badge>
                        <span className={styles.topScore}>{formatScore(item.total_score)}</span>
                      </div>
                    ))
                  )}
                </div>
              ) : null}

              <div className={styles.matchCounts}>
                <div>
                  <div className={styles.countValue}>{formatCount(passed)}</div>
                  <div className={styles.countLabel}>{text.matchPassed}</div>
                </div>
                <div>
                  <div className={styles.countValue}>{formatCount(failedMatch)}</div>
                  <div className={styles.countLabel}>{text.matchFailed}</div>
                </div>
                <div>
                  <div className={styles.countValue}>
                    {formatPercent(passed, passed + failedMatch)}
                    <span className={styles.countUnit}>%</span>
                  </div>
                  <div className={styles.countLabel}>{text.matchRate}</div>
                </div>
              </div>
            </div>
          ) : (
            <EmptyState title={text.matchEmptyTitle} hint={text.matchEmptyHint} />
          )}
        </Panel>
        ) : null}
      </div>

      {showOps ? (
        <Panel title={text.opsTitle} meta={text.opsMeta} className={styles.glassPanel} flush>
          <DataTable
            caption={text.opsTitle}
            columns={columns}
            rows={data?.recent_operations ?? []}
            rowKey={(row) => row.id}
            loading={loading}
            skeletonRows={4}
            empty={<p className={styles.tableEmpty}>{text.opsEmpty}</p>}
          />
        </Panel>
      ) : null}
    </div>
  );
}
