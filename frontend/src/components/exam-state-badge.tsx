import { Badge } from "./ui/badge";
import type { ExamSummary } from "../lib/api-types";

type ExamStateBadgeProps = {
  state: ExamSummary["state"];
  label?: string;
};

const FALLBACK_LABEL: Record<ExamSummary["state"], string> = {
  none: "未测评",
  assigned: "待测评",
  submitted: "已测评",
};

export function ExamStateBadge({ state, label }: ExamStateBadgeProps) {
  const tone = state === "submitted" ? "success" : state === "assigned" ? "info" : "neutral";
  return <Badge tone={tone}>{label || FALLBACK_LABEL[state]}</Badge>;
}
