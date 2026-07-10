import { Database, FileText, FileType2, Plug, Server } from "lucide-react";
import type { ReactNode } from "react";
import type { RoutePath } from "../app/router";

export const settingsSections: Array<{
  label: string;
  items: Array<{ path: RoutePath; label: string; icon: typeof Database }>;
}> = [
  {
    label: "Отчёт",
    items: [{ path: "/settings", label: "Отчёт", icon: FileType2 }],
  },
  {
    label: "Данные",
    items: [{ path: "/settings/data", label: "Данные", icon: Database }],
  },
  {
    label: "Система",
    items: [{ path: "/settings/server", label: "Сервер", icon: Server }],
  },
  {
    label: "Диагностика",
    items: [
      { path: "/settings/sources", label: "Источники данных", icon: Plug },
      { path: "/settings/logs", label: "Логи", icon: FileText },
    ],
  },
];

function SettingsLayout({ activeRoute, children }: { activeRoute: RoutePath; children: ReactNode }) {
  return (
    <div className="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)] lg:items-start">
      <aside className="settings-nav-shell rounded-xl border border-ink-700 bg-ink-850 p-3 shadow-panel lg:sticky lg:top-[88px]">
        <div className="px-2 pb-3 pt-1">
          <p className="text-base font-semibold text-report-text">Настройки</p>
          <p className="mt-1 text-xs leading-5 text-report-muted">Отчёт, данные, система и диагностика</p>
        </div>
        <nav className="grid gap-3" aria-label="Настройки">
          {settingsSections.map((section) => (
            <div key={section.label}>
              <p className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-report-muted">
                {section.label}
              </p>
              <div className="grid gap-1">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const active = item.path === activeRoute;
                  return (
                    <a
                      key={item.path}
                      href={`#${item.path}`}
                      className={[
                        "flex min-h-10 items-center gap-2.5 rounded-lg border px-2.5 py-2 text-sm font-medium outline-none transition focus:ring-2 focus:ring-report-blue/55",
                        active
                          ? "border-report-blue/60 bg-report-blue/15 text-report-text"
                          : "border-transparent text-report-secondary hover:border-ink-700 hover:bg-ink-900/55 hover:text-report-text",
                      ].join(" ")}
                      aria-current={active ? "page" : undefined}
                    >
                      <Icon size={16} aria-hidden="true" />
                      {item.label}
                    </a>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export default SettingsLayout;
