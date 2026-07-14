import type { StatisticsResult } from "../../types/report";
import i18n from "../../i18n";
import { localeForLanguage } from "../../i18n/language";

export type StatisticsSemanticColor =
  | "reviews"
  | "study-time"
  | "introduced"
  | "success"
  | "previous"
  | "again"
  | "hard"
  | "good"
  | "easy"
  | "learning"
  | "review"
  | "relearning"
  | "young"
  | "mature"
  | "suspended"
  | "buried"
  | "unseen";

export const statisticsColorClass: Record<StatisticsSemanticColor, string> = {
  reviews: "stats-color-reviews",
  "study-time": "stats-color-study-time",
  introduced: "stats-color-introduced",
  success: "stats-color-success",
  previous: "stats-color-previous",
  again: "stats-color-again",
  hard: "stats-color-hard",
  good: "stats-color-good",
  easy: "stats-color-easy",
  learning: "stats-color-learning",
  review: "stats-color-review",
  relearning: "stats-color-relearning",
  young: "stats-color-young",
  mature: "stats-color-mature",
  suspended: "stats-color-suspended",
  buried: "stats-color-buried",
  unseen: "stats-color-unseen",
};

export interface StatisticsDeltaModel {
  text: string;
  direction: "increase" | "decrease" | "same" | "unavailable";
  comparisonStyle: "outline-dashed" | "unavailable";
}

type ComparisonValue = { delta?: number | null; direction?: string } | undefined;

export function comparisonValue(
  comparison: StatisticsResult["overview"]["comparison"],
  key: string,
): ComparisonValue {
  const value = comparison[key];
  return value && typeof value === "object" ? value as ComparisonValue : undefined;
}

export function deltaModel(
  comparison: StatisticsResult["overview"]["comparison"],
  key: string,
  kind: "relative" | "percentage-points" | "seconds" = "relative",
): StatisticsDeltaModel {
  if (comparison.status !== "available") {
    return { text: i18n.t("comparison.unavailable", { ns: "statistics" }), direction: "unavailable", comparisonStyle: "unavailable" };
  }
  const value = comparisonValue(comparison, key);
  if (!value || value.delta == null || !Number.isFinite(value.delta)) {
    return { text: i18n.t("comparison.unavailable", { ns: "statistics" }), direction: "unavailable", comparisonStyle: "unavailable" };
  }
  const delta = value.delta;
  const sign = delta > 0 ? "+" : delta < 0 ? "−" : "";
  const amount = new Intl.NumberFormat(localeForLanguage(i18n.resolvedLanguage || i18n.language), { maximumFractionDigits: 1 }).format(Math.abs(delta));
  const suffix = kind === "percentage-points" ? i18n.t("comparison.percentagePoints", { ns: "statistics" }) : kind === "seconds" ? i18n.t("comparison.seconds", { ns: "statistics" }) : "%";
  return {
    text: delta === 0 ? i18n.t("comparison.unchanged", { ns: "statistics" }) : i18n.t("comparison.delta", { ns: "statistics", value: `${sign}${amount}${suffix}` }),
    direction: delta > 0 ? "increase" : delta < 0 ? "decrease" : "same",
    comparisonStyle: "outline-dashed",
  };
}

export function selectDefaultDeckIds(rows: StatisticsResult["deckComparison"]["rows"], limit = 3): number[] {
  return [...rows]
    .filter((row) => row.reviews > 0 && row.confidence !== "insufficient")
    .sort((left, right) => right.reviews - left.reviews || left.fullName.localeCompare(right.fullName, "ru") || left.deckId - right.deckId)
    .slice(0, Math.max(0, limit))
    .map((row) => row.deckId);
}

export function futureDueTotal(result: StatisticsResult["load"], days: number): number {
  return result.futureDue.reduce((sum, row) => sum + (row.dayOffset <= days ? row.total : 0), 0);
}

export function describeSeries(values: Array<number | null | undefined>, label: string): string {
  const available = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  if (!available.length) return i18n.t("series.noData", { ns: "statistics", label });
  if (available.length === 1) return i18n.t("series.single", { ns: "statistics", label, value: formatCompactNumber(available[0]) });
  const peak = Math.max(...available);
  const total = available.reduce((sum, value) => sum + value, 0);
  return i18n.t("series.summary", { ns: "statistics", label, count: available.length, peak: formatCompactNumber(peak), total: formatCompactNumber(total) });
}

export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat(localeForLanguage(i18n.resolvedLanguage || i18n.language), { maximumFractionDigits: 1 }).format(value);
}
