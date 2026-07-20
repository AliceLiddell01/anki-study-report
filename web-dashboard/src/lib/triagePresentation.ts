import type { TFunction } from "i18next";
import type { TriageEvidence, TriageItem, TriageReason, TriageSourceStatus } from "../types/triage";

export function reasonLabel(code: string, t: TFunction): string {
  return t(`reasons.${code.replace(/\./g, "_")}`, { defaultValue: t("reasons.other") });
}

export function scopeLabel(reason: TriageReason | undefined, t: TFunction): string {
  if (!reason) return "";
  const profile = reason.evidence.find((item) => item.kind === "profile_check");
  return reason.scope === "note"
    ? t("scope.note", { count: profile?.kind === "profile_check" ? profile.affectedSiblingCount : 1 })
    : t("scope.card");
}

export function sourceLabel(reason: TriageReason, t: TFunction): string {
  return reason.sources.map((source) => t(`sources.${source}`)).join(" · ");
}

export function evidenceLabel(evidence: TriageEvidence | undefined, t: TFunction): string {
  if (!evidence) return t("evidence.unavailable");
  if (evidence.kind === "leech_state") return t("evidence.lapses", { count: evidence.lapses });
  if (evidence.kind === "review_counts") return t("evidence.againPeriod", { count: evidence.againCount, days: periodDays(evidence.periodStartMs, evidence.periodEndMs) });
  if (evidence.kind === "pass_rate") return t("evidence.passRatePeriod", { value: Math.round(evidence.passRate * 100), days: periodDays(evidence.periodStartMs, evidence.periodEndMs) });
  if (evidence.kind === "answer_time") return t("evidence.answerTimePeriod", { value: new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(evidence.averageAnswerSeconds), days: periodDays(evidence.periodStartMs, evidence.periodEndMs) });
  if (evidence.kind === "signal_evidence") return t("evidence.signal", { again: evidence.againCount, reviews: evidence.reviewCount, days: evidence.windowDays });
  if (evidence.marker) return t("evidence.marker", { marker: evidence.marker });
  if (evidence.expectedTextLength !== null) return t("evidence.length", { actual: evidence.actualTextLength ?? 0, expected: evidence.expectedTextLength });
  return t("evidence.profile", { condition: evidence.expectedCondition });
}

export function stateLabel(item: TriageItem, t: TFunction): string {
  const state = item.cardState.state;
  const base = state ? t(`states.card.${state}`) : t("states.card.unknown");
  return item.cardState.flag ? `${base} · ${t("states.flag", { value: item.cardState.flag })}` : base;
}

export function recommendedStep(item: TriageItem, t: TFunction): string {
  return item.reasons.some((reason) => reason.family === "content")
    ? t("inspector.recommendProfile")
    : t("inspector.recommendAnki");
}

export function sourceStatusLabel(status: TriageSourceStatus, t: TFunction): string {
  const base = t(`coverage.status.${status.status}`);
  if (!status.errorCode) return base;
  return t(`coverage.errors.${status.errorCode}`, { defaultValue: t("coverage.errors.unknown", { status: base }) });
}

export function periodDays(start: number, end: number): number {
  const duration = Math.max(0, end - start);
  return Math.max(1, Math.round(duration / (24 * 60 * 60 * 1000)));
}
