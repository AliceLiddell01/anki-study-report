import type { ReactNode } from "react";
import BrowsePage from "../pages/BrowsePage";
import CalendarPage from "../pages/CalendarPage";
import CardsPage from "../pages/CardsPage";
import DecksPage from "../pages/DecksPage";
import FsrsPage from "../pages/FsrsPage";
import HomePage, { type LoadState } from "../pages/HomePage";
import ProfilePage from "../pages/ProfilePage";
import SettingsPage from "../pages/SettingsPage";
import StatsPage from "../pages/StatsPage";
import type { StudyReport } from "../types/report";

export type RoutePath =
  | "/home"
  | "/profile"
  | "/decks"
  | "/cards"
  | "/stats"
  | "/calendar"
  | "/fsrs"
  | "/browse"
  | "/settings";

export const navItems: Array<{ path: RoutePath; label: string }> = [
  { path: "/home", label: "Home" },
  { path: "/profile", label: "Profile" },
  { path: "/decks", label: "Decks" },
  { path: "/cards", label: "Cards" },
  { path: "/stats", label: "Stats" },
  { path: "/calendar", label: "Calendar" },
  { path: "/fsrs", label: "FSRS" },
  { path: "/browse", label: "Browse" },
  { path: "/settings", label: "Settings" },
];

const routePaths = new Set<RoutePath>(navItems.map((item) => item.path));

export function getRouteFromHash(hash: string): RoutePath {
  const rawPath = hash.replace(/^#/, "") || "/home";
  const normalized = rawPath === "/" ? "/home" : rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
  return routePaths.has(normalized as RoutePath) ? (normalized as RoutePath) : "/home";
}

export function renderRoute(route: RoutePath, report: StudyReport | null, loadState: LoadState): ReactNode {
  switch (route) {
    case "/profile":
      return <ProfilePage />;
    case "/decks":
      return <DecksPage report={report} loadState={loadState} />;
    case "/cards":
      return <CardsPage />;
    case "/stats":
      return <StatsPage />;
    case "/calendar":
      return <CalendarPage report={report} loadState={loadState} />;
    case "/fsrs":
      return <FsrsPage />;
    case "/browse":
      return <BrowsePage />;
    case "/settings":
      return <SettingsPage report={report} />;
    case "/home":
    default:
      return <HomePage report={report} loadState={loadState} />;
  }
}
