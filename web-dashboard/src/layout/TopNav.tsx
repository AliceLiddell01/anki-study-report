import { Brain, ChevronDown, Heart, Settings, UserRound, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { RoutePath } from "../app/router";
import { primaryNavItems } from "../app/router";

const BOOSTY_SUPPORT_URL = "https://boosty.to/ankistudyreport";

type ProfileMenuItem = {
  label: string;
  icon: typeof UserRound;
} & (
  | { path: RoutePath; externalHref?: never }
  | { path?: never; externalHref: string }
);

const profileMenuSections: Array<{
  label: string;
  items: ProfileMenuItem[];
}> = [
  {
    label: "Личное меню",
    items: [
      { path: "/profile", label: "Профиль", icon: UserRound },
      { path: "/settings", label: "Настройки", icon: Settings },
    ],
  },
  {
    label: "Утилиты",
    items: [
      { path: "/actions", label: "Инструменты", icon: Wrench },
      { externalHref: BOOSTY_SUPPORT_URL, label: "Поддержать проект", icon: Heart },
    ],
  },
];

function TopNav({ activeRoute }: { activeRoute: RoutePath }) {
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const profileTriggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setProfileMenuOpen(false);
  }, [activeRoute]);

  useEffect(() => {
    if (!profileMenuOpen) {
      return;
    }

    profileMenuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();

    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!profileMenuRef.current?.contains(event.target as Node)) {
        setProfileMenuOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setProfileMenuOpen(false);
        profileTriggerRef.current?.focus();
      }
    };

    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [profileMenuOpen]);

  const focusMenuItem = (direction: 1 | -1) => {
    const items = Array.from(profileMenuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
    const currentIndex = items.indexOf(document.activeElement as HTMLElement);
    const nextIndex = currentIndex < 0 ? 0 : (currentIndex + direction + items.length) % items.length;
    items[nextIndex]?.focus();
  };

  return (
    <header className="topbar-surface sticky top-0 z-40 border-b border-ink-700/80 backdrop-blur">
      <div className="mx-auto flex min-h-[68px] w-full max-w-[1760px] items-center gap-6 px-4 py-3 sm:px-6 lg:px-8">
        <a href="#/home" className="flex min-w-0 shrink-0 items-center gap-3 py-0.5 text-report-text">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-report-blue/35 bg-report-blue/10 text-report-blue">
            <Brain size={19} aria-hidden="true" />
          </span>
          <span className="hidden min-w-0 leading-none sm:block">
            <span className="block truncate text-sm font-semibold leading-5 tracking-normal xl:text-base">Anki Study Report</span>
            <span className="block whitespace-nowrap text-xs leading-5 text-report-muted">Локальный учебный портал</span>
          </span>
        </a>

        <nav className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto" aria-label="Основная навигация">
          {primaryNavItems.map((item) => {
            const active = item.path === activeRoute || (item.path === "/stats" && activeRoute.startsWith("/stats/"));
            return (
              <a
                key={item.path}
                href={`#${item.path}`}
                className={[
                  "shrink-0 whitespace-nowrap rounded-lg border px-3.5 py-2 text-sm font-medium transition",
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
        </nav>

        <div className="relative shrink-0" ref={profileMenuRef}>
          <button
            ref={profileTriggerRef}
            type="button"
            className={[
              "inline-flex min-h-11 items-center gap-2 rounded-xl border px-2 py-1.5 text-sm font-medium text-report-text transition",
              profileMenuOpen || activeRoute === "/profile"
                ? "border-report-blue/70 bg-report-blue/15 shadow-glow"
                : "border-ink-700 bg-ink-850 hover:border-report-blue/45 hover:bg-ink-800",
            ].join(" ")}
            aria-label="Открыть меню профиля"
            aria-haspopup="menu"
            aria-expanded={profileMenuOpen}
            aria-controls="profile-menu"
            onClick={() => setProfileMenuOpen((current) => !current)}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setProfileMenuOpen(true);
              }
            }}
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-report-blue/35 bg-report-blue/10 text-report-blue">
              <UserRound size={17} aria-hidden="true" />
            </span>
            <span className="hidden sm:inline">Профиль</span>
            <ChevronDown
              size={15}
              aria-hidden="true"
              className={`hidden text-report-muted transition-transform sm:block ${profileMenuOpen ? "rotate-180" : ""}`}
            />
          </button>

          {profileMenuOpen ? (
            <div
              id="profile-menu"
              role="menu"
              aria-label="Меню профиля"
              className="popover-motion absolute right-0 top-[calc(100%+0.65rem)] z-50 w-64 overflow-hidden rounded-xl border border-ink-700 bg-ink-850 p-2 shadow-[var(--shadow-popover)]"
              onKeyDown={(event) => {
                if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                  event.preventDefault();
                  focusMenuItem(event.key === "ArrowDown" ? 1 : -1);
                }
                if (event.key === "Home" || event.key === "End") {
                  event.preventDefault();
                  const items = profileMenuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]');
                  items?.[event.key === "Home" ? 0 : items.length - 1]?.focus();
                }
              }}
            >
              {profileMenuSections.map((section, sectionIndex) => (
                <div
                  key={section.label}
                  role="group"
                  aria-label={section.label}
                  className={sectionIndex > 0 ? "mt-2 border-t border-ink-700/80 pt-2" : ""}
                >
                  {section.items.map((item) => {
                    const Icon = item.icon;
                    const active = "path" in item && item.path === activeRoute;
                    const href = "path" in item ? `#${item.path}` : item.externalHref;
                    return (
                      <a
                        key={href}
                        href={href}
                        role="menuitem"
                        target={"externalHref" in item ? "_blank" : undefined}
                        rel={"externalHref" in item ? "noopener noreferrer" : undefined}
                        referrerPolicy={"externalHref" in item ? "no-referrer" : undefined}
                        className={[
                          "flex min-h-11 items-center gap-3 rounded-lg border px-3 py-2 text-sm font-medium outline-none transition",
                          active
                            ? "border-report-blue/45 bg-report-blue/15 text-report-text"
                            : "border-transparent text-report-secondary hover:bg-ink-800 hover:text-report-text focus:border-report-blue/45 focus:bg-ink-800 focus:text-report-text",
                        ].join(" ")}
                        onClick={() => setProfileMenuOpen(false)}
                      >
                        <Icon size={17} className="text-report-blue" aria-hidden="true" />
                        {item.label}
                      </a>
                    );
                  })}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}

export default TopNav;
