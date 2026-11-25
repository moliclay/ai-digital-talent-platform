import { copy } from "../content/copy";

const countFormatter = new Intl.NumberFormat("zh-CN");

export function formatCount(value: number | null | undefined): string {
  return countFormatter.format(Number(value ?? 0));
}

export function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined) return copy.common.empty;
  return Number(value).toFixed(1);
}

export function formatPercent(part: number, total: number): number {
  if (!total) return 0;
  return Math.round((part / total) * 100);
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** 后端给的是 "2026-11-03 14:20:31" 这种本地时间字符串，不做时区换算。 */
export function formatDateTime(input: string): string {
  if (!input) return copy.common.unknown;
  const date = new Date(input.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return input;

  const now = new Date();
  const clock = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  if (sameDay) return `${copy.common.today} ${clock}`;

  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  if (
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()
  ) {
    return `${copy.common.yesterday} ${clock}`;
  }

  if (date.getFullYear() === now.getFullYear()) {
    return `${date.getMonth() + 1}-${pad(date.getDate())} ${clock}`;
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${clock}`;
}

export function formatDuration(ms: number | null | undefined): string {
  const value = Number(ms ?? 0);
  if (value < 1000) return `${formatCount(value)} ${copy.common.ms}`;
  return `${(value / 1000).toFixed(1)} ${copy.common.seconds}`;
}

export function initials(name: string): string {
  const trimmed = (name || "").trim();
  if (!trimmed) return "?";
  return trimmed.slice(-2);
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 KB";
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.round(kb)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}
