export type Profile = {
  id: number;
  resume_id: number;
  name: string;
  title: string;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  abilities: Record<string, number>;
  dimensions: string[];
  tags: string[];
  recommendation: string;
  data_sources: unknown[];
  exam_evidence: ExamEvidence | null;
};

export type ExamRow = {
  dim: string;
  resume: number;
  exam: number;
  merged: number;
  questions: number;
  weight: number;
};

export type ExamEvidence = {
  type: string;
  submissions: number;
  exam_ids: number[];
  weight: number;
  rows: ExamRow[];
};

export type PageData<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type GenerateResult = {
  total: number;
  created: number;
  updated: number;
  ai_used: number;
  ai_available: boolean;
  exam_used: number;
  exam_weight: number;
};

export type ResumeOption = {
  id: number;
  name: string;
  education: string;
  years_experience: number;
};

export type SourceNote = {
  ai?: boolean;
  generated_at?: string;
  resume_id?: number;
};

export function sourceNote(profile: Profile): SourceNote | null {
  for (const source of profile.data_sources) {
    if (source && typeof source === "object" && "ai" in source) {
      return source as SourceNote;
    }
  }
  return null;
}

export const DIM_ORDER = ["技术深度", "工程能力", "业务理解", "协作沟通", "成长性"];
