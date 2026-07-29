import { Bell, ChevronDown, Database, FileCheck2, FileText, FileType2, Plug, Server, ShieldCheck } from "lucide-react";
import {
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import type { RoutePath } from "../app/router";
import { SettingsRouteHeaderTargetProvider } from "./SettingsRouteHeader";

type SettingsItem = {
  path: RoutePath;
  labelKey: string;
  icon: typeof Database;
};

type SettingsSection = {
  labelKey: string;
  items: SettingsItem[];
};

export const settingsSections: SettingsSection[] = [
  {
    labelKey: "settings.reportGroup",
    items: [{ path: "/settings", labelKey: "settings.report", icon: FileType2 }],
  },
  {
    labelKey: "settings.dataGroup",
    items: [
      { path: "/settings/data", labelKey: "settings.data", icon: Database },
      { path: "/settings/inspection-profiles", labelKey: "settings.inspectionProfiles", icon: FileCheck2 },
      { path: "/settings/privacy", labelKey: "settings.privacy", icon: ShieldCheck },
    ],
  },
  {
    labelKey: "settings.systemGroup",
    items: [
      { path: "/settings/notifications", labelKey: "settings.notifications", icon: Bell },
      { path: "/settings/server", labelKey: "settings.server", icon: Server },
    ],
  },
  {
    labelKey: "settings.diagnosticsGroup",
    items: [
      { path: "/settings/sources", labelKey: "settings.sources", icon: Plug },
      { path: "/settings/logs", labelKey: "settings.logs", icon: FileText },
    ],
  },
];

const COMPACT_VISIBLE_SECTION_COUNT = 2;
const compactOverflowItems = settingsSections.slice(COMPACT_VISIBLE_SECTION_COUNT).flatMap((section) => section.items);
let pendingSettingsRouteFocus: RoutePath | null = null;
const useIsomorphicLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

function rememberKeyboardRouteFocus(event: ReactMouseEvent<HTMLAnchorElement>, path: RoutePath) {
  if (event.detail === 0) pendingSettingsRouteFocus = path;
}

function SettingsLayout({ activeRoute, children }: { activeRoute: RoutePath; children: ReactNode }) {
  const { t } = useTranslation("navigation");
  const [overflowOpen, setOverflowOpen] = useState(false);
  const [headerTarget] = useState<HTMLDivElement | null>(() => {
    if (typeof document === "undefined") return null;
    const node = document.createElement("div");
    node.className = "settings-route-header-portal";
    node.dataset.settingsRouteHeaderPortal = "true";
    return node;
  });
  const headerSlotRef = useRef<HTMLDivElement>(null);
  const overflowRootRef = useRef<HTMLDivElement>(null);
  const overflowTriggerRef = useRef<HTMLButtonElement>(null);
  const overflowMenuRef = useRef<HTMLDivElement>(null);
  const routeContentRef = useRef<HTMLDivElement>(null);
  const activeRouteIsInOverflow = compactOverflowItems.some((item) => item.path === activeRoute);

  useIsomorphicLayoutEffect(() => {
    if (!headerTarget || !headerSlotRef.current) return;
    headerSlotRef.current.append(headerTarget);
    return () => headerTarget.remove();
  }, [headerTarget]);

  useEffect(() => {
    setOverflowOpen(false);
  }, [activeRoute]);

  useEffect(() => {
    if (!overflowOpen) return;

    overflowMenuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();

    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!overflowRootRef.current?.contains(event.target as Node)) setOverflowOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      overflowTriggerRef.current?.focus();
      setOverflowOpen(false);
    };

    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [overflowOpen]);

  useEffect(() => {
    if (pendingSettingsRouteFocus !== activeRoute) return;

    const focusRouteHeading = () => {
      const target = headerSlotRef.current?.querySelector<HTMLElement>("h1")
        ?? routeContentRef.current?.querySelector<HTMLElement>("h1, h2, [role='heading']");
      if (!target) return false;

      pendingSettingsRouteFocus = null;
      const previousTabIndex = target.getAttribute("tabindex");
      const previousFocusKey = target.getAttribute("data-focus-key");
      target.setAttribute("tabindex", "-1");
      target.setAttribute("data-focus-key", "route-target");
      target.focus({ preventScroll: true });
      target.scrollIntoView?.({ block: "nearest" });

      target.addEventListener(
        "blur",
        () => {
          if (previousTabIndex === null) target.removeAttribute("tabindex");
          else target.setAttribute("tabindex", previousTabIndex);
          if (previousFocusKey === null) target.removeAttribute("data-focus-key");
          else target.setAttribute("data-focus-key", previousFocusKey);
        },
        { once: true },
      );
      return true;
    };

    if (focusRouteHeading()) return;

    const observer = new MutationObserver(() => {
      if (focusRouteHeading()) observer.disconnect();
    });
    if (headerTarget) observer.observe(headerTarget, { childList: true, subtree: true });
    if (routeContentRef.current) observer.observe(routeContentRef.current, { childList: true, subtree: true });

    return () => observer.disconnect();
  }, [activeRoute, headerTarget]);

  const focusOverflowItem = (direction: 1 | -1) => {
    const items = Array.from(overflowMenuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
    const currentIndex = items.indexOf(document.activeElement as HTMLElement);
    const nextIndex = currentIndex < 0 ? 0 : (currentIndex + direction + items.length) % items.length;
    items[nextIndex]?.focus();
  };

  return (
    <SettingsRouteHeaderTargetProvider target={headerTarget}>
      <div className="settings-layout-shell" data-testid="settings-layout-shell">
        <div
          ref={headerSlotRef}
          className="settings-route-header-slot"
          data-testid="settings-route-header-slot"
        />

        <aside className="settings-nav-shell" data-testid="settings-navigation-shell">
          <div className="settings-nav-intro">
            <p>{t("settings.title")}</p>
            <span>{t("settings.subtitle")}</span>
          </div>

          <div className="settings-nav-row">
            <nav className="settings-nav" aria-label={t("settings.title")} data-testid="settings-navigation">
              {settingsSections.map((section, sectionIndex) => (
                <div
                  key={section.labelKey}
                  className={[
                    "settings-nav-section",
                    sectionIndex >= COMPACT_VISIBLE_SECTION_COUNT ? "settings-nav-section--overflow" : "",
                  ].join(" ")}
                >
                  <p className="settings-nav-section-label">{t(section.labelKey)}</p>
                  <div className="settings-nav-links">
                    {section.items.map((item) => {
                      const Icon = item.icon;
                      const active = item.path === activeRoute;
                      return (
                        <a
                          key={item.path}
                          href={`#${item.path}`}
                          className="settings-nav-link"
                          aria-current={active ? "page" : undefined}
                          data-settings-nav-link={item.path}
                          onClick={(event) => rememberKeyboardRouteFocus(event, item.path)}
                        >
                          <Icon size={16} aria-hidden="true" />
                          <span>{t(item.labelKey)}</span>
                        </a>
                      );
                    })}
                  </div>
                </div>
              ))}
            </nav>

            <div className="settings-nav-overflow" ref={overflowRootRef} data-testid="settings-overflow-root">
              <button
                ref={overflowTriggerRef}
                type="button"
                className="settings-nav-overflow-trigger"
                aria-label={t("settings.more")}
                aria-haspopup="menu"
                aria-expanded={overflowOpen}
                aria-controls={overflowOpen ? "settings-nav-overflow-menu" : undefined}
                data-active-route={activeRouteIsInOverflow ? "true" : "false"}
                data-testid="settings-overflow-trigger"
                onClick={() => setOverflowOpen((current) => !current)}
                onKeyDown={(event) => {
                  if (event.key !== "ArrowDown") return;
                  event.preventDefault();
                  setOverflowOpen(true);
                }}
              >
                <span>{t("settings.more")}</span>
                <ChevronDown size={14} aria-hidden="true" className={overflowOpen ? "is-open" : ""} />
              </button>

              {overflowOpen ? (
                <div
                  ref={overflowMenuRef}
                  id="settings-nav-overflow-menu"
                  role="menu"
                  aria-label={t("settings.additionalSections")}
                  className="settings-nav-overflow-menu popover-motion"
                  data-testid="settings-overflow-menu"
                  onKeyDown={(event) => {
                    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                      event.preventDefault();
                      focusOverflowItem(event.key === "ArrowDown" ? 1 : -1);
                    }
                    if (event.key === "Home" || event.key === "End") {
                      event.preventDefault();
                      const items = overflowMenuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]');
                      items?.[event.key === "Home" ? 0 : items.length - 1]?.focus();
                    }
                  }}
                >
                  {compactOverflowItems.map((item) => {
                    const Icon = item.icon;
                    const active = item.path === activeRoute;
                    return (
                      <a
                        key={item.path}
                        href={`#${item.path}`}
                        role="menuitem"
                        className="settings-nav-overflow-link"
                        aria-current={active ? "page" : undefined}
                        data-settings-overflow-link={item.path}
                        onClick={() => {
                          pendingSettingsRouteFocus = item.path;
                          setOverflowOpen(false);
                        }}
                      >
                        <Icon size={16} aria-hidden="true" />
                        <span>{t(item.labelKey)}</span>
                      </a>
                    );
                  })}
                </div>
              ) : null}
            </div>
          </div>
        </aside>

        <div ref={routeContentRef} className="settings-route-content" data-testid="settings-route-content">
          {children}
        </div>
      </div>
    </SettingsRouteHeaderTargetProvider>
  );
}

export default SettingsLayout;
