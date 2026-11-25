import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldX } from "lucide-react";

import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { DataTable, type Column } from "../components/ui/data-table";
import { EmptyState } from "../components/ui/empty-state";
import { ErrorState } from "../components/ui/error-state";
import { FormField } from "../components/ui/form-field";
import { Input } from "../components/ui/input";
import { Modal } from "../components/ui/modal";
import { PageHeader } from "../components/ui/page-header";
import { Pagination } from "../components/ui/pagination";
import { Panel } from "../components/ui/panel";
import { Select } from "../components/ui/select";
import { copy } from "../content/copy";
import { ApiError, request } from "../lib/api";
import { track } from "../lib/analytics";
import { useAuth } from "../lib/auth";
import { formatCount } from "../lib/format";
import { hasPermission } from "../lib/permission";
import { CourseDialog } from "./training/course-dialog";
import { MyTrainingView } from "./training/my-training";
import { PlanDrawer } from "./training/plan-drawer";
import type {
  Course,
  DiagnoseResult,
  LedgerRow,
  Option,
  PageData,
  PlanDetail,
  PlanSummary,
} from "./training/types";
import styles from "./training.module.css";

const text = copy.training;
const courseText = text.courses;
const formText = text.courseForm;
const diagnoseText = text.diagnose;
const planText = text.plans;
const ledgerText = text.ledger;

type TabKey = "courses" | "diagnose" | "plans" | "ledger";

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: "courses", label: text.tabs.courses },
  { key: "diagnose", label: text.tabs.diagnose },
  { key: "plans", label: text.tabs.plans },
  { key: "ledger", label: text.tabs.ledger },
];

type ProfileOption = { id: number; resume_id: number; name: string };

const PAGE_SIZE = 20;

