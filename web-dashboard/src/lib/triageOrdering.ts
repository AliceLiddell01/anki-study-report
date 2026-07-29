import type { TriageItem, TriagePriority, TriageReason, TriageSource } from "../types/triage";

const PRIORITY_ORDER: Record<TriagePriority, number> = { high: 0, medium: 1, low: 2 };
const REASON_ORDER: Record<string, number> = {
  "learning.leech": 0,
  "learning.repeated_again": 1,
  "learning.low_pass_rate": 2,
  "learning.slow_answer": 3,
  "content.required_text_missing": 10,
  "content.audio_missing": 11,
  "content.image_missing": 12,
  "content.text_too_short": 13,
  "content.required_group_missing": 14,
};
const SOURCE_ORDER: Record<TriageSource, number> = {
  search_workset: 0,
  attention: 1,
  signals: 2,
  profile_checks: 3,
};

export function compareTriageItems(left: TriageItem, right: TriageItem): number {
  const priority = priorityRank(left.priority) - priorityRank(right.priority);
  if (priority) return priority;
  const reason = reasonRank(left.primaryReasonCode) - reasonRank(right.primaryReasonCode);
  if (reason) return reason;
  const recency = reasonRecency(right.reasons[0]) - reasonRecency(left.reasons[0]);
  if (recency) return recency;
  return numericId(left.cardId) - numericId(right.cardId);
}

export function compareTriageReasons(left: TriageReason, right: TriageReason): number {
  const priority = priorityRank(left.priority) - priorityRank(right.priority);
  if (priority) return priority;
  const reason = reasonRank(left.code) - reasonRank(right.code);
  if (reason) return reason;
  const recency = reasonRecency(right) - reasonRecency(left);
  if (recency) return recency;
  return left.code.localeCompare(right.code);
}

export function strongestPriority(left: TriagePriority | null, right: TriagePriority | null): TriagePriority | null {
  if (!left) return right;
  if (!right) return left;
  return priorityRank(left) <= priorityRank(right) ? left : right;
}

export function sortedSources(values: readonly TriageSource[]): TriageSource[] {
  return [...new Set(values)].sort((left, right) => SOURCE_ORDER[left] - SOURCE_ORDER[right]);
}

export function reasonRank(code: string | null): number {
  return code ? REASON_ORDER[code] ?? 99 : 99;
}

function priorityRank(value: TriagePriority | null): number {
  return value ? PRIORITY_ORDER[value] : 99;
}

function reasonRecency(reason: TriageReason | undefined): number {
  return reason?.detectedAtMs ?? 0;
}

function numericId(value: string): number {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : Number.MAX_SAFE_INTEGER;
}
