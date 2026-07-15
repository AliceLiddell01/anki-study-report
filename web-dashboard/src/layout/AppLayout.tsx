import type { ReactNode } from "react";
import type { RoutePath } from "../app/router";
import { useThemePreference } from "../lib/theme";
import GlobalUtilityDock from "./GlobalUtilityDock";
import TopNav from "./TopNav";

function AppLayout({ activeRoute, children, onOpenWhatsNew = () => undefined }: { activeRoute: RoutePath; children: ReactNode; onOpenWhatsNew?: () => void }) {
  const { resolvedTheme, setThemeMode } = useThemePreference();

  return (
    <div className="min-h-screen bg-ink-950 text-report-text">
      <TopNav activeRoute={activeRoute} onOpenWhatsNew={onOpenWhatsNew} />
      <main className="page-enter app-content-safe-inset mx-auto w-full max-w-[1760px] px-4 py-5 sm:px-6 lg:px-8">{children}</main>
      <GlobalUtilityDock resolvedTheme={resolvedTheme} onThemeChange={setThemeMode} />
    </div>
  );
}

export default AppLayout;
