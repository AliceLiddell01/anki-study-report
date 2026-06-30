const datePattern = /^\d{4}-\d{2}-\d{2}$/;
const shortMonths = ["янв.", "февр.", "мар.", "апр.", "мая", "июн.", "июл.", "авг.", "сент.", "окт.", "нояб.", "дек."];

export function isDateKey(value: unknown): value is string {
  if (typeof value !== "string" || !datePattern.test(value)) {
    return false;
  }
  const date = dateFromKey(value);
  return !Number.isNaN(date.getTime()) && toDateKey(date) === value;
}

export function toDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function todayDateKey(): string {
  return toDateKey(new Date());
}

export function parseDateKey(value: string): Date | null {
  if (!isDateKey(value)) {
    return null;
  }
  return dateFromKey(value);
}

export function addDays(dateKey: string, days: number): string | null {
  const date = parseDateKey(dateKey);
  if (!date || !Number.isFinite(days)) {
    return null;
  }
  date.setDate(date.getDate() + Math.trunc(days));
  return toDateKey(date);
}

export function daysBetween(start: string, end: string): number | null {
  const startDate = parseDateKey(start);
  const endDate = parseDateKey(end);
  if (!startDate || !endDate) {
    return null;
  }
  return Math.round((endDate.getTime() - startDate.getTime()) / 86_400_000);
}

export function compareDateKeys(a: string, b: string): number {
  return a.localeCompare(b);
}

export function formatShortDate(dateKey: string): string {
  if (!isDateKey(dateKey)) {
    return "Нет данных";
  }
  const [, month, day] = dateKey.split("-").map((part) => Number.parseInt(part, 10));
  return `${day} ${shortMonths[month - 1] ?? ""}`.trim();
}

export function monthKey(dateKey: string): string {
  return dateKey.slice(0, 7);
}

export function enumerateDateKeys(start: string, end: string): string[] {
  const distance = daysBetween(start, end);
  if (distance === null || distance < 0) {
    return [];
  }
  const result: string[] = [];
  for (let offset = 0; offset <= distance; offset += 1) {
    const next = addDays(start, offset);
    if (next) {
      result.push(next);
    }
  }
  return result;
}

function dateFromKey(value: string): Date {
  const [year, month, day] = value.split("-").map((part) => Number.parseInt(part, 10));
  return new Date(year, month - 1, day, 12, 0, 0, 0);
}
