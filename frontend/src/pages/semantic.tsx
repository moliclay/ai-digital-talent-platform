import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Search, ShieldX } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { DataTable, type Column } from "../components/ui/data-table";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { FormField } from "../components/ui/form-field";
import { Input } from "../components/ui/input";
import { PageHeader } from "../components/ui/page-header";
import { Panel } from "../components/ui/panel";
import { Select } from "../components/ui/select";
import { Skeleton } from "../components/ui/skeleton";
import { ResumeBriefCell } from "../components/resume-brief-cell";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { formatCount } from "../lib/format";
import { hasPermission } from "../lib/permission";
import type { ResumeBrief, VectorStatus } from "../lib/api-types";
import styles from "./semantic.module.css";

const text = copy.semantic;

type Status = VectorStatus;

type SearchItem = ResumeBrief & {
  score: number;
};

type SearchResult = {
  available: boolean;
  query: string;
  items: SearchItem[];
  total: number;
  reason?: string;
};

type DuplicatePair = {
  similarity: number;
  a: ResumeBrief;
  b: ResumeBrief;
  a_name?: string;
  b_name?: string;
  a_id?: number;
  b_id?: number;
};

type DuplicateResult = {
  available: boolean;
  threshold: number;
  pairs: DuplicatePair[];
  total: number;
  reason?: string;
};

type Candidate = ResumeBrief & {
  similarity: number;
};

type CandidateResult = {
  available: boolean;
  job_id: number;
  job_name: string;
  items: Candidate[];
  reason?: string;
};

type RepairResult = {
  rebuilt: boolean;
  available: boolean;
  count?: number;
  expected?: number;
  indexed?: number;
  total?: number;
  reason?: string;
};

type BuildResult = {
  resumes: { indexed: number; total: number; available: boolean; reason?: string };
  jobs: { indexed: number; total: number; available: boolean; reason?: string };
  status: Status;
};

type Job = { id: number; name: string };

type PageData<T> = { items: T[]; total: number };

type TabKey = "search" | "duplicates" | "candidates";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "search", label: text.tabs.search },
  { key: "duplicates", label: text.tabs.duplicates },
  { key: "candidates", label: text.tabs.candidates },
];

const TOP_K = [
  { value: "5", label: "5" },
  { value: "10", label: "10" },
  { value: "20", label: "20" },
];

const THRESHOLDS = [
  { value: "0.93", label: text.thresholdStrict },
  { value: "0.9", label: text.thresholdHigh },
  { value: "0.8", label: text.thresholdMedium },
  { value: "0.7", label: text.thresholdLoose },
  { value: "0.5", label: text.thresholdLow },
];

