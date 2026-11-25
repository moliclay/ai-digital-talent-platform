import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ShieldX } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { DataTable, type Column } from "../components/ui/data-table";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { FormField } from "../components/ui/form-field";
import { Input } from "../components/ui/input";
import { Modal } from "../components/ui/modal";
import { PageHeader } from "../components/ui/page-header";
import { Pagination } from "../components/ui/pagination";
import { Panel } from "../components/ui/panel";
import { Select } from "../components/ui/select";
import { Switch } from "../components/ui/switch";
import { ExamStateBadge } from "../components/exam-state-badge";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { formatCount, formatDateTime } from "../lib/format";
import { hasPermission } from "../lib/permission";
import { QueueDrawer } from "./resumes/queue-drawer";
import { UploadDialog } from "./resumes/upload-dialog";
import type { PageData, QueueData, QueueTask, ResumeRow, SuspectedResult } from "./resumes/types";
import styles from "./resumes.module.css";

const text = copy.resumes;
const PAGE_SIZE = 20;

const EDUCATION_OPTIONS = [
  { value: "", label: text.educationAll },
  { value: "博士", label: "博士" },
  { value: "硕士", label: "硕士" },
  { value: "本科", label: "本科" },
  { value: "大专", label: "大专" },
  { value: "高中", label: "高中" },
];

function statusTone(status: string) {
  if (status === "completed") return "success" as const;
  if (status === "failed") return "error" as const;
  if (status === "need_ocr") return "warning" as const;
  if (status === "parsing") return "info" as const;
  return "neutral" as const;
}

