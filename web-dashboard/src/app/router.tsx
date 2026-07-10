import type { ReactNode } from "react";
import SettingsLayout from "../layout/SettingsLayout";
import ActionsPage from "../pages/ActionsPage";
import CalendarPage from "../pages/CalendarPage";
import CardsPage from "../pages/CardsPage";
import DecksPage from "../pages/DecksPage";
import HomePage, { type LoadState } from "../pages/HomePage";
import IntegrationsPage from "../pages/IntegrationsPage";
import LogsPage from "../pages/LogsPage";
import ProfilePage from "../pages/ProfilePage";
import ServerSettingsPage from "../pages/ServerSettingsPage";
import SettingsPage from "../pages/SettingsPage";
import type { StudyReport } from "../types/report";

export type RoutePath =
  | "/home"
  | "/profile"
  | "/decks"
  | "/cards"
  | "/calendar"
  | "/actions"
  | "/settings"
  | "/settings/server"
  | "/integrations"
  | "/logs";

export const primaryNavItems: Array<{ path: RoutePath; label: string }> = [
  { path: "/home", label: "Сегодня" },
  { path: "/calendar", label: "Календарь" },
  { path: "/decks", label: "Колоды" },
  { path: "/cards", label: "Карточки" },
];

const routePaths = new Set<RoutePath>([
  "/home",
  "/profile",
  "/decks",
  "/cards",
  "/calendar",
  "/actions",
  "/settings",
  "/settings/server",
  "/integrations",
  "/logs",
]);

export function getRouteFromHash(hash: string): RoutePath {
  const rawPath = hash.replace(/^#/, "") || "/home";
  const normalized = rawPath === "/" ? "/home" : rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
  return routePaths.has(normalized as RoutePath) ? (normalized as RoutePath) : "/home";
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
    case "/actions":
      return <ActionsPage report={report} loadState={loadState} />;
    case "/integrations":
      return <SettingsLayout activeRoute={route}><IntegrationsPage /></SettingsLayout>;
    case "/logs":
      return <SettingsLayout activeRoute={route}><LogsPage /></SettingsLayout>;
    case "/settings/server":
      return <SettingsLayout activeRoute={route}><ServerSettingsPage /></SettingsLayout>;
    case "/settings":
      return <SettingsLayout activeRoute={route}><SettingsPage report={report} /></SettingsLayout>;
    case "/home":
    default:
      return <HomePage report={report} loadState={loadState} />;
  }
}
