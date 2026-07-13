import { lazy, type ReactNode } from "react";
import SettingsLayout from "../layout/SettingsLayout";
import ActionsPage from "../pages/ActionsPage";
import CalendarPage from "../pages/CalendarPage";
import CardsPage from "../pages/CardsPage";
import DecksPage from "../pages/DecksPage";
import HomePage, { type LoadState } from "../pages/HomePage";
import IntegrationsPage from "../pages/IntegrationsPage";
import LogsPage from "../pages/LogsPage";
import ProfilePage from "../pages/ProfilePage";
import ReportSettingsPage from "../pages/ReportSettingsPage";
import ServerSettingsPage from "../pages/ServerSettingsPage";
import SettingsPage from "../pages/SettingsPage";
import type { StudyReport } from "../types/report";

const StatisticsPage = lazy(() => import("../pages/StatisticsPage"));
const FsrsStatisticsPage = lazy(() => import("../pages/FsrsStatisticsPage"));

export type RoutePath =
  | "/home"
  | "/profile"
  | "/decks"
  | "/cards"
  | "/calendar"
  | "/stats"
  | "/stats/quality"
  | "/stats/load"
  | "/stats/progress"
  | "/stats/decks"
  | "/stats/fsrs"
  | "/stats/fsrs/memory"
  | "/stats/fsrs/calibration"
  | "/stats/fsrs/steps"
  | "/stats/fsrs/simulator"
  | "/actions"
  | "/settings"
  | "/settings/data"
  | "/settings/server"
  | "/settings/sources"
  | "/settings/logs";

export const primaryNavItems: Array<{ path: RoutePath; label: string }> = [
  { path: "/home", label: "Сегодня" },
  { path: "/calendar", label: "Активность" },
  { path: "/stats", label: "Статистика" },
  { path: "/decks", label: "Колоды" },
  { path: "/cards", label: "Карточки" },
];

const routePaths = new Set<RoutePath>([
  "/home",
  "/profile",
  "/decks",
  "/cards",
  "/calendar",
  "/stats",
  "/stats/quality",
  "/stats/load",
  "/stats/progress",
  "/stats/decks",
  "/stats/fsrs",
  "/stats/fsrs/memory",
  "/stats/fsrs/calibration",
  "/stats/fsrs/steps",
  "/stats/fsrs/simulator",
  "/actions",
  "/settings",
  "/settings/data",
  "/settings/server",
  "/settings/sources",
  "/settings/logs",
]);

const compatibilityRoutes: Record<string, RoutePath> = {
  "/integrations": "/settings/sources",
  "/logs": "/settings/logs",
};

export function getRouteFromHash(hash: string): RoutePath {
  const rawPath = hash.replace(/^#/, "") || "/home";
  const normalized = rawPath === "/" ? "/home" : rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
  return compatibilityRoutes[normalized] ?? (routePaths.has(normalized as RoutePath) ? (normalized as RoutePath) : "/home");
}

export function compatibilityRedirectForHash(hash: string): RoutePath | null {
  const rawPath = hash.replace(/^#/, "") || "/home";
  const normalized = rawPath === "/" ? "/home" : rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
  return compatibilityRoutes[normalized] ?? null;
}

export function renderRoute(
  route: RoutePath,
  report: StudyReport | null,
  loadState: LoadState,
  onReportUpdated?: (report: StudyReport) => void,
): ReactNode {
  switch (route) {
    case "/profile":
      return <ProfilePage report={report} onReportUpdated={onReportUpdated} />;
    case "/decks":
      return <DecksPage report={report} loadState={loadState} />;
    case "/cards":
      return <CardsPage report={report} loadState={loadState} />;
    case "/calendar":
      return <CalendarPage report={report} loadState={loadState} />;
    case "/stats":
      return <StatisticsPage report={report} loadState={loadState} section="overview" />;
    case "/stats/quality":
      return <StatisticsPage report={report} loadState={loadState} section="quality" />;
    case "/stats/load":
      return <StatisticsPage report={report} loadState={loadState} section="load" />;
    case "/stats/progress":
      return <StatisticsPage report={report} loadState={loadState} section="progress" />;
    case "/stats/decks":
      return <StatisticsPage report={report} loadState={loadState} section="decks" />;
    case "/stats/fsrs":
      return <FsrsStatisticsPage report={report} loadState={loadState} section="overview" />;
    case "/stats/fsrs/memory":
      return <FsrsStatisticsPage report={report} loadState={loadState} section="memory" />;
    case "/stats/fsrs/calibration":
      return <FsrsStatisticsPage report={report} loadState={loadState} section="calibration" />;
    case "/stats/fsrs/steps":
      return <FsrsStatisticsPage report={report} loadState={loadState} section="steps" />;
    case "/stats/fsrs/simulator":
      return <FsrsStatisticsPage report={report} loadState={loadState} section="simulator" />;
    case "/actions":
      return <ActionsPage report={report} loadState={loadState} />;
    case "/settings/sources":
      return <SettingsLayout activeRoute={route}><IntegrationsPage /></SettingsLayout>;
    case "/settings/logs":
      return <SettingsLayout activeRoute={route}><LogsPage /></SettingsLayout>;
    case "/settings/server":
      return <SettingsLayout activeRoute={route}><ServerSettingsPage /></SettingsLayout>;
    case "/settings/data":
      return <SettingsLayout activeRoute={route}><SettingsPage report={report} /></SettingsLayout>;
    case "/settings":
      return <SettingsLayout activeRoute={route}><ReportSettingsPage onReportUpdated={onReportUpdated} /></SettingsLayout>;
    case "/home":
    default:
      return <HomePage report={report} loadState={loadState} />;
  }
}