function similarity(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function Availability({ ok }: { ok: boolean }) {
  return <Badge tone={ok ? "success" : "error"}>{ok ? text.available : text.unavailable}</Badge>;
}

export default function SemanticPage() {
  const { me } = useAuth();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState<TabKey>("search");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [repairNotice, setRepairNotice] = useState<{ tone: "ok" | "error"; message: string } | null>(null);
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [topK, setTopK] = useState("10");
  const [threshold, setThreshold] = useState("0.93");
  const [jobId, setJobId] = useState("");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const canView = hasPermission(me, "resume:view");
  const canBuild = hasPermission(me, "resume:create");

  useEffect(() => {
    track("page_view", { page: "semantic" });
  }, []);

  const status = useQuery({
    queryKey: ["vector-status"],
    queryFn: () => request<Status>("/vector/status"),
    enabled: canView,
  });

  const available = Boolean(status.data?.embed.available && status.data?.milvus.available);

  const jobs = useQuery({
    queryKey: ["semantic-jobs"],
    queryFn: () => request<PageData<Job>>("/job-profiles?page_size=200"),
    enabled: canView && available && tab === "candidates",
  });

  useEffect(() => {
    if (!jobs.data?.items.length) return;
    if (jobId && jobs.data.items.some((job) => String(job.id) === jobId)) return;
    setJobId(String(jobs.data.items[0].id));
  }, [jobs.data, jobId]);

  const search = useQuery({
    queryKey: ["semantic-search", submitted, topK],
    queryFn: () =>
      request<SearchResult>(`/resumes/semantic?q=${encodeURIComponent(submitted)}&top_k=${topK}`),
    enabled: canView && available && submitted.length > 0,
  });

  const duplicates = useQuery({
    queryKey: ["semantic-duplicates", threshold],
    queryFn: () => request<DuplicateResult>(`/resumes/duplicates?threshold=${threshold}`),
    enabled: canView && available && tab === "duplicates",
  });

  const candidates = useQuery({
    queryKey: ["semantic-candidates", jobId],
    queryFn: () => request<CandidateResult>(`/job-profiles/${jobId}/semantic-candidates?top_k=10`),
    enabled: canView && available && tab === "candidates" && jobId !== "",
  });

  const rebuild = useMutation({
    mutationFn: () => request<BuildResult>("/vector/index", { method: "POST", body: {} }),
    onSuccess: (data) => {
      queryClient.setQueryData(["vector-status"], data.status);
      void queryClient.invalidateQueries({ queryKey: ["semantic-search"] });
      void queryClient.invalidateQueries({ queryKey: ["semantic-duplicates"] });
      void queryClient.invalidateQueries({ queryKey: ["semantic-candidates"] });
    },
  });

  const repair = useMutation({
    mutationFn: () => request<RepairResult>("/vector/reindex-if-stale", { method: "POST", body: {} }),
    onSuccess: (data) => {
      setRepairNotice({
        tone: data.rebuilt ? "ok" : "ok",
        message: data.rebuilt
          ? text.repairDone(data.count ?? 0, data.expected ?? 0)
          : text.repairNoop,
      });
      void status.refetch();
      void queryClient.invalidateQueries({ queryKey: ["semantic-search"] });
      void queryClient.invalidateQueries({ queryKey: ["semantic-duplicates"] });
      void queryClient.invalidateQueries({ queryKey: ["semantic-candidates"] });
    },
    onError: (error) => {
      setRepairNotice({
        tone: "error",
        message: error instanceof ApiError ? error.message : text.repairFailed,
      });
    },
  });

  function openResume(id: number) {
    const next = new URLSearchParams(params);
    next.set("resume", String(id));
    setParams(next);
  }

  const jobOptions = useMemo(
    () => (jobs.data?.items ?? []).map((job) => ({ value: String(job.id), label: job.name })),
    [jobs.data],
  );

  if (!canView) {
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

  if (status.isError) {
    return (
      <div className={styles.page}>
        <div className={styles.pageHead}>
          <PageHeader title={text.title} sub={text.sub} />
        </div>
        <ErrorState
          title={text.loadError}
          detail={status.error instanceof ApiError ? status.error.message : text.loadErrorHint}
          retryLabel={text.retry}
          onRetry={() => void status.refetch()}
        />
      </div>
    );
  }

  function handleTabKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % TABS.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + TABS.length) % TABS.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = TABS.length - 1;
    else return;
    event.preventDefault();
    setTab(TABS[next].key);
    tabRefs.current[next]?.focus();
  }

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = q.trim();
    if (value) setSubmitted(value);
  }

  const searchColumns: Column<SearchItem>[] = [
    {
      key: "candidate",
      header: text.columns.candidate,
      render: (row) => <ResumeBriefCell brief={row} onOpen={openResume} />,
    },
    {
      key: "score",
      header: text.columns.similarity,
      align: "right",
      width: "calc(var(--space-5xl) + var(--space-lg))",
      render: (row) => <span className={styles.similarity}>{similarity(row.score)}</span>,
    },
  ];

  const duplicateColumns: Column<DuplicatePair>[] = [
    {
      key: "a",
      header: text.duplicateColumns.a,
      width: "calc(50% - var(--space-5xl))",
      render: (row) => <ResumeBriefCell brief={row.a} onOpen={openResume} />,
    },
    {
      key: "b",
      header: text.duplicateColumns.b,
      width: "calc(50% - var(--space-5xl))",
      render: (row) => <ResumeBriefCell brief={row.b} onOpen={openResume} />,
    },
    {
      key: "similarity",
      header: text.duplicateColumns.similarity,
      align: "right",
      width: "calc(var(--space-5xl) + var(--space-lg))",
      render: (row) => <span className={styles.similarity}>{similarity(row.similarity)}</span>,
    },
  ];

  const candidateColumns: Column<Candidate>[] = [
    {
      key: "candidate",
      header: text.columns.candidate,
      render: (row) => <ResumeBriefCell brief={row} onOpen={openResume} />,
    },
    {
      key: "similarity",
      header: text.columns.similarity,
      align: "right",
      width: "calc(var(--space-5xl) + var(--space-lg))",
      render: (row) => <span className={styles.similarity}>{similarity(row.similarity)}</span>,
    },
  ];

  const statusData = status.data;
  const stale = statusData?.milvus.stale === true;
  const expectedCount = statusData?.milvus.expected_count ?? statusData?.milvus.resume_count ?? 0;

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader title={text.title} sub={text.sub} />
      </div>

      <Panel
        title={text.statusTitle}
        meta={text.statusMeta}
        className={styles.glassPanel}
        actions={
          canBuild ? (
            <>
              {stale ? (
                <Button
                  variant="primary"
                  onClick={() => repair.mutate()}
                  loading={repair.isPending}
                  disabled={!available}
                >
                  {repair.isPending ? text.repairing : text.repair}
                </Button>
              ) : null}
              <Button onClick={() => setConfirmOpen(true)} disabled={!available} loading={rebuild.isPending}>
                {text.rebuild}
              </Button>
            </>
          ) : undefined
        }
      >
        {status.isPending || !statusData ? (
          <div className={styles.statusGrid}>
            <div className={styles.statusCell}><span className={styles.statusLabel}>{text.embed}</span><span className={styles.statusValue}><Skeleton width="short" /></span></div>
            <div className={styles.statusCell}><span className={styles.statusLabel}>{text.milvus}</span><span className={styles.statusValue}><Skeleton width="short" /></span></div>
            <div className={styles.statusCell}><span className={styles.statusLabel}>{text.resumeCount}</span><span className={styles.statusValue}><Skeleton width="short" /></span></div>
            <div className={styles.statusCell}><span className={styles.statusLabel}>{text.jobCount}</span><span className={styles.statusValue}><Skeleton width="short" /></span></div>
          </div>
        ) : (
          <dl className={styles.statusGrid}>
            <div className={styles.statusCell}>
              <dt className={styles.statusLabel}>{text.embed}</dt>
              <dd className={styles.statusValue}>
                <span>{statusData.embed.model}</span>
                <span className={styles.dim}>{statusData.embed.dim} 维</span>
                <Availability ok={statusData.embed.available} />
              </dd>
            </div>
            <div className={styles.statusCell}>
              <dt className={styles.statusLabel}>{text.milvus}</dt>
              <dd className={styles.statusValue}>
                <span className={styles.uri}>{statusData.milvus.uri}</span>
                <Availability ok={statusData.milvus.available} />
              </dd>
            </div>
            <div className={styles.statusCell}>
              <dt className={styles.statusLabel}>{text.resumeCount}</dt>
              <dd className={styles.statusValue}>
                <span className={styles.count}>{formatCount(statusData.milvus.resume_count)}</span>
                <span className={styles.dim}>{text.unit}</span>
              </dd>
            </div>
            <div className={styles.statusCell}>
              <dt className={styles.statusLabel}>{text.jobCount}</dt>
              <dd className={styles.statusValue}>
                <span className={styles.count}>{formatCount(statusData.milvus.job_count)}</span>
                <span className={styles.dim}>{text.unit}</span>
              </dd>
            </div>
          </dl>
        )}
        {statusData ? (
          <p className={stale ? styles.indexStale : styles.indexFresh}>
            {text.indexExpected(statusData.milvus.resume_count, expectedCount)}
            {" · "}
            {stale ? text.indexStale : text.indexFresh}
            {stale ? <span>{text.indexStaleHint}</span> : null}
          </p>
        ) : null}
        {repairNotice ? (
          <p className={repairNotice.tone === "ok" ? styles.buildResult : styles.buildError} role="status">
            {repairNotice.message}
          </p>
        ) : null}
        {rebuild.isSuccess ? (
          <p className={styles.buildResult}>
            {text.rebuildDone(rebuild.data.resumes.indexed, rebuild.data.jobs.indexed)}
          </p>
        ) : null}
        {rebuild.isError ? <p className={styles.buildError}>{text.rebuildFailed}</p> : null}
      </Panel>

      {!available && !status.isPending ? (
        <EmptyState
          icon={<AlertTriangle size={20} strokeWidth={1.75} />}
          title={text.statusUnavailable}
          hint={text.statusUnavailableHint}
        />
      ) : (
        <>
          <div className={styles.tabs} role="tablist" aria-label={text.title}>
            {TABS.map((item, index) => (
              <button
                key={item.key}
                ref={(element) => {
                  tabRefs.current[index] = element;
                }}
                type="button"
                role="tab"
                id={`semantic-tab-${item.key}`}
                aria-selected={tab === item.key}
                aria-controls={`semantic-panel-${item.key}`}
                tabIndex={tab === item.key ? 0 : -1}
                className={tab === item.key ? `${styles.tab} ${styles.tabActive}` : styles.tab}
                onClick={() => setTab(item.key)}
                onKeyDown={(event) => handleTabKey(event, index)}
              >
                {item.label}
              </button>
            ))}
          </div>

          {tab === "search" ? (
            <div role="tabpanel" id="semantic-panel-search" aria-labelledby="semantic-tab-search" tabIndex={0}>
              <Panel
                title={text.searchPanelTitle}
                meta={search.data ? `${search.data.total} 条` : text.searchHint(Number(topK))}
                className={styles.glassTable}
                flush
              >
                <form className={styles.searchBar} onSubmit={handleSearch}>
                  <FormField id="semantic-q" label={text.searchLabel} className={styles.grow}>
                    <Input
                      value={q}
                      placeholder={text.searchPlaceholder}
                      onChange={(event) => setQ(event.target.value)}
                    />
                  </FormField>
                  <FormField id="semantic-k" label={text.topK} className={styles.topK}>
                    <Select id="semantic-k" value={topK} options={TOP_K} onChange={setTopK} ariaLabel={text.topK} />
                  </FormField>
                  <Button type="submit" variant="primary" iconLeft={<Search size={16} strokeWidth={1.75} />} disabled={!q.trim()}>
                    {text.searchAction}
                  </Button>
                </form>

                {submitted === "" ? (
                  <div className={styles.initialWrap}>
                    <EmptyState
                      icon={<Search size={20} strokeWidth={1.75} />}
                      title={text.searchInitial}
                      hint={text.searchHint(Number(topK))}
                    />
                  </div>
                ) : search.isError ? (
                  <div className={styles.stateWrap}>
                    <ErrorState
                      title={text.loadError}
                      detail={search.error instanceof ApiError ? search.error.message : text.loadErrorHint}
                      retryLabel={text.retry}
                      onRetry={() => void search.refetch()}
                    />
                  </div>
                ) : (
                  <DataTable
                    caption={text.tabs.search}
                    columns={searchColumns}
                    rows={search.data?.items ?? []}
                    rowKey={(row) => row.parsed_resume_id}
                    loading={search.isPending}
                    skeletonRows={4}
                    empty={
                      <div className={styles.emptyWrap}>
                        <EmptyState title={text.searchEmpty} hint={text.searchEmptyHint} />
                      </div>
                    }
                  />
                )}
              </Panel>
            </div>
          ) : null}

          {tab === "duplicates" ? (
            <div role="tabpanel" id="semantic-panel-duplicates" aria-labelledby="semantic-tab-duplicates" tabIndex={0}>
              <Panel
                title={text.duplicateTitle}
                meta={text.duplicateHint}
                className={styles.glassTable}
                actions={
                <FormField id="semantic-threshold" label={text.threshold} className={styles.threshold}>
                  <Select
                    id="semantic-threshold"
                    value={threshold}
                    options={THRESHOLDS}
                    onChange={setThreshold}
                    ariaLabel={text.threshold}
                  />
                </FormField>
              } flush>
                {duplicates.isError ? (
                  <div className={styles.stateWrap}>
                    <ErrorState
                      title={text.loadError}
                      detail={duplicates.error instanceof ApiError ? duplicates.error.message : text.loadErrorHint}
                      retryLabel={text.retry}
                      onRetry={() => void duplicates.refetch()}
                    />
                  </div>
                ) : (
                  <>
                    <DataTable
                      caption={text.duplicateTitle}
                      columns={duplicateColumns}
                      rows={duplicates.data?.pairs ?? []}
                      rowKey={(row) => `${row.a.parsed_resume_id}-${row.b.parsed_resume_id}`}
                      loading={duplicates.isPending}
                      skeletonRows={4}
                      empty={
                        <div className={styles.emptyWrap}>
                          <EmptyState title={text.duplicatesEmpty} hint={text.duplicatesEmptyHint} />
                        </div>
                      }
                    />
                    <p className={styles.note}>{text.duplicateNote}</p>
                  </>
                )}
              </Panel>
            </div>
          ) : null}

          {tab === "candidates" ? (
            <div role="tabpanel" id="semantic-panel-candidates" aria-labelledby="semantic-tab-candidates" tabIndex={0}>
              <Panel
                title={text.tabs.candidates}
                meta={text.candidatesHint}
                className={styles.glassTable}
                actions={
                  jobOptions.length ? (
                    <FormField id="semantic-job" label={text.candidatesJob} className={styles.jobSelect}>
                      <Select
                        id="semantic-job"
                        value={jobId}
                        options={jobOptions}
                        onChange={setJobId}
                        ariaLabel={text.candidatesJob}
                      />
                    </FormField>
                  ) : undefined
                }
                flush
              >
                {!jobId ? (
                  <div className={styles.initialWrap}>
                    <EmptyState title={text.candidatesInitial} />
                  </div>
                ) : candidates.isError ? (
                  <div className={styles.stateWrap}>
                    <ErrorState
                      title={text.loadError}
                      detail={candidates.error instanceof ApiError ? candidates.error.message : text.loadErrorHint}
                      retryLabel={text.retry}
                      onRetry={() => void candidates.refetch()}
                    />
                  </div>
                ) : (
                  <DataTable
                    caption={text.tabs.candidates}
                    columns={candidateColumns}
                    rows={candidates.data?.items ?? []}
                    rowKey={(row) => row.parsed_resume_id}
                    loading={candidates.isPending}
                    skeletonRows={5}
                    empty={
                      <div className={styles.emptyWrap}>
                        <EmptyState title={text.candidatesEmpty} />
                      </div>
                    }
                  />
                )}
              </Panel>
            </div>
          ) : null}
        </>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title={text.rebuildConfirmTitle}
        description={
          <>
            {text.rebuildConfirmBody}
            <br />
            {text.rebuildAppendNote}
          </>
        }
        confirmLabel={text.rebuild}
        busy={rebuild.isPending}
        onConfirm={() => {
          setConfirmOpen(false);
          rebuild.mutate();
        }}
        onClose={() => setConfirmOpen(false)}
      />
    </div>
  );
}
