export type Audience = "candidate" | "employee";

export type ResumeBrief = {
  parsed_resume_id: number;
  resume_file_id: number;
  name: string;
  education: string;
  major: string;
  years_experience: number;
  skills_top: string[];
  skills_count: number;
  filename: string;
  created_at: string;
  accessible: boolean;
};

export type ExamSummaryItem = {
  exam_id: number;
  exam_name: string;
  audience: Audience;
  state: "assigned" | "submitted";
  assignment_id: number | null;
  submission_id: number | null;
  deadline: string | null;
  score: number | null;
  max_score: number | null;
  pass_score: number | null;
  passed: boolean | null;
  submitted_at: string | null;
};

export type ExamSummary = {
  state: "none" | "assigned" | "submitted";
  label: string;
  total: number;
  passed: number;
  items: ExamSummaryItem[];
};

export type ResumeIdentitySibling = {
  parsed_resume_id: number;
  name: string;
  is_current: boolean;
  created_at: string;
  filename: string;
};

export type ResumeIdentity = {
  key: string;
  is_current: boolean;
  superseded_by: number | null;
  siblings: ResumeIdentitySibling[];
};

export type ExamAssignment = {
  id: number;
  exam_id: number;
  exam_name: string;
  audience: Audience;
  parsed_resume_id: number;
  candidate_name: string;
  status: "pending" | "submitted" | "cancelled";
  submission_id: number | null;
  assigned_by: number;
  deadline: string | null;
  note: string;
  created_at: string;
  result: {
    score: number;
    max_score: number;
    pass_score: number;
    passed: boolean;
  } | null;
};

export type QuestionDraft = {
  question_type: string;
  content: string;
  options: string[];
  answer: string;
  score: number;
  knowledge_point: string;
  knowledge_category: string;
  difficulty: string;
  analysis: string;
  needs_review: boolean;
};

export type QuestionImportResult = {
  source: "ai" | "rule";
  bank_id: number;
  bank_name: string;
  filename: string;
  parsed_count: number;
  draft: QuestionDraft[];
  warnings: string[];
  text_preview: string;
  text_length: number;
  ai_available: boolean;
};

export type QuestionImportConfirmResult = {
  created: number;
  skipped: number;
  failed: Array<{ index: number; reason: string }>;
  failed_count: number;
  bank_total: number;
};

export type MyTrainingTask = {
  id: number;
  plan_id: number;
  phase_index: number;
  title: string;
  dimension: string;
  course_id: number | null;
  exam_id: number | null;
  required_minutes: number;
  study_minutes: number;
  progress: number;
  status: "pending" | "learning" | "done" | "failed" | string;
  detail: Record<string, unknown>;
};

export type MyTrainingSummary = {
  onboarded: boolean;
  candidate_id: number | null;
  candidate_name?: string;
  plans: number;
  tasks: number;
  done_tasks: number;
  pending_tasks: number;
  progress_pct: number;
  ledger: number;
  todo: MyTrainingTask[];
};

export type MyTrainingPlan = {
  id: number;
  plan_title: string;
  goal: string;
  position_name: string;
  total_weeks: number;
  mentor: string;
  status: string;
  total_tasks: number;
  done_tasks: number;
  progress_pct: number;
  tasks: MyTrainingTask[];
};

export type MyTrainingPlansResult = {
  onboarded: boolean;
  candidate_id: number | null;
  total: number;
  items: MyTrainingPlan[];
};

export type MyTrainingLedgerRow = {
  id: number;
  dimension: string;
  before_score: number;
  after_score: number;
  delta: number;
  source: string;
  note: string;
  created_at: string;
};

export type MyTrainingLedgerResult = {
  onboarded: boolean;
  candidate_id: number | null;
  total: number;
  items: MyTrainingLedgerRow[];
};

export type VectorStatus = {
  embed: { available: boolean; model: string; dim: number };
  milvus: {
    available: boolean;
    uri: string;
    resume_collection: string;
    job_collection: string;
    resume_count: number;
    job_count: number;
    expected_count?: number;
    stale?: boolean;
  };
};
