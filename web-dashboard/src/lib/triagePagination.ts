import type {
  TriageContentSourceStatus,
  TriageItem,
  TriageQueryResponse,
  TriageReason,
  TriageResponseStatus,
  TriageSourceAvailability,
  TriageSourceStatus,
} from "../types/triage";
import { compareTriageItems, compareTriageReasons, sortedSources, strongestPriority } from "./triageOrdering";

export const MAX_ACCUMULATED_ITEMS = 500;
export const MAX_CONTENT_PAGES = 10;

export interface TriagePageMergeResult {
  response: TriageQueryResponse;
  addedItemCount: number;
  capped: boolean;
}

export function mergeTriagePages(base: TriageQueryResponse, next: TriageQueryResponse): TriagePageMergeResult {
  if (base.dataset !== "automatic" || next.dataset !== "automatic") {
    throw new Error("Only automatic triage pages can be accumulated.");
  }

  const itemsById = new Map(base.items.map((item) => [item.itemId, item]));
  let addedItemCount = 0;
  for (const item of next.items) {
    const current = itemsById.get(item.itemId);
    if (current) itemsById.set(item.itemId, mergeItem(current, item));
    else {
      itemsById.set(item.itemId, item);
      addedItemCount += 1;
    }
  }

  const allItems = [...itemsById.values()].sort(compareTriageItems);
  const capped = allItems.length > MAX_ACCUMULATED_ITEMS;
  const items = allItems.slice(0, MAX_ACCUMULATED_ITEMS);
  const contentCandidates = mergeContentSource(
    base.sourceStatus.contentCandidates,
    next.sourceStatus.contentCandidates,
  );
  const contentChecks = {
    ...next.contentChecks,
    confirmedProfileCount: Math.max(base.contentChecks.confirmedProfileCount, next.contentChecks.confirmedProfileCount),
    needsReviewProfileCount: Math.max(base.contentChecks.needsReviewProfileCount, next.contentChecks.needsReviewProfileCount),
    disabledProfileCount: Math.max(base.contentChecks.disabledProfileCount, next.contentChecks.disabledProfileCount),
    suggestedProfileCount: Math.max(base.contentChecks.suggestedProfileCount, next.contentChecks.suggestedProfileCount),
    scannedNoteCount: base.contentChecks.scannedNoteCount + next.contentChecks.scannedNoteCount,
    evaluatedNoteCount: base.contentChecks.evaluatedNoteCount + next.contentChecks.evaluatedNoteCount,
    failedCheckCount: base.contentChecks.failedCheckCount + next.contentChecks.failedCheckCount,
    skippedCount: base.contentChecks.skippedCount + next.contentChecks.skippedCount,
    truncated: next.contentChecks.truncated,
    nextCursor: next.contentChecks.nextCursor,
    errorCode: next.contentChecks.errorCode ?? base.contentChecks.errorCode,
    status: mergeContentCheckStatus(base.contentChecks.status, next.contentChecks.status),
  };

  return {
    addedItemCount,
    capped,
    response: {
      ...next,
      status: mergeResponseStatus(base.status, next.status, items.length),
      generatedAtMs: Math.max(base.generatedAtMs, next.generatedAtMs),
      totalCount: Math.max(base.totalCount, next.totalCount, items.length),
      returnedCount: items.length,
      truncated: base.truncated || next.truncated || capped,
      sourceStatus: {
        learningCandidates: mergeRepeatedSource(base.sourceStatus.learningCandidates, next.sourceStatus.learningCandidates),
        contentCandidates,
        signals: mergeRepeatedSource(base.sourceStatus.signals, next.sourceStatus.signals),
        searchResolver: mergeRepeatedSource(base.sourceStatus.searchResolver, next.sourceStatus.searchResolver),
        profileChecks: mergeRepeatedSource(base.sourceStatus.profileChecks, next.sourceStatus.profileChecks),
      },
      contentChecks,
      items,
    },
  };
}

function mergeItem(base: TriageItem, next: TriageItem): TriageItem {
  const reasonsById = new Map(base.reasons.map((reason) => [reason.reasonId, reason]));
  for (const reason of next.reasons) {
    const current = reasonsById.get(reason.reasonId);
    reasonsById.set(reason.reasonId, current ? mergeReason(current, reason) : reason);
  }
  const reasons = [...reasonsById.values()].sort(compareTriageReasons).slice(0, 4);
  return {
    ...base,
    ...next,
    priority: reasons[0]?.priority ?? strongestPriority(base.priority, next.priority),
    primaryReasonCode: reasons[0]?.code ?? next.primaryReasonCode ?? base.primaryReasonCode,
    reasons,
    sources: sortedSources([...base.sources, ...next.sources]),
    inspect: next.inspect ?? base.inspect,
  };
}

function mergeReason(base: TriageReason, next: TriageReason): TriageReason {
  const evidence = new Map<string, TriageReason["evidence"][number]>();
  for (const value of [...base.evidence, ...next.evidence]) evidence.set(stableJson(value), value);
  return {
    ...base,
    ...next,
    priority: strongestPriority(base.priority, next.priority) ?? base.priority,
    sources: sortedSources([...base.sources, ...next.sources]),
    evidence: [...evidence.values()].slice(0, 4),
    detectedAtMs: Math.max(base.detectedAtMs ?? 0, next.detectedAtMs ?? 0) || null,
  };
}

function mergeRepeatedSource(base: TriageSourceStatus, next: TriageSourceStatus): TriageSourceStatus {
  return {
    ...next,
    status: worseAvailability(base.status, next.status),
    itemCount: Math.max(base.itemCount, next.itemCount),
    skippedCount: Math.max(base.skippedCount, next.skippedCount),
    truncated: base.truncated || next.truncated,
    errorCode: next.errorCode ?? base.errorCode,
  };
}

function mergeContentSource(base: TriageContentSourceStatus, next: TriageContentSourceStatus): TriageContentSourceStatus {
  return {
    ...next,
    status: worseAvailability(base.status, next.status),
    itemCount: base.itemCount + next.itemCount,
    skippedCount: base.skippedCount + next.skippedCount,
    scannedNoteCount: base.scannedNoteCount + next.scannedNoteCount,
    truncated: next.truncated,
    nextCursor: next.nextCursor,
    errorCode: next.errorCode ?? base.errorCode,
  };
}

function worseAvailability(left: TriageSourceAvailability, right: TriageSourceAvailability): TriageSourceAvailability {
  const order: Record<TriageSourceAvailability, number> = {
    error: 5,
    unavailable: 4,
    partial: 3,
    available: 2,
    empty: 1,
    not_applicable: 0,
  };
  return order[left] >= order[right] ? left : right;
}

function mergeResponseStatus(left: TriageResponseStatus, right: TriageResponseStatus, itemCount: number): TriageResponseStatus {
  if (left === "partial" || right === "partial") return "partial";
  if (left === "unavailable" || right === "unavailable") return itemCount ? "partial" : "unavailable";
  return "available";
}

function mergeContentCheckStatus(
  left: TriageQueryResponse["contentChecks"]["status"],
  right: TriageQueryResponse["contentChecks"]["status"],
): TriageQueryResponse["contentChecks"]["status"] {
  if (left === "partial" || right === "partial") return "partial";
  if (left === "unavailable" || right === "unavailable") return "unavailable";
  if (left === "profiles_need_review" || right === "profiles_need_review") return "profiles_need_review";
  if (right === "available" || left === "available") return "available";
  return right;
}

function stableJson(value: unknown): string {
  if (!value || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  return `{${Object.entries(value as Record<string, unknown>)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`)
    .join(",")}}`;
}
