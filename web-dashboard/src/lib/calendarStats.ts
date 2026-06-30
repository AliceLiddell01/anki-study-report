import type { CalendarDayStats, CalendarInsight, StreakInfo, StudyReport } from "../types/report";
import { addDays, compareDateKeys, enumerateDateKeys, formatShortDate, isDateKey, monthKey, todayDateKey } from "./dateUtils";
import { finiteNullableNumber, finiteNumber } from "./formatters";

export type CalendarMetric = "reviews" | "study_time" | "new_cards" | "pass_rate" | "forecast";
export type CalendarPeriod = "30" | "90" | "year";
export type CalendarHealthStatus = "stable" | "inconsistent" | "overload_risk" | "insufficient_data";

export interface CalendarSummary {
  currentStreak: number | null;
  bestStreak: number | null;
  activeDaysThisMonth: number | null;
  reviewsThisMonth: number | null;
  studySecondsThisMonth: number | null;
  averageReviewsPerActiveDay: number | null;
  mostProductiveDay: CalendarDayStats | null;
}

export interface CalendarModel {
  today: string;
  allDays: CalendarDayStats[];
  visibleDays: CalendarDayStats[];
  historicalDays: CalendarDayStats[];
  futureDays: CalendarDayStats[];
  streak: StreakInfo;
  summary: CalendarSummary;
  status: CalendarHealthStatus;
  statusText: string;
  insights: CalendarInsight[];
  metricAvailability: Record<CalendarMetric, boolean>;
  hasHistory: boolean;
  hasLimitedHistory: boolean;
  periodStart: string | null;
  periodEnd: string | null;
}

