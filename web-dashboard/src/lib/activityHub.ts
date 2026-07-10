import type {
  ActivityFeedDay,
  ActivityHubDay,
  ActivityHubModel,
  ActivityMetric,
  ActivityPeriod,
  ActivityWeekSummary,
} from "../types/report";

export function activityDaysForPeriod(hub: ActivityHubModel, period: ActivityPeriod): ActivityHubDay[] {
  const bounds = hub.periods[period] ?? hub.periods["90d"];
  return hub.days.filter((day) => day.date >= bounds.start && day.date <= bounds.end);
}

export function activityOverview(days: ActivityHubDay[], currentStreak: number) {
  const active = days.filter((day) => day.availability === "active");
  let bestStreak = 0;
  let running = 0;
  for (const day of days) {
    if (day.availability === "active") {
      running += 1;
      bestStreak = Math.max(bestStreak, running);
    } else if (day.availability === "inactive") {
      running = 0;
    } else {
      running = 0;
    }
  }
  return {
    activeDays: active.length,
    reviews: active.reduce((sum, day) => sum + (day.reviews ?? 0), 0),
    currentStreak,
    bestStreak,
  };
}

export function activityMetricValue(day: ActivityHubDay, metric: ActivityMetric): number | null {
  if (day.availability === "unavailable") return null;
  if (metric === "reviews") return day.reviews ?? 0;
  if (metric === "new_cards") return day.newCards ?? 0;
  if (metric === "study_time") return day.studySeconds ?? null;
  return day.successRate ?? null;
}

export function activityMetricIntensity(day: ActivityHubDay, metric: ActivityMetric, days: ActivityHubDay[]): number {
  const value = activityMetricValue(day, metric);
  if (value === null || value <= 0) return 0;
  const values = days
    .map((item) => activityMetricValue(item, metric))
    .filter((item): item is number => item !== null && item > 0)
    .sort((a, b) => a - b);
  if (!values.length) return 0;
  const cap = values[Math.min(values.length - 1, Math.floor((values.length - 1) * 0.9))] || values[values.length - 1];
  return Math.max(0.16, Math.min(1, value / Math.max(cap, Number.EPSILON)));
}

export function visibleActivityFeed(
  hub: ActivityHubModel,
  period: ActivityPeriod,
  activeLimit: number,
): { days: ActivityFeedDay[]; weeks: ActivityWeekSummary[]; hasMore: boolean } {
  const bounds = hub.periods[period] ?? hub.periods["90d"];
  const eligible = hub.feed.days.filter((entry) => entry.date >= bounds.start && entry.date <= bounds.end);
  const days = eligible.slice(0, activeLimit);
  const oldest = days[days.length - 1]?.date ?? bounds.end;
  const weeks = hub.feed.weeks.filter(
    (week) => week.weekEnd >= oldest && week.weekEnd >= bounds.start && week.weekEnd <= bounds.end,
  );
  return { days, weeks, hasMore: eligible.length > days.length };
}

export function activityDayMap(days: ActivityHubDay[]): Map<string, ActivityHubDay> {
  return new Map(days.map((day) => [day.date, day]));
}
