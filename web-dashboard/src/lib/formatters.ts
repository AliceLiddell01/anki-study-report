export function finiteNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function finiteNullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function formatInteger(value: unknown): string {
  return Math.round(finiteNumber(value)).toLocaleString("ru-RU");
}

export function formatPercent(value: unknown): string {
  const normalized = finiteNullableNumber(value);
  if (normalized === null) {
    return "Нет данных";
  }
  return `${Math.round(normalized * 100)}%`;
}

export function formatSeconds(value: unknown): string {
  const normalized = finiteNullableNumber(value);
  if (normalized === null || normalized <= 0) {
    return "Нет данных";
  }
  return `${normalized.toFixed(normalized % 1 === 0 ? 0 : 1)} сек`;
}

export function formatCompactSeconds(value: unknown): string {
  const normalized = finiteNullableNumber(value);
  if (normalized === null || normalized <= 0) {
    return "Нет данных";
  }
  return `${normalized.toFixed(normalized % 1 === 0 ? 0 : 1)}s`;
}

export function formatDurationSeconds(value: unknown, empty = "Нет данных"): string {
  const normalized = finiteNullableNumber(value);
  if (normalized === null || normalized <= 0) {
    return empty;
  }
  const totalSeconds = Math.round(normalized);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0 && minutes > 0) {
    return `${hours} ч ${minutes} мин`;
  }
  if (hours > 0) {
    return `${hours} ч`;
  }
  if (minutes > 0) {
    return `${minutes} мин`;
  }
  return `${totalSeconds} сек`;
}

export function safeText(value: unknown, fallback = "Нет данных"): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}