export default function ResumesPage() {
  const { me } = useAuth();
  const [draft, setDraft] = useState("");
  const [keyword, setKeyword] = useState("");
  const [education, setEducation] = useState("");
  const [page, setPage] = useState(1);
  const [suspectedOpen, setSuspectedOpen] = useState(false);
  const [reconcileOpen, setReconcileOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [queueOpen, setQueueOpen] = useState(false);
  const [params, setParams] = useSearchParams();
  const history = params.get("history") === "1";
  const setHistory = (checked: boolean) => {
    const next = new URLSearchParams(params);
    if (checked) next.set("history", "1");
    else next.delete("history");
    setParams(next);
    setPage(1);
  };
  const [banner, setBanner] = useState<{ tone: "ok" | "error"; message: string } | null>(null);

  const canCreate = hasPermission(me, "resume:create");
  const canDelete = hasPermission(me, "resume:delete");
  const canViewJobs = hasPermission(me, "job:view");
  const canEdit = hasPermission(me, "resume:edit");

  useEffect(() => {
    track("page_view", { page: "resumes" });
  }, []);

  const list = useQuery({
    queryKey: ["resumes", keyword, education, page, history],
    queryFn: () =>
      request<PageData<ResumeRow>>(
        `/resumes?keyword=${encodeURIComponent(keyword)}&education=${encodeURIComponent(education)}&page=${page}&page_size=${PAGE_SIZE}&include_superseded=${history ? 1 : 0}`,
      ),
    staleTime: 20_000,
  });

  const suspected = useQuery({
    queryKey: ["resume-suspected"],
    queryFn: () => request<SuspectedResult>("/resumes/identity/suspected"),
    staleTime: 60_000,
  });

  const queue = useQuery({
    queryKey: ["resume-queue"],
    queryFn: () => request<QueueData>("/resumes/queue"),
    staleTime: 10_000,
  });

  const parse = useMutation({
    mutationFn: () =>
      request<{ task_id: number | null; status: string }>("/resumes/parse-next", { method: "POST" }),
    onSuccess: (result) => {
      track("queue_process_result", {
        page: "resumes",
        status: result.task_id ? result.status : "idle",
      });
      if (!result.task_id) {
        setBanner({ tone: "ok", message: text.queueEmpty });
      } else if (result.status === "completed") {
        setBanner({ tone: "ok", message: text.parseDone });
      } else {
        setBanner({ tone: "error", message: text.parseFailed });
      }
      void list.refetch();
      void queue.refetch();
    },
    onError: (error) => {
      setBanner({
        tone: "error",
        message: error instanceof ApiError ? error.message : text.uploadError,
      });
    },
  });

  const remove = useMutation({
    mutationFn: (taskId: number) =>
      request<{ deleted: number }>(`/resumes/queue/${taskId}`, { method: "DELETE" }),
    onSuccess: () => {
      setBanner({ tone: "ok", message: text.removeDone });
      void queue.refetch();
    },
    onError: (error) => {
      setBanner({
        tone: "error",
        message: error instanceof ApiError ? error.message : text.saveError,
      });
    },
  });

  const reconcile = useMutation({
    mutationFn: () =>
      request<{ total: number; keyed: number; unkeyed: number; superseded: number }>(
        "/resumes/identity/reconcile",
        { method: "POST", body: {} },
      ),
    onSuccess: (result) => {
      setReconcileOpen(false);
      setBanner({
        tone: "ok",
        message: text.suspected.reconcileDone(result.total, result.superseded),
      });
      void list.refetch();
      void suspected.refetch();
    },
    onError: (error) => {
      setReconcileOpen(false);
      setBanner({
        tone: "error",
        message: error instanceof ApiError ? error.message : text.loadErrorHint,
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

  const rawResume = params.get("resume");
  const selectedId = rawResume && /^\d+$/.test(rawResume) ? Number(rawResume) : null;
  const openResume = (id: number) => {
    const next = new URLSearchParams(params);
    next.set("resume", String(id));
    setParams(next);
  };
  const rows = list.data?.items ?? [];
  const total = list.data?.total ?? 0;
  const counts = queue.data?.counts ?? {};
  const pending =
    (counts.waiting ?? 0) + (counts.parsing ?? 0) + (counts.need_ocr ?? 0) + (counts.failed ?? 0);
  const queueTotal =
    (counts.waiting ?? 0) +
    (counts.parsing ?? 0) +
    (counts.need_ocr ?? 0) +
    (counts.failed ?? 0) +
    (counts.completed ?? 0);
  const completionRate = queueTotal === 0 ? 0 : Math.round(((counts.completed ?? 0) / queueTotal) * 100);
  const hasFilters = Boolean(keyword || education);
  const from = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(page * PAGE_SIZE, total);

  const columns: Column<ResumeRow>[] = [
    {
      key: "name",
      header: text.columns.name,
      width: "calc(var(--space-5xl) * 1.5)",
      render: (row) => (
        <div className={styles.nameCell}>
          <button
            type="button"
            className={styles.nameButton}
            title={row.is_current === false ? text.badges.superseded : undefined}
            onClick={() => {
              const target = row.is_current === false && row.superseded_by ? row.superseded_by : row.id;
              openResume(target);
              track("resume_open", { page: "resumes" });
            }}
          >
            {row.name || copy.common.unknown}
          </button>
          <span className={styles.nameBadges}>
            {row.employee_user_id ? <Badge tone="info">{text.badges.employee}</Badge> : null}
            {row.is_current === false ? <Badge tone="neutral">{text.badges.superseded}</Badge> : null}
          </span>
        </div>
      ),
    },
    {
      key: "education",
      header: text.columns.education,
      width: "var(--space-5xl)",
      render: (row) => row.education || copy.common.unknown,
    },
    {
      key: "major",
      header: text.columns.major,
      width: "calc(var(--space-5xl) + var(--space-2xl))",
      hideOnTablet: true,
      render: (row) => <span className={styles.ellipsis} title={row.major}>{row.major || copy.common.unknown}</span>,
    },
    {
      key: "years",
      header: text.columns.years,
      align: "right",
      width: "calc(var(--space-5xl) + var(--space-md))",
      render: (row) => text.years(row.years_experience ?? 0),
    },
    {
      key: "skills",
      header: text.columns.skills,
      render: (row) => {
        const skills = row.skills ?? [];
        if (skills.length === 0) return copy.common.empty;
        const head = skills.slice(0, 3).join("、");
        return (
          <span className={styles.ellipsis} title={skills.join("、")}>
            {head}
            {skills.length > 3 ? ` ${text.skillsMore(skills.length - 3)}` : ""}
          </span>
        );
      },
    },
    {
      key: "status",
      header: text.columns.status,
      width: "calc(var(--space-5xl) + var(--space-2xl))",
      render: (row) => (
        <Badge tone={statusTone(row.status)}>{text.status[row.status] ?? row.status}</Badge>
      ),
    },
    {
      key: "exam",
      header: text.columns.exam,
      width: "calc(var(--space-5xl) + var(--space-2xl))",
      render: (row) => {
        const summary = row.exam_summary;
        if (!summary) return <span className={styles.muted}>{copy.common.empty}</span>;
        const detail = summary.items
          .map((item) => `${item.exam_name}${item.score === null ? "" : ` ${item.score}/${item.max_score ?? 0}`}`)
          .join("；");
        return (
          <span className={styles.examCell} title={detail || undefined}>
            <ExamStateBadge state={summary.state} label={summary.label} />
            {summary.total > 1 ? <span className={styles.examCount}>{summary.passed}/{summary.total}</span> : null}
          </span>
        );
      },
    },
    {
      key: "confidence",
      header: text.columns.confidence,
      align: "right",
      width: "calc(var(--space-5xl) + var(--space-xs))",
      hideOnTablet: true,
      render: (row) =>
        row.confidence === null || row.confidence === undefined
          ? copy.common.empty
          : `${Math.round(row.confidence * 100)}%`,
    },
    {
      key: "file",
      header: text.columns.file,
      width: "calc(var(--space-5xl) * 2 + var(--space-2xl))",
      hideOnTablet: true,
      render: (row) => (
        <span className={styles.ellipsis} title={row.filename}>
          {row.filename || copy.common.unknown}
        </span>
      ),
    },
    {
      key: "created",
      header: text.columns.created,
      width: "calc(var(--space-5xl) * 2 + var(--space-md))",
      hideOnTablet: true,
      render: (row) => <span className={styles.time}>{formatDateTime(row.created_at)}</span>,
    },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader
          title={text.title}
          sub={text.sub}
          actions={
            canCreate ? (
              <Button variant="primary" onClick={() => setUploadOpen(true)}>
                {text.upload}
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

      {suspected.data && suspected.data.total > 0 ? (
        <div className={styles.suspectedBanner} role="status">
          <AlertTriangle size={18} strokeWidth={1.75} aria-hidden="true" />
          <div className={styles.suspectedText}>
            <strong>{text.suspected.title(suspected.data.total)}</strong>
            <span>{text.suspected.hint}</span>
          </div>
          <Button variant="secondary" onClick={() => setSuspectedOpen(true)}>
            {text.suspected.view}
          </Button>
        </div>
      ) : null}

      <section className={styles.overview}>
        <div className={styles.overviewMain}>
          <p className={styles.overviewLabel}>{text.summary.label}</p>
          <p className={styles.overviewValue}>
            {list.isError ? (
              "暂无"
            ) : (
              <>
                {formatCount(total)}
                <span className={styles.overviewUnit}>份</span>
              </>
            )}
          </p>
          <p className={styles.overviewNote}>
            {list.isError
              ? text.summary.unavailable
              : hasFilters
                ? text.summary.noteFiltered
                : text.summary.noteAll}
          </p>
        </div>
        <dl className={styles.overviewStats}>
          <div className={styles.overviewStat}>
            <dt>{text.summary.parsed}</dt>
            <dd>{formatCount(counts.completed ?? 0)}</dd>
          </div>
          <div className={styles.overviewStat}>
            <dt>{text.summary.pending}</dt>
            <dd>{formatCount(pending)}</dd>
          </div>
          <div className={styles.overviewStat}>
            <dt>{text.summary.failed}</dt>
            <dd>{formatCount(counts.failed ?? 0)}</dd>
          </div>
          <div className={styles.overviewStat}>
            <dt>{text.summary.completion}</dt>
            <dd>{completionRate}%</dd>
          </div>
        </dl>
        <Button variant="secondary" onClick={() => setQueueOpen(true)}>
          {text.summary.queueAction}
        </Button>
      </section>

      <Panel
        title={text.listTitle}
        meta={list.isPending || list.isError ? undefined : hasFilters ? text.filteredTotal(total) : text.total(total)}
        className={styles.glassTable}
        flush
      >
        <div className={styles.toolbar}>
          <div className={styles.search}>
            <FormField id="resume-keyword" label={text.searchLabel} className={styles.searchField}>
              <Input
                value={draft}
                placeholder={text.searchPlaceholder}
                aria-label={text.searchLabel}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    setPage(1);
                    setKeyword(draft.trim());
                    track("resume_search", { page: "resumes", hasKeyword: Boolean(draft.trim()) });
                  }
                }}
              />
            </FormField>
            <Button
              variant="secondary"
              size="lg"
              onClick={() => {
                setPage(1);
                setKeyword(draft.trim());
              }}
            >
              {text.search}
            </Button>
          </div>
          <div className={styles.filter}>
            <FormField id="resume-education" label={text.educationLabel}>
              <Select
                id="resume-education"
                value={education}
                options={EDUCATION_OPTIONS}
                onChange={(value) => {
                  setEducation(value);
                  setPage(1);
                }}
                ariaLabel={text.educationLabel}
              />
            </FormField>
          </div>
          <div className={styles.historyToggle}>
            <Switch
              checked={history}
              label={text.historyLabel}
              hint={text.historyHint}
              onChange={(checked) => {
                setHistory(checked);
                setPage(1);
              }}
            />
          </div>
          {hasFilters ? (
            <Button
              variant="ghost"
              onClick={() => {
                setDraft("");
                setKeyword("");
                setEducation("");
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
              rowKey={(row) => row.id}
              loading={list.isPending}
              skeletonRows={8}
              selectedKey={selectedId}
              rowClassName={(row) => (row.is_current === false ? styles.oldRow : "")}
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
                            setEducation("");
                            setPage(1);
                          }}
                        >
                          {text.clearFilters}
                        </Button>
                      ) : canCreate ? (
                        <Button variant="primary" onClick={() => setUploadOpen(true)}>
                          {text.upload}
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

      <Modal
        open={suspectedOpen}
        onClose={() => setSuspectedOpen(false)}
        title={text.suspected.modalTitle}
        size="md"
        footer={
          <>
            {canEdit ? (
              <Button variant="ghost" onClick={() => setReconcileOpen(true)}>
                {text.suspected.reconcile}
              </Button>
            ) : null}
            <Button variant="secondary" onClick={() => setSuspectedOpen(false)}>{copy.common.close}</Button>
          </>
        }
      >
        <div className={styles.suspectedGroups}>
          {(suspected.data?.groups ?? []).map((group) => (
            <section className={styles.suspectedGroup} key={group.ids.join("-")}>
              <div className={styles.suspectedGroupHead}>
                <strong>{group.names[0] || copy.common.unknown}</strong>
                <span className={styles.muted}>{text.suspected.groupMeta(group.education, group.major)}</span>
              </div>
              <p className={styles.suspectedReason}>{group.reason}</p>
              <div className={styles.suspectedActions}>
                {group.ids.map((id) => (
                  <Button key={id} variant="ghost" onClick={() => openResume(id)}>
                    #{id} {text.suspected.open}
                  </Button>
                ))}
              </div>
            </section>
          ))}
          <p className={styles.muted}>{text.suspected.note}</p>
        </div>
      </Modal>

      <ConfirmDialog
        open={reconcileOpen}
        title={text.suspected.reconcileTitle}
        description={text.suspected.reconcileBody}
        confirmLabel={text.suspected.reconcileConfirm}
        busy={reconcile.isPending}
        onConfirm={() => reconcile.mutate()}
        onClose={() => setReconcileOpen(false)}
      />

      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        canViewJobs={canViewJobs}
        onUploaded={(accepted) => {
          setBanner({ tone: "ok", message: text.uploadDone(accepted) });
          track("resume_uploaded", { page: "resumes", accepted });
          void list.refetch();
          void queue.refetch();
        }}
      />

      <QueueDrawer
        open={queueOpen}
        onClose={() => setQueueOpen(false)}
        data={queue.data}
        loading={queue.isPending}
        error={queue.isError}
        onRetry={() => void queue.refetch()}
        pending={pending}
        canProcess={canCreate}
        processing={parse.isPending}
        onProcess={() => parse.mutate()}
        canDelete={canDelete}
        removingId={remove.isPending ? (remove.variables ?? null) : null}
        onRemove={(task: QueueTask) => remove.mutate(task.task_id)}
      />

    </div>
  );
}
