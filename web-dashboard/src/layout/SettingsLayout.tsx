import { Database, FileText, FileType2, Plug, Server } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { RoutePath } from "../app/router";

export const settingsSections: Array<{
  labelKey: string;
  items: Array<{ path: RoutePath; labelKey: string; icon: typeof Database }>;
}> = [
  {
    labelKey: "settings.reportGroup",
    items: [{ path: "/settings", labelKey: "settings.report", icon: FileType2 }],
  },
  {
    labelKey: "settings.dataGroup",
    items: [{ path: "/settings/data", labelKey: "settings.data", icon: Database }],
  },
  {
    labelKey: "settings.systemGroup",
    items: [{ path: "/settings/server", labelKey: "settings.server", icon: Server }],
  },
  {
    labelKey: "settings.diagnosticsGroup",
    items: [
      { path: "/settings/sources", labelKey: "settings.sources", icon: Plug },
      { path: "/settings/logs", labelKey: "settings.logs", icon: FileText },
    ],
  },
];

function SettingsLayout({ activeRoute, children }: { activeRoute: RoutePath; children: ReactNode }) {
  const { t } = useTranslation("navigation");
  return (
    <div className="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)] lg:items-start">
      <aside className="settings-nav-shell rounded-xl border border-ink-700 bg-ink-850 p-3 shadow-panel lg:sticky lg:top-[88px]">
        <div className="px-2 pb-3 pt-1">
          <p className="text-base font-semibold text-report-text">{t("settings.title")}</p>
          <p className="mt-1 text-xs leading-5 text-report-muted">{t("settings.subtitle")}</p>
        </div>
        <nav className="grid gap-3" aria-label={t("settings.title")}>
          {settingsSections.map((section) => (
            <div key={section.labelKey}>
              <p className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-report-muted">
                {t(section.labelKey)}
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
                      {t(item.labelKey)}
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
