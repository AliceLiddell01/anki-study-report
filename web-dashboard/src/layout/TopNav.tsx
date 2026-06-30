import { Brain } from "lucide-react";
import type { RoutePath } from "../app/router";
import { navItems } from "../app/router";

function TopNav({ activeRoute }: { activeRoute: RoutePath }) {
  return (
    <header className="sticky top-0 z-20 border-b border-ink-700/80 bg-ink-950/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-[1760px] flex-col gap-3 px-4 py-3 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <a href="#/home" className="flex min-w-0 items-center gap-3 text-report-text">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-report-blue/35 bg-report-blue/10 text-report-blue">
            <Brain size={19} aria-hidden="true" />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold tracking-normal sm:text-base">Anki Study Report</span>
            <span className="block truncate text-xs text-report-muted">Local study portal</span>
          </span>
        </a>
        <nav className="flex gap-1 overflow-x-auto pb-1 lg:justify-end lg:pb-0" aria-label="Main navigation">
          {navItems.map((item) => {
            const active = item.path === activeRoute;
            return (
              <a
                key={item.path}
                href={`#${item.path}`}
                className={[
                  "whitespace-nowrap rounded-lg border px-3 py-2 text-sm font-medium transition",
                  active
                    ? "border-report-blue/60 bg-report-blue/15 text-report-blue"
                    : "border-transparent text-report-muted hover:border-ink-700 hover:bg-ink-850 hover:text-report-text",
                ].join(" ")}
                aria-current={active ? "page" : undefined}
              >
                {item.label}
              </a>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

export default TopNav;
