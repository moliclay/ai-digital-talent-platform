export type Condition = {
  key: string;
  op: string;
  value: unknown;
};

export type JobProfile = {
  id: number;
  name: string;
  prompt: string;
  conditions: Condition[];
  score_rules: { weights?: Record<string, number> };
  ability_requirements: Record<string, number>;
  passing_threshold: number;
  status: string;
  required_skills: string[];
  created_at: string;
};

export type TrialResult = {
  job_profile_id: number;
  job_profile_name: string;
  threshold: number;
  scanned: number;
  passed: number;
  failed: number;
  avg_score: number;
  buckets: Array<{ label: string; count: number }>;
  top: Array<{ name: string; score: number; passed: boolean }>;
};

export type PageData<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
