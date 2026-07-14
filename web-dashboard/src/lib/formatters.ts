import i18n from "../i18n";
import { localeForLanguage } from "../i18n/language";

function locale(): string {
  return localeForLanguage(i18n.resolvedLanguage || i18n.language);
}

export function finiteNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function finiteNullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function formatInteger(value: unknown): string {
  return Math.round(finiteNumber(value)).toLocaleString(locale());
}

export function formatPercent(value: unknown): string {
  const normalized = finiteNullableNumber(value);
  if (normalized === null) {
    return i18n.t("state.noData", { ns: "common" });
  }
  return new Intl.NumberFormat(locale(), { style: "percent", maximumFractionDigits: 1 }).format(normalized);
}

export function formatSeconds(value: unknown): string {
  const normalized = finiteNullableNumber(value);
  if (normalized === null || normalized <= 0) {
    return i18n.t("state.noData", { ns: "common" });
  }
  const valueText = new Intl.NumberFormat(locale(), { maximumFractionDigits: 1 }).format(normalized);
  return i18n.t("units.secondsShort", { ns: "common", value: valueText });
}

export function formatCompactSeconds(value: unknown): string {
  const normalized = finiteNullableNumber(value);
  if (normalized === null || normalized <= 0) {
    return i18n.t("state.noData", { ns: "common" });
  }
  const valueText = new Intl.NumberFormat(locale(), { maximumFractionDigits: 1 }).format(normalized);
  return i18n.t("units.secondsShort", { ns: "common", value: valueText });
}

export function formatDurationSeconds(value: unknown, empty = i18n.t("state.noData", { ns: "common" })): string {
  const normalized = finiteNullableNumber(value);
  if (normalized === null || normalized <= 0) {
    return empty;
  }
  const totalSeconds = Math.round(normalized);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0 && minutes > 0) {
    return `${i18n.t("units.hoursShort", { ns: "common", value: formatInteger(hours) })} ${i18n.t("units.minutesShort", { ns: "common", value: formatInteger(minutes) })}`;
  }
  if (hours > 0) {
    return i18n.t("units.hoursShort", { ns: "common", value: formatInteger(hours) });
  }
  if (minutes > 0) {
    return i18n.t("units.minutesShort", { ns: "common", value: formatInteger(minutes) });
  }
  return i18n.t("units.secondsShort", { ns: "common", value: formatInteger(totalSeconds) });
}

export function safeText(value: unknown, fallback = i18n.t("state.noData", { ns: "common" })): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}
