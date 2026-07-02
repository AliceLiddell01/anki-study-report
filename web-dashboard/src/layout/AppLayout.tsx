import type { ReactNode } from "react";
import type { RoutePath } from "../app/router";
import { useThemePreference } from "../lib/theme";
import TopNav from "./TopNav";

function AppLayout({ activeRoute, children }: { activeRoute: RoutePath; children: ReactNode }) {
  useThemePreference();

  return (
    <div className="min-h-screen bg-ink-950 text-report-text">
      <TopNav activeRoute={activeRoute} />
      <main key={activeRoute} className="page-enter mx-auto w-full max-w-[1760px] px-4 py-5 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}

export default AppLayout;
