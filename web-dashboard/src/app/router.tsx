import type { ReactNode } from "react";
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

export const navItems: Array<{ path: RoutePath; label: string; group: "Основное" | "Аналитика" | "Инструменты" | "Система" }> = [
  { path: "/home", label: "Главная", group: "Основное" },
  { path: "/profile", label: "Профиль", group: "Основное" },
  { path: "/decks", label: "Колоды", group: "Основное" },
  { path: "/cards", label: "Карточки", group: "Аналитика" },
  { path: "/calendar", label: "Календарь", group: "Аналитика" },
  { path: "/actions", label: "Действия", group: "Инструменты" },
  { path: "/integrations", label: "Интеграции", group: "Система" },
  { path: "/logs", label: "Логи", group: "Система" },
  { path: "/settings/server", label: "Настройки", group: "Система" },
];

const routePaths = new Set<RoutePath>(navItems.map((item) => item.path));

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
      return <IntegrationsPage />;
    case "/logs":
      return <LogsPage />;
    case "/settings/server":
      return <ServerSettingsPage />;
    case "/settings":
      return <SettingsPage report={report} />;
    case "/home":
    default:
      return <HomePage report={report} loadState={loadState} />;
  }
}
