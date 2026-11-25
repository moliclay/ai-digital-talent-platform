export type Course = {
  id: number;
  name: string;
  description: string;
  category: string;
  duration_hours: number;
  difficulty: string;
  instructor: string;
  content: string;
  exam_id: number | null;
  status: string;
};

export type DiagnoseGap = {
  dimension: string;
  current: number;
  target: number;
  gap: number;
  severity: "high" | "medium" | "low" | "none";
  recommended_courses: Course[];
};

export type DiagnoseResult = {
  candidate_id: number;
  candidate_name: string;
  job_id: number;
  position_name: string;
  targets: Record<string, number>;
  gaps: DiagnoseGap[];
};

export type PlanPhase = {
  week: number;
  goal: string;
  dimension: string;
};

export type PlanTask = {
  id: number;
  phase_index: number;
  title: string;
  dimension: string;
  course_id: number | null;
  exam_id: number | null;
  required_minutes: number;
  study_minutes: number;
  progress: number;
  status: "pending" | "learning" | "done" | "failed" | string;
  detail: { goal?: string; target?: number; current?: number };
  last_active_at: string;
};

export type PlanSummary = {
  id: number;
  candidate_id: number;
  candidate_name: string;
  position_name: string;
  plan_title: string;
  goal: string;
  total_weeks: number;
  mentor: string;
  status: string;
  course_ids: number[];
  task_total: number;
  task_done: number;
  progress: number;
};

export type PlanDetail = PlanSummary & {
  phases: PlanPhase[];
  tasks: PlanTask[];
};

export type LedgerRow = {
  id: number;
  candidate_id: number;
  candidate_name: string;
  dimension: string;
  before_score: number;
  after_score: number;
  delta: number;
  source: string;
  ref_id: number;
  note: string;
  created_at: string;
};

export type Submission = {
  id: number;
  candidate_name: string;
  exam_id: number;
  result: string;
  score: number;
};

export type Option = { id: number; name: string };

export type PageData<T> = { items: T[]; total: number; page: number; page_size: number };
