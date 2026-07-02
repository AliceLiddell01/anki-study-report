import { Brain } from "lucide-react";
import type { RoutePath } from "../app/router";
import { navItems } from "../app/router";

function TopNav({ activeRoute }: { activeRoute: RoutePath }) {
  const groups = ["Основное", "Аналитика", "Инструменты", "Система"] as const;

  return (
    <header className="topbar-surface sticky top-0 z-20 border-b border-ink-700/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-[1760px] flex-col gap-3 px-4 py-3 sm:px-6 lg:min-h-[68px] lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <a href="#/home" className="flex min-w-0 items-center gap-3 py-0.5 text-report-text">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-report-blue/35 bg-report-blue/10 text-report-blue">
            <Brain size={19} aria-hidden="true" />
          </span>
          <span className="min-w-0 leading-none">
            <span className="block truncate text-sm font-semibold leading-5 tracking-normal sm:text-base">Anki Study Report</span>
            <span className="block whitespace-nowrap text-xs leading-5 text-report-muted">Локальный учебный портал</span>
          </span>
        </a>
        <nav className="flex gap-4 overflow-x-auto pb-1 lg:justify-end lg:pb-0" aria-label="Основная навигация">
          {groups.map((group) => (
            <div key={group} className="flex shrink-0 items-center gap-1">
              <span className="topbar-link-muted hidden px-1.5 text-[11px] font-medium uppercase xl:inline">{group}</span>
              {navItems.filter((item) => item.group === group).map((item) => {
                const active = item.path === activeRoute;
                return (
                  <a
                    key={item.path}
                    href={`#${item.path}`}
                    className={[
                      "whitespace-nowrap rounded-lg border px-3.5 py-2 text-sm font-medium transition",
                      active
                        ? "border-report-blue/75 bg-report-blue/15 text-report-text shadow-glow"
                        : "topbar-link-muted border-transparent hover:border-ink-700/80 hover:bg-ink-900/55 hover:text-report-text",
                    ].join(" ")}
                    aria-current={active ? "page" : undefined}
                  >
                    {item.label}
                  </a>
                );
              })}
            </div>
          ))}
        </nav>
      </div>
    </header>
  );
}

export default TopNav;