function HrTrainingPage() {
  const { me } = useAuth();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<TabKey>("courses");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const [courseKeyword, setCourseKeyword] = useState("");
  const [courseSubmitted, setCourseSubmitted] = useState("");
  const [coursePage, setCoursePage] = useState(1);
  const [courseDialog, setCourseDialog] = useState<{ open: boolean; course: Course | null }>({ open: false, course: null });
  const [courseToDelete, setCourseToDelete] = useState<Course | null>(null);
  const [courseError, setCourseError] = useState("");

  const [diagnoseCandidate, setDiagnoseCandidate] = useState("");
  const [diagnoseJob, setDiagnoseJob] = useState("");
  const [diagnoseKey, setDiagnoseKey] = useState<{ candidateId: number; jobId: number } | null>(null);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [weeks, setWeeks] = useState("4");
  const [mentor, setMentor] = useState("");
  const [generateError, setGenerateError] = useState("");

  const [planPage, setPlanPage] = useState(1);
  const [openPlanId, setOpenPlanId] = useState<number | null>(null);

  const [ledgerCandidate, setLedgerCandidate] = useState("");
  const [ledgerPage, setLedgerPage] = useState(1);

  const canView = hasPermission(me, "train:view");
  const canCreate = hasPermission(me, "train:create");
  const canEdit = hasPermission(me, "train:edit");
  const canDelete = hasPermission(me, "train:delete");

  useEffect(() => {
    track("page_view", { page: "training" });
  }, []);

  const courses = useQuery({
    queryKey: ["training-courses", courseSubmitted, coursePage],
    queryFn: () =>
      request<PageData<Course>>(
        `/training-courses?keyword=${encodeURIComponent(courseSubmitted)}&page=${coursePage}&page_size=50`,
      ),
    enabled: canView && tab === "courses",
  });

  const exams = useQuery({
    queryKey: ["training-exams"],
    queryFn: () => request<Option[]>("/exams?page_size=200"),
    enabled: canView && canCreate,
  });

  const candidates = useQuery({
    queryKey: ["training-candidates"],
    queryFn: () => request<PageData<ProfileOption>>("/talent-profiles?page_size=200"),
    enabled: canView,
  });

  const jobs = useQuery({
    queryKey: ["training-jobs"],
    queryFn: () => request<PageData<Option>>("/job-profiles?page_size=200"),
    enabled: canView,
  });

  const plans = useQuery({
    queryKey: ["training-plans", planPage],
    queryFn: () => request<PageData<PlanSummary>>(`/prejob-plans?page=${planPage}&page_size=${PAGE_SIZE}`),
    enabled: canView && tab === "plans",
  });

  const diagnose = useQuery({
    queryKey: ["training-diagnose", diagnoseKey],
    queryFn: () =>
      request<DiagnoseResult>(
        `/training/diagnose?candidate_id=${diagnoseKey?.candidateId}&job_id=${diagnoseKey?.jobId}`,
      ),
    enabled: canView && diagnoseKey !== null,
  });

  const ledger = useQuery({
    queryKey: ["training-ledger", ledgerCandidate, ledgerPage],
    queryFn: () =>
      request<PageData<LedgerRow>>(
        `/training/ledger?candidate_id=${ledgerCandidate}&page=${ledgerPage}&page_size=${PAGE_SIZE}`,
      ),
    enabled: canView && ledgerCandidate !== "",
  });

  useEffect(() => {
    if (!candidates.data?.items.length) return;
    if (!diagnoseCandidate) setDiagnoseCandidate(String(candidates.data.items[0].resume_id));
    if (!ledgerCandidate) setLedgerCandidate(String(candidates.data.items[0].resume_id));
  }, [candidates.data, diagnoseCandidate, ledgerCandidate]);

  useEffect(() => {
    if (!jobs.data?.items.length) return;
    if (!diagnoseJob) setDiagnoseJob(String(jobs.data.items[0].id));
  }, [jobs.data, diagnoseJob]);

  const candidateOptions = useMemo(
    () =>
      (candidates.data?.items ?? []).map((item) => ({
        value: String(item.resume_id),
        label: item.name,
      })),
    [candidates.data],
  );

  const jobOptions = useMemo(
    () => (jobs.data?.items ?? []).map((item) => ({ value: String(item.id), label: item.name })),
    [jobs.data],
  );

  const examMap = useMemo(() => {
    const map = new Map<number, string>();
    (exams.data ?? []).forEach((exam) => map.set(exam.id, exam.name));
    return map;
  }, [exams.data]);

  const saveCourse = useMutation({
    mutationFn: (payload: { id?: number; body: Record<string, unknown> }) =>
      request<Course>(payload.id ? `/training-courses/${payload.id}` : "/training-courses", {
        method: payload.id ? "PUT" : "POST",
        body: payload.body,
      }),
    onSuccess: () => {
      setCourseDialog({ open: false, course: null });
      setCourseError("");
      void queryClient.invalidateQueries({ queryKey: ["training-courses"] });
    },
    onError: (error) => {
      setCourseError(error instanceof ApiError ? error.message : formText.saveError);
    },
  });

  const deleteCourse = useMutation({
    mutationFn: (id: number) => request<{ deleted: number }>(`/training-courses/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      setCourseToDelete(null);
      void queryClient.invalidateQueries({ queryKey: ["training-courses"] });
    },
  });

  const generatePlan = useMutation({
    mutationFn: () =>
      request<PlanDetail>("/prejob-plans/generate", {
        method: "POST",
        body: {
          candidate_id: Number(diagnoseCandidate),
          job_id: Number(diagnoseJob),
          weeks: Math.max(1, Math.min(12, Number(weeks) || 4)),
          mentor: mentor.trim(),
        },
      }),
    onSuccess: (plan) => {
      setGenerateOpen(false);
      setGenerateError("");
      setPlanPage(1);
      setTab("plans");
      setOpenPlanId(plan.id);
      void queryClient.invalidateQueries({ queryKey: ["training-plans"] });
    },
    onError: (error) => {
      setGenerateError(error instanceof ApiError ? error.message : diagnoseText.generateError);
    },
  });

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

  const courseColumns: Column<Course>[] = [
    { key: "name", header: courseText.columns.name, render: (row) => <span className={styles.strong}>{row.name}</span> },
    { key: "category", header: courseText.columns.category, render: (row) => row.category || copy.common.empty },
    {
      key: "difficulty",
      header: courseText.columns.difficulty,
      width: "calc(var(--space-5xl) + var(--space-md))",
      render: (row) => text.difficulty[row.difficulty as keyof typeof text.difficulty] ?? row.difficulty,
    },
    {
      key: "hours",
      header: courseText.columns.hours,
      width: "calc(var(--space-5xl) + var(--space-2xs))",
      render: (row) => `${formatCount(row.duration_hours)} ${text.unit.hour}`,
    },
    {
      key: "instructor",
      header: courseText.columns.instructor,
      render: (row) => row.instructor || copy.common.empty,
      hideOnTablet: true,
    },
    {
      key: "exam",
      header: courseText.columns.exam,
      render: (row) => (row.exam_id ? examMap.get(row.exam_id) ?? `#${row.exam_id}` : courseText.examNone),
      hideOnTablet: true,
    },
    {
      key: "actions",
      header: courseText.columns.actions,
      width: "calc(var(--space-5xl) * 3)",
      render: (row) => (
        <div className={styles.rowActions}>
          {canEdit ? (
            <Button variant="ghost" onClick={() => { setCourseDialog({ open: true, course: row }); setCourseError(""); }}>
              {courseText.edit}
            </Button>
          ) : null}
          {canDelete ? (
            <Button variant="ghost" onClick={() => setCourseToDelete(row)}>
              {courseText.delete}
            </Button>
          ) : null}
        </div>
      ),
    },
  ];

  const gapColumns: Column<DiagnoseResult["gaps"][number]>[] = [
    { key: "dim", header: diagnoseText.columns.dimension, render: (row) => <span className={styles.strong}>{row.dimension}</span> },
    { key: "current", header: diagnoseText.columns.current, align: "right", render: (row) => formatCount(row.current) },
    { key: "target", header: diagnoseText.columns.target, align: "right", render: (row) => formatCount(row.target) },
    {
      key: "gap",
      header: diagnoseText.columns.gap,
      align: "right",
      render: (row) => <span className={styles.gap}>{diagnoseText.gapText(row.gap)}</span>,
    },
    {
      key: "severity",
      header: diagnoseText.columns.severity,
      width: "calc(var(--space-5xl) + var(--space-md))",
      render: (row) => (
        <Badge
          tone={
            row.severity === "high" ? "error" : row.severity === "medium" ? "warning" : row.severity === "low" ? "info" : "success"
          }
        >
          {text.severity[row.severity]}
        </Badge>
      ),
    },
    {
      key: "courses",
      header: diagnoseText.columns.courses,
      render: (row) => (
        <span className={styles.chips}>
          {row.recommended_courses.length
            ? row.recommended_courses.map((course) => (
                <span className={styles.chip} key={course.id}>{course.name}</span>
              ))
            : <span className={styles.muted}>{diagnoseText.noCourses}</span>}
        </span>
      ),
    },
  ];

  const planColumns: Column<PlanSummary>[] = [
    {
      key: "plan",
      header: planText.columns.plan,
      render: (row) => (
        <button type="button" className={styles.linkButton} onClick={() => setOpenPlanId(row.id)}>
          {row.plan_title}
        </button>
      ),
    },
    { key: "candidate", header: planText.columns.candidate, render: (row) => row.candidate_name },
    { key: "position", header: planText.columns.position, render: (row) => row.position_name || copy.common.empty, hideOnTablet: true },
    {
      key: "progress",
      header: planText.columns.progress,
      width: "calc(var(--space-5xl) * 3)",
      render: (row) => (
        <div className={styles.progressCell}>
          <span className={styles.progressText}>
            {row.task_total ? planText.tasksText(row.task_done, row.task_total, row.progress) : planText.tasksEmpty}
          </span>
          <span className={styles.track} aria-hidden><span className={styles.fill} style={{ width: `${row.progress}%` }} /></span>
        </div>
      ),
    },
    {
      key: "mentor",
      header: planText.columns.mentor,
      render: (row) => <span className={styles.mentorCell}>{row.mentor || copy.common.empty}</span>,
      hideOnTablet: true,
    },
    {
      key: "actions",
      header: planText.columns.actions,
      width: "calc(var(--space-5xl) * 2)",
      render: (row) => (
        <Button variant="ghost" onClick={() => setOpenPlanId(row.id)}>{planText.view}</Button>
      ),
    },
  ];

  const ledgerColumns: Column<LedgerRow>[] = [
    {
      key: "time",
      header: ledgerText.columns.time,
      width: "calc(var(--space-5xl) * 3)",
      render: (row) => <time dateTime={row.created_at.replace(" ", "T")}>{row.created_at.slice(0, 16)}</time>,
    },
    { key: "dimension", header: ledgerText.columns.dimension, render: (row) => <span className={styles.strong}>{row.dimension}</span> },
    {
      key: "change",
      header: ledgerText.columns.change,
      render: (row) => (
        <span className={styles.change}>
          {ledgerText.changeText(row.before_score, row.after_score)}
          <Badge tone={row.delta > 0 ? "success" : "neutral"}>{ledgerText.deltaText(row.delta)}</Badge>
        </span>
      ),
    },
    {
      key: "source",
      header: ledgerText.columns.source,
      render: (row) => text.source[row.source as keyof typeof text.source] ?? row.source,
      hideOnTablet: true,
    },
    { key: "note", header: ledgerText.columns.note, render: (row) => row.note },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.pageHead}>
        <PageHeader title={text.title} sub={text.sub} />
      </div>

      <div className={`${styles.tabs} glass-tabs`} role="tablist" aria-label={text.title}>
        {TABS.map((item, index) => (
          <button
            key={item.key}
            ref={(element) => {
              tabRefs.current[index] = element;
            }}
            type="button"
            role="tab"
            id={`training-tab-${item.key}`}
            aria-selected={tab === item.key}
            aria-controls={`training-panel-${item.key}`}
            tabIndex={tab === item.key ? 0 : -1}
            className={tab === item.key ? `${styles.tab} ${styles.tabActive}` : styles.tab}
            onClick={() => setTab(item.key)}
            onKeyDown={(event) => handleTabKey(event, index)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === "courses" ? (
        <div role="tabpanel" id="training-panel-courses" aria-labelledby="training-tab-courses" tabIndex={0}>
          <Panel
            title={text.tabs.courses}
            meta={courses.data ? `共 ${courses.data.total} 门` : undefined}
            actions={canCreate ? <Button variant="primary" onClick={() => { setCourseDialog({ open: true, course: null }); setCourseError(""); }}>{courseText.create}</Button> : undefined}
            className={styles.glassTable}
            flush
          >
            <form className={styles.searchBar} onSubmit={(event) => { event.preventDefault(); setCoursePage(1); setCourseSubmitted(courseKeyword.trim()); }}>
              <FormField id="course-search" label={courseText.searchLabel} className={styles.grow}>
                <Input value={courseKeyword} placeholder={courseText.searchPlaceholder} onChange={(event) => setCourseKeyword(event.target.value)} />
              </FormField>
              <Button type="submit" variant="secondary">{courseText.searchAction}</Button>
            </form>
            {courses.isError ? (
              <div className={styles.stateWrap}>
                <ErrorState
                  title={courseText.loadError}
                  detail={courses.error instanceof ApiError ? courses.error.message : courseText.loadErrorHint}
                  retryLabel={courseText.retry}
                  onRetry={() => void courses.refetch()}
                />
              </div>
            ) : (
              <>
                <DataTable
                  caption={text.tabs.courses}
                  columns={courseColumns}
                  rows={courses.data?.items ?? []}
                  rowKey={(row) => row.id}
                  loading={courses.isPending}
                  skeletonRows={5}
                  empty={<div className={styles.emptyWrap}><EmptyState title={courseText.empty} hint={courseText.emptyHint} /></div>}
                />
                {(courses.data?.total ?? 0) > 50 ? (
                  <div className={styles.pagination}>
                    <Pagination page={coursePage} pageSize={50} total={courses.data?.total ?? 0} onChange={setCoursePage} label="" />
                  </div>
                ) : null}
              </>
            )}
          </Panel>
        </div>
      ) : null}

      {tab === "diagnose" ? (
        <div role="tabpanel" id="training-panel-diagnose" aria-labelledby="training-tab-diagnose" tabIndex={0}>
          <Panel title={text.tabs.diagnose} meta={diagnoseText.meta} className={styles.glassTable} flush>
            <div className={styles.diagnoseBar}>
              <FormField id="diagnose-candidate" label={diagnoseText.candidate} className={styles.selectField}>
                <Select id="diagnose-candidate" value={diagnoseCandidate} options={candidateOptions} onChange={(value) => { setDiagnoseCandidate(value); setDiagnoseKey(null); }} ariaLabel={diagnoseText.candidate} />
              </FormField>
              <FormField id="diagnose-job" label={diagnoseText.job} className={styles.selectField}>
                <Select id="diagnose-job" value={diagnoseJob} options={jobOptions} onChange={(value) => { setDiagnoseJob(value); setDiagnoseKey(null); }} ariaLabel={diagnoseText.job} />
              </FormField>
              <Button
                variant="primary"
                disabled={!diagnoseCandidate || !diagnoseJob}
                onClick={() => setDiagnoseKey({ candidateId: Number(diagnoseCandidate), jobId: Number(diagnoseJob) })}
              >
                {diagnoseText.run}
              </Button>
              {diagnose.data ? (
                <Button variant="secondary" onClick={() => { setGenerateOpen(true); setGenerateError(""); }}>
                  {diagnoseText.generate}
                </Button>
              ) : null}
            </div>

            {diagnoseKey === null ? (
              <div className={styles.initialWrap}>
                <EmptyState title={diagnoseText.initial} hint={diagnoseText.initialHint} />
              </div>
            ) : diagnose.isError ? (
              <div className={styles.stateWrap}>
                <ErrorState
                  title={diagnoseText.loadError}
                  detail={diagnose.error instanceof ApiError ? diagnose.error.message : diagnoseText.loadErrorHint}
                  retryLabel={diagnoseText.retry}
                  onRetry={() => void diagnose.refetch()}
                />
              </div>
            ) : (
              <DataTable
                caption={text.tabs.diagnose}
                columns={gapColumns}
                rows={diagnose.data?.gaps ?? []}
                rowKey={(row) => row.dimension}
                loading={diagnose.isPending}
                skeletonRows={5}
                empty={<div className={styles.emptyWrap}><EmptyState title={diagnoseText.initial} /></div>}
              />
            )}
            {diagnose.data ? (
              <p className={styles.note}>{diagnoseText.resultMeta(diagnose.data.candidate_name, diagnose.data.position_name)}</p>
            ) : null}
          </Panel>
        </div>
      ) : null}

      {tab === "plans" ? (
        <div role="tabpanel" id="training-panel-plans" aria-labelledby="training-tab-plans" tabIndex={0}>
          <Panel title={text.tabs.plans} meta={planText.meta} className={styles.glassTable} flush>
            {plans.isError ? (
              <div className={styles.stateWrap}>
                <ErrorState
                  title={planText.loadError}
                  detail={plans.error instanceof ApiError ? plans.error.message : planText.loadError}
                  retryLabel={planText.retry}
                  onRetry={() => void plans.refetch()}
                />
              </div>
            ) : (
              <>
                <DataTable
                  caption={text.tabs.plans}
                  columns={planColumns}
                  rows={plans.data?.items ?? []}
                  rowKey={(row) => row.id}
                  loading={plans.isPending}
                  skeletonRows={4}
                  empty={<div className={styles.emptyWrap}><EmptyState title={planText.empty} hint={planText.emptyHint} /></div>}
                />
                {(plans.data?.total ?? 0) > PAGE_SIZE ? (
                  <div className={styles.pagination}>
                    <Pagination page={planPage} pageSize={PAGE_SIZE} total={plans.data?.total ?? 0} onChange={setPlanPage} label="" />
                  </div>
                ) : null}
              </>
            )}
          </Panel>
        </div>
      ) : null}

      {tab === "ledger" ? (
        <div role="tabpanel" id="training-panel-ledger" aria-labelledby="training-tab-ledger" tabIndex={0}>
          <Panel title={text.tabs.ledger} meta={ledgerText.meta} className={styles.glassTable} flush>
            <div className={styles.diagnoseBar}>
              <FormField id="ledger-candidate" label={ledgerText.candidate} className={styles.selectField}>
                <Select
                  id="ledger-candidate"
                  value={ledgerCandidate}
                  options={candidateOptions}
                  onChange={(value) => { setLedgerCandidate(value); setLedgerPage(1); }}
                  ariaLabel={ledgerText.candidate}
                />
              </FormField>
            </div>
            {ledger.isError ? (
              <div className={styles.stateWrap}>
                <ErrorState
                  title={planText.loadError}
                  detail={ledger.error instanceof ApiError ? ledger.error.message : planText.loadError}
                  retryLabel={planText.retry}
                  onRetry={() => void ledger.refetch()}
                />
              </div>
            ) : (
              <>
                <DataTable
                  caption={text.tabs.ledger}
                  columns={ledgerColumns}
                  rows={ledger.data?.items ?? []}
                  rowKey={(row) => row.id}
                  loading={ledger.isPending}
                  skeletonRows={4}
                  empty={<div className={styles.emptyWrap}><EmptyState title={ledgerText.empty} hint={ledgerText.emptyHint} /></div>}
                />
                {(ledger.data?.total ?? 0) > PAGE_SIZE ? (
                  <div className={styles.pagination}>
                    <Pagination page={ledgerPage} pageSize={PAGE_SIZE} total={ledger.data?.total ?? 0} onChange={setLedgerPage} label="" />
                  </div>
                ) : null}
              </>
            )}
          </Panel>
        </div>
      ) : null}

      <CourseDialog
        open={courseDialog.open}
        course={courseDialog.course}
        exams={(exams.data ?? []).map((exam) => ({ id: exam.id, name: exam.name }))}
        busy={saveCourse.isPending}
        error={courseError}
        onClose={() => setCourseDialog({ open: false, course: null })}
        onSave={(body) => saveCourse.mutate({ id: courseDialog.course?.id, body })}
      />

      <ConfirmDialog
        open={courseToDelete !== null}
        title={courseText.deleteTitle}
        description={courseToDelete ? courseText.deleteBody(courseToDelete.name) : undefined}
        confirmLabel={courseText.delete}
        tone="destructive"
        busy={deleteCourse.isPending}
        onConfirm={() => { if (courseToDelete) deleteCourse.mutate(courseToDelete.id); }}
        onClose={() => setCourseToDelete(null)}
      />

      <Modal
        open={generateOpen}
        onClose={() => setGenerateOpen(false)}
        title={diagnoseText.generateTitle}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setGenerateOpen(false)} disabled={generatePlan.isPending}>{copy.common.cancel}</Button>
            <Button variant="primary" onClick={() => generatePlan.mutate()} loading={generatePlan.isPending}>{diagnoseText.generate}</Button>
          </>
        }
      >
        <div className={styles.formStack}>
          <FormField id="plan-weeks" label={diagnoseText.weeks} hint={diagnoseText.weeksHint}>
            <Input type="number" min={1} max={12} value={weeks} onChange={(event) => setWeeks(event.target.value)} />
          </FormField>
          <FormField id="plan-mentor" label={diagnoseText.mentor}>
            <Input value={mentor} placeholder={diagnoseText.mentorPlaceholder} onChange={(event) => setMentor(event.target.value)} />
          </FormField>
          <p className={styles.note}>{diagnoseText.generateHint}</p>
          {generateError ? <p className={styles.formError} role="alert">{generateError}</p> : null}
        </div>
      </Modal>

      <PlanDrawer planId={openPlanId} onClose={() => setOpenPlanId(null)} />
    </div>
  );
}


export default function TrainingPage() {
  const { me } = useAuth();
  const isEmployee = Boolean(me?.user.roles.includes("employee") && !hasPermission(me, "resume:view"));
  return isEmployee ? <MyTrainingView /> : <HrTrainingPage />;
}