export function buildCalendarModel(
  report: StudyReport | null,
  period: CalendarPeriod,
  todayOverride?: string,
): CalendarModel {
  const today = resolveTodayKey(report, todayOverride);
  const dayMap = new Map<string, CalendarDayStats>();

  for (const day of report?.activity.days ?? []) {
    if (!isDateKey(day.date)) {
      continue;
    }
    const reviews = normalizeCount(day.reviews);
    const fail = Math.min(reviews, normalizeCount(day.again));
    const studySeconds = normalizeOptionalCount(day.studySeconds);
    dayMap.set(day.date, {
      date: day.date,
      reviews,
      newCards: normalizeCount(day.newCards),
      fail,
      pass: Math.max(0, reviews - fail),
      passRate: reviews > 0 ? roundRate((reviews - fail) / reviews) : null,
      studySeconds: studySeconds ?? 0,
      avgAnswerSeconds: reviews > 0 && studySeconds ? roundOne(studySeconds / reviews) : null,
      isToday: day.date === today,
      isFuture: false,
      dueForecast: null,
    });
  }

  const comparisonToday = report?.comparison?.today;
  if (comparisonToday && isDateKey(comparisonToday.date)) {
    mergeHistoricalDay(dayMap, comparisonToday.date, {
      reviews: normalizeCount(comparisonToday.reviews),
      newCards: normalizeCount(comparisonToday.newCards),
      pass: normalizeCount(comparisonToday.pass),
      fail: normalizeCount(comparisonToday.fail),
      passRate: finiteNullableNumber(comparisonToday.passRate),
      studySeconds: normalizeOptionalCount(comparisonToday.studySeconds) ?? 0,
      avgAnswerSeconds: finiteNullableNumber(comparisonToday.avgAnswerSeconds),
      activeDecks: normalizeCount(comparisonToday.activeDecks),
      isToday: comparisonToday.date === today,
    });
  }

  for (const item of report?.forecast.daily ?? []) {
    if (!isDateKey(item.date)) {
      continue;
    }
    const existing = dayMap.get(item.date);
    dayMap.set(item.date, {
      date: item.date,
      reviews: existing?.reviews ?? 0,
      newCards: existing?.newCards ?? 0,
      fail: existing?.fail ?? 0,
      pass: existing?.pass ?? 0,
      passRate: existing?.passRate ?? null,
      studySeconds: existing?.studySeconds ?? 0,
      avgAnswerSeconds: existing?.avgAnswerSeconds ?? null,
      activeDecks: existing?.activeDecks,
      isToday: item.date === today,
      isFuture: compareDateKeys(item.date, today) > 0,
      dueForecast: normalizeCount(item.due),
      learning: normalizeCount(item.learningDue),
    });
  }

  if (!dayMap.size) {
    return emptyCalendarModel(today, period);
  }

  const sortedKnownDays = [...dayMap.values()].sort((a, b) => compareDateKeys(a.date, b.date));
  const historicalKnown = sortedKnownDays.filter((day) => !day.isFuture && compareDateKeys(day.date, today) <= 0);
  const firstHistoricalDate = historicalKnown[0]?.date ?? null;
  const lastHistoricalDate = historicalKnown[historicalKnown.length - 1]?.date ?? null;
  const periodStart = firstHistoricalDate ? maxDate(firstHistoricalDate, periodStartFor(today, period)) : today;
  const periodEnd = maxDate(lastHistoricalDate ?? today, today);
  const visibleHistorical = firstHistoricalDate ? fillHistoricalDays(dayMap, periodStart, periodEnd, today) : [];
  const futureDays = sortedKnownDays.filter((day) => day.isFuture).sort((a, b) => compareDateKeys(a.date, b.date));
  const visibleDays = [...visibleHistorical, ...futureDays];
  const historicalDays = visibleHistorical.filter((day) => compareDateKeys(day.date, today) <= 0);
  const allHistoricalDays = firstHistoricalDate ? fillHistoricalDays(dayMap, firstHistoricalDate, periodEnd, today) : [];
  const streak = calculateStreakInfo(allHistoricalDays, today);
  const summary = buildSummary(historicalDays, today, streak);
  const status = calendarHealthStatus(historicalDays, futureDays, report);
  const insights = buildInsights(historicalDays, futureDays, summary, status, report);

  return {
    today,
    allDays: sortedKnownDays,
    visibleDays,
    historicalDays,
    futureDays,
    streak,
    summary,
    status,
    statusText: calendarStatusText(status),
    insights,
    metricAvailability: metricAvailability(visibleDays),
    hasHistory: historicalDays.some((day) => isActiveDay(day)),
    hasLimitedHistory: historicalDays.length > 0 && historicalDays.length < periodLength(period),
    periodStart: visibleDays[0]?.date ?? null,
    periodEnd: visibleDays[visibleDays.length - 1]?.date ?? null,
  };
}

export function calculateStreakInfo(days: CalendarDayStats[], today: string): StreakInfo {
  const historicalDays = days
    .filter((day) => compareDateKeys(day.date, today) <= 0)
    .sort((a, b) => compareDateKeys(a.date, b.date));
  const activeDates = new Set(historicalDays.filter(isActiveDay).map((day) => day.date));
  const todayActive = activeDates.has(today);
  const yesterday = addDays(today, -1);
  let cursor = todayActive ? today : yesterday && activeDates.has(yesterday) ? yesterday : null;
  let currentStreak = 0;
  while (cursor && activeDates.has(cursor)) {
    currentStreak += 1;
    cursor = addDays(cursor, -1);
  }

  let bestStreak = 0;
  let current = 0;
  for (const day of historicalDays) {
    if (isActiveDay(day)) {
      current += 1;
      bestStreak = Math.max(bestStreak, current);
    } else {
      current = 0;
    }
  }

  return {
    currentStreak,
    bestStreak,
    activeDays: activeDates.size,
    totalDays: historicalDays.length,
  };
}

export function isActiveDay(day: CalendarDayStats): boolean {
  return normalizeCount(day.reviews) > 0 || normalizeCount(day.studySeconds) > 0;
}

