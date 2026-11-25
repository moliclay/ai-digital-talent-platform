import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ShieldX } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { DataTable, type Column } from "../components/ui/data-table";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { Input } from "../components/ui/input";
import { PageHeader } from "../components/ui/page-header";
import { Pagination } from "../components/ui/pagination";
import { Panel } from "../components/ui/panel";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { formatDateTime } from "../lib/format";
import { hasPermission } from "../lib/permission";
import { EditorDialog } from "./job-profiles/editor-dialog";
import { TrialDialog } from "./job-profiles/trial-dialog";
import type { JobProfile, PageData } from "./job-profiles/types";
import styles from "./job-profiles.module.css";

const text = copy.jobProfiles;
const editorText = text.editor;
const PAGE_SIZE = 20;
const WEIGHT_KEYS = ["education", "skills", "experience", "project", "other"];

function conditionText(condition: JobProfile["conditions"][number]): string {
  const value = Array.isArray(condition.value) ? condition.value.join("、") : String(condition.value ?? "");
  return `${condition.key} ${text.ops[condition.op] ?? condition.op} ${value}`;
}

export default function JobProfilesPage() {
  const { me } = useAuth();
  const [draft, setDraft] = useState("");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorJobId, setEditorJobId] = useState<number | null>(null);
  const [trialJob, setTrialJob] = useState<JobProfile | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<JobProfile | null>(null);
  const [banner, setBanner] = useState<{ tone: "ok" | "error"; message: string } | null>(null);

  const canCreate = hasPermission(me, "job:create");
  const canEdit = hasPermission(me, "job:edit");
  const canDelete = hasPermission(me, "job:delete");

  useEffect(() => {
    track("page_view", { page: "job-profiles" });
  }, []);

  const list = useQuery({
    queryKey: ["job-profiles", keyword, page],
    queryFn: () =>
      request<PageData<JobProfile>>(
        `/job-profiles?keyword=${encodeURIComponent(keyword)}&page=${page}&page_size=${PAGE_SIZE}`,
      ),
    staleTime: 20_000,
  });

  const remove = useMutation({
    mutationFn: (id: number) => request<{ deleted: number }>(`/job-profiles/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      setBanner({ tone: "ok", message: text.remove.done });
      setDeleteTarget(null);
      track("job_deleted", { page: "job-profiles" });
      void list.refetch();
    },
    onError: (error) => {
      setBanner({
        tone: "error",
        message: error instanceof ApiError ? `${text.remove.error}${error.message}` : text.remove.error,
      });
    },
  });

  if (list.error instanceof ApiError && list.error.status === 403) {
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

  const rows = list.data?.items ?? [];
  const total = list.data?.total ?? 0;
  const hasFilters = Boolean(keyword);
  const from = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(page * PAGE_SIZE, total);

  function openCreate() {
    setEditorJobId(null);
    setEditorOpen(true);
    track("job_editor_open", { page: "job-profiles", mode: "create" });
  }

  function openEdit(job: JobProfile) {
    setEditorJobId(job.id);
    setEditorOpen(true);
    track("job_editor_open", { page: "job-profiles", mode: "edit" });
  }

  const columns: Column<JobProfile>[] = [
    {
      key: "name",
      header: text.columns.name,
      width: "calc(var(--space-5xl) * 3 + var(--space-xs))",
      render: (job) =>
        canEdit ? (
          <button type="button" className={styles.jobName} title={job.name} onClick={() => openEdit(job)}>
            {job.name}
          </button>
        ) : (
          <span className={styles.jobName} title={job.name}>
            {job.name}
          </span>
        ),
    },
    {
      key: "conditions",
      header: text.columns.conditions,
      render: (job) => {
        if ((job.conditions ?? []).length === 0) return copy.common.empty;
        const all = job.conditions.map(conditionText);
        return (
          <span className={styles.ellipsis} title={all.join("；")}>
            {all[0]}
            {all.length > 1 ? ` ${text.conditionMore(all.length - 1)}` : ""}
          </span>
        );
      },
    },
    {
      key: "weights",
      header: text.columns.weights,
      width: "calc(var(--space-5xl) * 2 + var(--space-xl))",
      hideOnTablet: true,
      render: (job) => {
        const weights = WEIGHT_KEYS.map((key) => Math.max(0, Number(job.score_rules?.weights?.[key] ?? 0)));
        const sum = weights.reduce((acc, value) => acc + value, 0);
        if (sum <= 0) return copy.common.empty;
        const topIndex = weights.indexOf(Math.max(...weights));
        const title = WEIGHT_KEYS.map(
          (key, index) => `${text.weights[key]} ${Math.round((weights[index] / sum) * 100)}%`,
        ).join(" · ");
        const topText = text.weightTop(
          text.weights[WEIGHT_KEYS[topIndex]],
          Math.round((weights[topIndex] / sum) * 100),
        );
        return (
          <div className={styles.weights} title={title}>
            <span className={styles.weightBar} aria-hidden="true">
              {weights.map((weight, index) => (
                <span
                  key={WEIGHT_KEYS[index]}
                  className={styles.weightFill}
                  style={{ flexGrow: weight }}
                />
              ))}
            </span>
            <span className={styles.weightText} title={title}>
              {topText} · {text.weightMore}
            </span>
          </div>
        );
      },
    },
    {
      key: "threshold",
      header: text.columns.threshold,
      align: "right",
      width: "calc(var(--space-5xl) + var(--space-md))",
      render: (job) => `${job.passing_threshold} 分`,
    },
    {
      key: "status",
      header: text.columns.status,
      width: "calc(var(--space-5xl) + var(--space-md))",
      hideOnTablet: true,
      render: (job) =>
        job.status === "active" ? (
          <Badge tone="success">{text.statusActive}</Badge>
        ) : (
          <Badge tone="neutral">{job.status}</Badge>
        ),
    },
    {
      key: "created",
      header: text.columns.created,
      width: "calc(var(--space-5xl) * 2 + var(--space-sm))",
      hideOnTablet: true,
      render: (job) => <span className={styles.time}>{formatDateTime(job.created_at)}</span>,
    },
  ];

  if (canEdit || canDelete) {
    columns.push({
      key: "actions",
      header: text.columns.actions,
      width: "calc(var(--space-5xl) * 3 + var(--space-md))",
      hideOnTablet: true,
      render: (job) => (
        <div className={styles.actions}>
          {canEdit ? (
            <>
              <Button variant="ghost" onClick={() => {
                setTrialJob(job);
                track("job_trial_open", { page: "job-profiles" });
              }}>
                {text.trial.action}
              </Button>
              <Button variant="ghost" onClick={() => openEdit(job)}>
                {text.editAction}
              </Button>
            </>
          ) : null}
          {canDelete ? (
            <Button variant="ghost" onClick={() => setDeleteTarget(job)}>
              {text.remove.action}
            </Button>
          ) : null}
        </div>
      ),
    });
  }

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader
          title={text.title}
          sub={text.sub}
          actions={
            canCreate ? (
              <Button variant="primary" onClick={openCreate}>
                {text.create}
              </Button>
            ) : undefined
          }
        />
      </div>

      {banner ? (
        <p className={banner.tone === "ok" ? styles.bannerOk : styles.bannerError} role="status">
          {banner.message}
        </p>
      ) : null}

      <Panel
        title={text.listTitle}
        meta={list.isPending || list.isError ? undefined : hasFilters ? text.filteredTotal(total) : text.total(total)}
        className={styles.glassTable}
        flush
      >
        <div className={styles.toolbar}>
          <div className={styles.search}>
            <Input
              value={draft}
              placeholder={text.searchPlaceholder}
              aria-label={text.searchPlaceholder}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  setPage(1);
                  setKeyword(draft.trim());
                }
              }}
            />
            <Button
              variant="secondary"
              onClick={() => {
                setPage(1);
                setKeyword(draft.trim());
              }}
            >
              {text.search}
            </Button>
          </div>
          {hasFilters ? (
            <Button
              variant="ghost"
              onClick={() => {
                setDraft("");
                setKeyword("");
                setPage(1);
              }}
            >
              {text.clear}
            </Button>
          ) : null}
        </div>

        {list.isError ? (
          <div className={styles.stateWrap}>
            <ErrorState
              title={text.loadError}
              detail={list.error instanceof ApiError ? list.error.message : text.loadErrorHint}
              retryLabel={text.retry}
              onRetry={() => void list.refetch()}
            />
          </div>
        ) : (
          <>
            <DataTable
              caption={text.title}
              columns={columns}
              rows={rows}
              rowKey={(job) => job.id}
              loading={list.isPending}
              skeletonRows={6}
              empty={
                <div className={styles.emptyWrap}>
                  <EmptyState
                    title={hasFilters ? text.emptyFilteredTitle : text.emptyTitle}
                    hint={hasFilters ? text.emptyFilteredHint : text.emptyHint}
                    action={
                      hasFilters ? (
                        <Button
                          variant="secondary"
                          onClick={() => {
                            setDraft("");
                            setKeyword("");
                            setPage(1);
                          }}
                        >
                          {text.clear}
                        </Button>
                      ) : canCreate ? (
                        <Button variant="primary" onClick={openCreate}>
                          {text.create}
                        </Button>
                      ) : undefined
                    }
                  />
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
                  label={text.pageRange(from, to, total)}
                />
              </div>
            ) : null}
          </>
        )}
      </Panel>

      <EditorDialog
        open={editorOpen}
        jobId={editorJobId}
        onClose={() => setEditorOpen(false)}
        onSaved={() => {
          setBanner({ tone: "ok", message: editorText.saved });
          track("job_saved", { page: "job-profiles", mode: editorJobId === null ? "create" : "edit" });
          void list.refetch();
        }}
      />

      <TrialDialog open={trialJob !== null} job={trialJob} onClose={() => setTrialJob(null)} />

      <ConfirmDialog
        open={deleteTarget !== null}
        title={text.remove.title}
        description={deleteTarget ? text.remove.hint(deleteTarget.name) : undefined}
        confirmLabel={text.remove.confirm}
        tone="destructive"
        busy={remove.isPending}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) remove.mutate(deleteTarget.id);
        }}
      />
    </div>
  );
}
