import type { DeckPerformance, Status } from "../types/report";
import { finiteNumber, finiteNullableNumber, formatPercent } from "./formatters";

export type DeckHealthStatus = Status;

export interface DeckHealth {
  status: DeckHealthStatus;
  statusLabel: "good" | "normal" | "warning" | "danger";
  reason: string;
  action: string;
  hasEnoughData: boolean;
  passRate: number | null;
  failRate: number | null;
  averageAnswerSeconds: number | null;
  totalReviews: number;
  failCount: number;
  newCards: number;
}

const MIN_REVIEWS_FOR_STRONG_STATUS = 10;
const SLOW_ANSWER_SECONDS = 18;

export function buildDeckHealth(deck: DeckPerformance): DeckHealth {
  const totalReviews = Math.max(0, finiteNumber(deck.totalReviews));
  const failCount = Math.max(0, finiteNumber(deck.failCount));
  const newCards = Math.max(0, finiteNumber(deck.newCards));
  const passRate = boundedRate(deck.passRate);
  const reportedFailRate = boundedRate(deck.failRate);
  const failRate = reportedFailRate ?? (totalReviews > 0 ? Math.min(1, failCount / totalReviews) : null);
  const averageAnswerSeconds = finiteNullableNumber(deck.averageAnswerSeconds);
  const hasEnoughData = totalReviews >= MIN_REVIEWS_FOR_STRONG_STATUS;

  if (totalReviews <= 0) {
    return {
      status: "neutral",
      statusLabel: "normal",
      reason: "Сегодня по колоде нет повторений.",
      action: "Нужно больше данных для оценки.",
      hasEnoughData: false,
      passRate,
      failRate,
      averageAnswerSeconds,
      totalReviews,
      failCount,
      newCards,
    };
  }

  if (!hasEnoughData) {
    return {
      status: "neutral",
      statusLabel: "normal",
      reason: "Данных мало, вывод предварительный.",
      action: "Нужно больше данных для оценки.",
      hasEnoughData: false,
      passRate,
      failRate,
      averageAnswerSeconds,
      totalReviews,
      failCount,
      newCards,
    };
  }

  const slowAnswers = averageAnswerSeconds !== null && averageAnswerSeconds >= SLOW_ANSWER_SECONDS;
  const status = resolveStatus(passRate, failRate, slowAnswers);
  return {
    status,
    statusLabel: status === "neutral" ? "normal" : status,
    reason: buildReason(status, passRate, failRate, slowAnswers),
    action: buildAction(status, slowAnswers),
    hasEnoughData,
    passRate,
    failRate,
    averageAnswerSeconds,
    totalReviews,
    failCount,
    newCards,
  };
}

export function buildDeckHealthRows(decks: DeckPerformance[]): Array<DeckPerformance & { health: DeckHealth }> {
  return decks.map((deck) => ({ ...deck, health: buildDeckHealth(deck) }));
}

export function countDeckStatuses(rows: Array<{ health: DeckHealth }>) {
  return rows.reduce(
    (counts, row) => {
      counts[row.health.statusLabel] += 1;
      return counts;
    },
    { good: 0, normal: 0, warning: 0, danger: 0 },
  );
}

export function averageRate(values: Array<number | null>): number | null {
  const valid = values.filter((value): value is number => value !== null && Number.isFinite(value));
  if (!valid.length) {
    return null;
  }
  return valid.reduce((sum, value) => sum + value, 0) / valid.length;
}

export function averageNumber(values: Array<number | null>): number | null {
  return averageRate(values);
}

function resolveStatus(passRate: number | null, failRate: number | null, slowAnswers: boolean): Status {
  if (passRate !== null && passRate < 0.7) {
    return "danger";
  }
  if (failRate !== null && failRate >= 0.32) {
    return "danger";
  }
  if ((passRate !== null && passRate < 0.8) || (failRate !== null && failRate >= 0.2) || slowAnswers) {
    return "warning";
  }
  if (passRate !== null && passRate >= 0.9 && (failRate === null || failRate <= 0.1) && !slowAnswers) {
    return "good";
  }
  return "neutral";
}

function buildReason(status: Status, passRate: number | null, failRate: number | null, slowAnswers: boolean): string {
  if (status === "good") {
    return "Колода выглядит стабильной: высокая успешность и мало ошибок.";
  }
  if (status === "danger") {
    if (passRate !== null && passRate < 0.7) {
      return `Качество сильно ниже нормы: успешность ${formatPercent(passRate)}.`;
    }
    return "Много ошибок относительно количества повторений.";
  }
  if (status === "warning") {
    if (passRate !== null && passRate < 0.8) {
      return `Качество ниже нормы: успешность ${formatPercent(passRate)}.`;
    }
    if (failRate !== null && failRate >= 0.2) {
      return "Много ошибок относительно количества повторений.";
    }
    if (slowAnswers) {
      return "Ответы идут медленно, колода может требовать ручного разбора.";
    }
  }
  return "Колода без явных проблем по текущим данным.";
}

function buildAction(status: Status, slowAnswers: boolean): string {
  if (status === "good") {
    return "Продолжать в обычном режиме.";
  }
  if (status === "danger") {
    return "Временно не добавлять новые карточки.";
  }
  if (status === "warning") {
    return slowAnswers ? "Проверить сложные карточки вручную." : "Разобрать ошибки перед добавлением новых.";
  }
  return "Продолжать в обычном режиме.";
}

function boundedRate(value: unknown): number | null {
  const normalized = finiteNullableNumber(value);
  if (normalized === null) {
    return null;
  }
  return Math.min(1, Math.max(0, normalized));
}