export function calendarMetricValue(day: CalendarDayStats, metric: CalendarMetric): number | null {
  if (metric === "reviews") {
    return normalizeCount(day.reviews);
  }
  if (metric === "study_time") {
    return normalizeOptionalCount(day.studySeconds);
  }
  if (metric === "new_cards") {
    return normalizeCount(day.newCards);
  }
  if (metric === "pass_rate") {
    return finiteNullableNumber(day.passRate);
  }
  return normalizeOptionalCount(day.dueForecast);
}

export function heatmapIntensity(day: CalendarDayStats, metric: CalendarMetric, maxValue: number): number {
  const value = calendarMetricValue(day, metric);
  if (value === null || value <= 0) {
    return 0;
  }
  if (metric === "pass_rate") {
    return Math.max(0.12, Math.min(1, value));
  }
  return Math.max(0.12, Math.min(1, value / Math.max(1, maxValue)));
}

export function maxMetricValue(days: CalendarDayStats[], metric: CalendarMetric): number {
  if (metric === "pass_rate") {
    return 1;
  }
  return Math.max(1, ...days.map((day) => calendarMetricValue(day, metric) ?? 0));
}

function mergeHistoricalDay(
  dayMap: Map<string, CalendarDayStats>,
  date: string,
  incoming: Partial<CalendarDayStats>,
) {
  const existing = dayMap.get(date);
  const reviews = incoming.reviews ?? existing?.reviews ?? 0;
  const fail = Math.min(reviews, incoming.fail ?? existing?.fail ?? 0);
  const pass = incoming.pass ?? existing?.pass ?? Math.max(0, reviews - fail);
  dayMap.set(date, {
    date,
    reviews,
    newCards: incoming.newCards ?? existing?.newCards ?? 0,
    fail,
    pass,
    passRate: incoming.passRate ?? existing?.passRate ?? (reviews > 0 ? roundRate(pass / reviews) : null),
    studySeconds: incoming.studySeconds ?? existing?.studySeconds ?? 0,
    avgAnswerSeconds: incoming.avgAnswerSeconds ?? existing?.avgAnswerSeconds ?? null,
    activeDecks: incoming.activeDecks ?? existing?.activeDecks,
    isToday: incoming.isToday ?? existing?.isToday ?? false,
    isFuture: false,
    dueForecast: existing?.dueForecast ?? null,
  });
}

function fillHistoricalDays(dayMap: Map<string, CalendarDayStats>, start: string, end: string, today: string): CalendarDayStats[] {
  return enumerateDateKeys(start, end).map((date) => {
    const existing = dayMap.get(date);
    if (existing) {
      return { ...existing, isToday: date === today, isFuture: false };
    }
    return {
      date,
      reviews: 0,
      newCards: 0,
      pass: 0,
      fail: 0,
      passRate: null,
      studySeconds: 0,
      avgAnswerSeconds: null,
      isToday: date === today,
      isFuture: false,
      dueForecast: null,
    };
  });
}

function buildSummary(days: CalendarDayStats[], today: string, streak: StreakInfo): CalendarSummary {
  const currentMonth = monthKey(today);
  const monthDays = days.filter((day) => monthKey(day.date) === currentMonth);
  const activeMonthDays = monthDays.filter(isActiveDay);
  const monthStudySeconds = monthDays.reduce((sum, day) => sum + normalizeCount(day.studySeconds), 0);
  const monthReviews = monthDays.reduce((sum, day) => sum + normalizeCount(day.reviews), 0);
  const mostProductiveDay =
    [...monthDays].sort((a, b) => normalizeCount(b.reviews) - normalizeCount(a.reviews))[0] ?? null;
  const meaningfulBestDay = mostProductiveDay && mostProductiveDay.reviews > 0 ? mostProductiveDay : null;

  return {
    currentStreak: days.length ? streak.currentStreak : null,
    bestStreak: days.length ? streak.bestStreak : null,
    activeDaysThisMonth: monthDays.length ? activeMonthDays.length : null,
    reviewsThisMonth: monthDays.length ? monthReviews : null,
    studySecondsThisMonth: monthStudySeconds > 0 ? monthStudySeconds : null,
    averageReviewsPerActiveDay: activeMonthDays.length ? Math.round(monthReviews / activeMonthDays.length) : null,
    mostProductiveDay: meaningfulBestDay,
  };
}

