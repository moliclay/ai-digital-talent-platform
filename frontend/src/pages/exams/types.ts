import type { Audience, ExamAssignment, QuestionDraft } from "../../lib/api-types";

export type Bank = {
  id: number;
  name: string;
  description: string;
  total_questions: number;
  status: string;
  audience: Audience;
};

export type Question = {
  id: number;
  bank_id: number;
  type: string;
  content: string;
  options: string[];
  score: number;
  difficulty: string;
  knowledge_point: string;
  knowledge_category: string;
  answer: string;
};

export type Exam = {
  id: number;
  name: string;
  category: string;
  total_questions: number;
  total_score: number;
  pass_score: number;
  duration_minutes: number;
  status: string;
  submissions: number;
  audience: Audience;
};

export type Submission = {
  id: number;
  exam_id: number;
  exam_name: string;
  candidate_name: string;
  score: number;
  max_score: number;
  pass_score: number;
  result: string;
  recommendation: string;
  parsed_resume_id?: number | null;
  audience?: Audience;
};

export type PageData<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type CreateExamResult = {
  id: number;
  name: string;
  total_questions: number;
  total_score: number;
  pass_score: number;
};

export type CreateQuestionResult = {
  id: number;
  content: string;
  score: number;
};

export type CreateBankResult = {
  id: number;
  name: string;
};


export type AssignmentsResult = { items: ExamAssignment[]; total: number };
export type { Audience, ExamAssignment, QuestionDraft };
