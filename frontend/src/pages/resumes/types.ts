import type { ExamSummary, ResumeIdentity } from "../../lib/api-types";

export type ResumeRow = {
  id: number;
  resume_file_id: number;
  name: string;
  phone: string;
  email: string;
  gender: string;
  age: number | null;
  education: string;
  major: string;
  skills: string[];
  years_experience: number;
  strengths: string;
  manually_fixed: boolean;
  filename: string;
  status: string;
  project_name: string;
  created_at: string;
  confidence: number | null;
  is_current?: boolean;
  superseded_by?: number | null;
  identity_key?: string;
  employee_user_id?: number | null;
  onboarded_at?: string | null;
  exam_summary?: ExamSummary;
};

export type ResumeLog = {
  status: string;
  message: string;
  duration_ms: number;
  created_at: string;
};

export type ResumeDetail = ResumeRow & {
  identity?: ResumeIdentity;
  attachment_url: string;
  resume_content: string;
  raw_json: unknown;
  logs: ResumeLog[];
};

export type QueueTask = {
  task_id: number;
  resume_id: number;
  filename: string;
  status: string;
  attempts: number;
  error: string | null;
  created_at: string;
};

export type QueueData = {
  counts: Record<string, number>;
  tasks: QueueTask[];
};

export type PageData<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type JobOption = {
  id: number;
  name: string;
  status: string;
};


export type OnboardResult = {
  parsed_resume_id: number;
  employee_user_id: number;
  username: string;
  real_name: string;
  department_id: number | null;
  department_name: string;
  initial_password: string;
  password_generated: boolean;
  onboarded_at: string;
  role: string;
  note: string;
};

export type SuspectedGroup = {
  reason: string;
  ids: number[];
  names: string[];
  education: string;
  major: string;
};

export type SuspectedResult = {
  total: number;
  groups: SuspectedGroup[];
};