function calendarHealthStatus(
  historicalDays: CalendarDayStats[],
  futureDays: CalendarDayStats[],
  report: StudyReport | null,
): CalendarHealthStatus {
  if (historicalDays.length < 3 || historicalDays.filter(isActiveDay).length < 1) {
    return "insufficient_data";
  }
  if (hasOverloadRisk(historicalDays, futureDays, report)) {
    return "overload_risk";
  }
  const last7 = historicalDays.slice(-7);
  const activeLast7 = last7.filter(isActiveDay).length;
  if (activeLast7 >= 5 && longestGap(historicalDays) < 3) {
    return "stable";
  }
  return "inconsistent";
}

function hasOverloadRisk(
  historicalDays: CalendarDayStats[],
  futureDays: CalendarDayStats[],
  report: StudyReport | null,
): boolean {
  if (report?.forecast.overloadRisk === "warning" || report?.forecast.overloadRisk === "danger") {
    return true;
  }
  const activeReviews = historicalDays.map((day) => day.reviews).filter((value) => value > 0);
  if (!activeReviews.length || !futureDays.length) {
    return false;
  }
  const average = activeReviews.reduce((sum, value) => sum + value, 0) / activeReviews.length;
  return futureDays.slice(0, 7).some((day) => normalizeCount(day.dueForecast) >= Math.max(30, average * 1.6));
}

function buildInsights(
  historicalDays: CalendarDayStats[],
  futureDays: CalendarDayStats[],
  summary: CalendarSummary,
  status: CalendarHealthStatus,
  report: StudyReport | null,
): CalendarInsight[] {
  if (status === "insufficient_data") {
    return [
      {
        tone: "neutral",
        title: "Данных пока мало",
        text: "Календарь станет полезнее после нескольких дней учёбы.",
      },
    ];
  }

  const last7 = historicalDays.slice(-7);
  const activeLast7 = last7.filter(isActiveDay).length;
  const insights: CalendarInsight[] = [
    {
      tone: activeLast7 >= 5 ? "positive" : "warning",
      title: activeLast7 >= 5 ? "Регулярная неделя" : "Есть пропуски",
      text: `Вы учились ${activeLast7} дней из последних ${last7.length}.`,
    },
  ];

  if (summary.mostProductiveDay) {
    insights.push({
      tone: "positive",
      title: "Самый продуктивный день месяца",
      text: `${formatShortDate(summary.mostProductiveDay.date)} - ${summary.mostProductiveDay.reviews.toLocaleString("ru-RU")} повторений.`,
    });
  }

  const weekDelta = report?.comparison?.comparisons.week.reviews.percentDelta;
  if (weekDelta !== null && weekDelta !== undefined && Number.isFinite(weekDelta)) {
    insights.push({
      tone: weekDelta >= 10 ? "positive" : weekDelta <= -20 ? "warning" : "neutral",
      title: weekDelta >= 10 ? "Неделя активнее прошлой" : weekDelta <= -20 ? "Неделя тише прошлой" : "Неделя около нормы",
      text:
        weekDelta >= 10
          ? "На этой неделе активность выше прошлой."
          : weekDelta <= -20
            ? "На этой неделе повторений заметно меньше, чем на прошлой."
            : "Текущая неделя близка к прошлой по объёму.",
    });
  }

  if (status === "overload_risk") {
    insights.push({
      tone: "warning",
      title: "Риск перегруза",
      text: "В ближайшие дни forecast заметно выше обычной активности.",
    });
  } else if (futureDays.length) {
    const nextDue = futureDays.slice(0, 7).reduce((sum, day) => sum + normalizeCount(day.dueForecast), 0);
    insights.push({
      tone: "neutral",
      title: "Forecast на неделю",
      text: `В ближайшие 7 дней ожидается около ${nextDue.toLocaleString("ru-RU")} due cards.`,
    });
  }

  return insights.slice(0, 5);
}

function metricAvailability(days: CalendarDayStats[]): Record<CalendarMetric, boolean> {
  return {
    reviews: days.some((day) => !day.isFuture),
    study_time: days.some((day) => normalizeCount(day.studySeconds) > 0),
    new_cards: days.some((day) => normalizeCount(day.newCards) > 0),
    pass_rate: days.some((day) => finiteNullableNumber(day.passRate) !== null),
    forecast: days.some((day) => finiteNullableNumber(day.dueForecast) !== null),
  };
}

function emptyCalendarModel(today: string, period: CalendarPeriod): CalendarModel {
  return {
    today,
    allDays: [],
    visibleDays: [],
    historicalDays: [],
    futureDays: [],
    streak: { currentStreak: 0, bestStreak: 0, activeDays: 0, totalDays: 0 },
    summary: {
      currentStreak: null,
      bestStreak: null,
      activeDaysThisMonth: null,
      reviewsThisMonth: null,
      studySecondsThisMonth: null,
      averageReviewsPerActiveDay: null,
      mostProductiveDay: null,
    },
    status: "insufficient_data",
    statusText: calendarStatusText("insufficient_data"),
    insights: [
      {
        tone: "neutral",
        title: "Недостаточно истории для календаря",
        text: "Данные появятся после накопления дневной статистики.",
      },
    ],
    metricAvailability: {
      reviews: false,
      study_time: false,
      new_cards: false,
      pass_rate: false,
      forecast: false,
    },
    hasHistory: false,
    hasLimitedHistory: false,
    periodStart: null,
    periodEnd: null,
  };
}

function resolveTodayKey(report: StudyReport | null, todayOverride?: string): string {
  if (todayOverride && isDateKey(todayOverride)) {
    return todayOverride;
  }
  const reportToday = report?.comparison?.today.date;
  if (reportToday && isDateKey(reportToday)) {
    return reportToday;
  }
  return todayDateKey();
}

function calendarStatusText(status: CalendarHealthStatus): string {
  return {
    stable: "Стабильная неделя: вы учились большую часть последних дней.",
    inconsistent: "Есть пропуски: регулярность пока нестабильная.",
    overload_risk: "Возможен перегруз: ближайшая очередь выше обычной.",
    insufficient_data: "Пока мало данных для оценки регулярности.",
  }[status];
}

function periodStartFor(today: string, period: CalendarPeriod): string {
  return addDays(today, -periodLength(period) + 1) ?? today;
}

function periodLength(period: CalendarPeriod): number {
  return period === "30" ? 30 : period === "90" ? 90 : 365;
}

function maxDate(a: string, b: string): string {
  return compareDateKeys(a, b) >= 0 ? a : b;
}

function longestGap(days: CalendarDayStats[]): number {
  let longest = 0;
  let current = 0;
  for (const day of days) {
    if (isActiveDay(day)) {
      current = 0;
    } else {
      current += 1;
      longest = Math.max(longest, current);
    }
  }
  return longest;
}

function normalizeCount(value: unknown): number {
  return Math.max(0, Math.round(finiteNumber(value)));
}

function normalizeOptionalCount(value: unknown): number | null {
  const normalized = finiteNullableNumber(value);
  if (normalized === null) {
    return null;
  }
  return Math.max(0, Math.round(normalized));
}

function roundRate(value: number): number {
  return Math.round(value * 10_000) / 10_000;
}

function roundOne(value: number): number {
  return Math.round(value * 10) / 10;
}
