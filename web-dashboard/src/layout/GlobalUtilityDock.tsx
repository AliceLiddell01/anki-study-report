import { Check, Languages, Moon, Sun } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { changeAppLanguage, currentAppLanguage } from "../i18n";
import type { AppLanguage } from "../i18n/language";
import type { ResolvedTheme } from "../lib/theme";

const languageOptions: Array<{ code: AppLanguage; labelKey: string }> = [
  { code: "ru", labelKey: "utility.russian" },
  { code: "en", labelKey: "utility.english" },
];

function GlobalUtilityDock({
  resolvedTheme,
  onThemeChange,
}: {
  resolvedTheme: ResolvedTheme;
  onThemeChange: (theme: ResolvedTheme) => void;
}) {
  const { t, i18n } = useTranslation(["pages", "common"]);
  const [languageMenuOpen, setLanguageMenuOpen] = useState(false);
  const languageControlRef = useRef<HTMLDivElement>(null);
  const languageTriggerRef = useRef<HTMLButtonElement>(null);
  const nextTheme: ResolvedTheme = resolvedTheme === "dark" ? "light" : "dark";
  const themeLabel = nextTheme === "light" ? t("utility.enableLight") : t("utility.enableDark");
  const Icon = nextTheme === "light" ? Sun : Moon;
  const activeLanguage = currentAppLanguage();

  useEffect(() => {
    if (!languageMenuOpen) return;
    languageControlRef.current?.querySelector<HTMLElement>(`[data-language="${activeLanguage}"]`)?.focus();
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (!languageControlRef.current?.contains(event.target as Node)) setLanguageMenuOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setLanguageMenuOpen(false);
      languageTriggerRef.current?.focus();
    };
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [activeLanguage, languageMenuOpen]);

  const focusLanguage = (direction: 1 | -1) => {
    const items = Array.from(languageControlRef.current?.querySelectorAll<HTMLElement>('[role="menuitemradio"]') ?? []);
    const index = items.indexOf(document.activeElement as HTMLElement);
    items[(index < 0 ? 0 : index + direction + items.length) % items.length]?.focus();
  };

  const selectLanguage = async (language: AppLanguage) => {
    await changeAppLanguage(language);
    setLanguageMenuOpen(false);
    languageTriggerRef.current?.focus();
  };

  return (
    <aside className="global-utility-dock" aria-label={t("utility.ariaLabel")} data-testid="global-utility-dock">
      <div className="utility-control-with-tooltip" ref={languageControlRef}>
        <button
          ref={languageTriggerRef}
          type="button"
          className="utility-icon-button utility-language-button"
          aria-label={t("utility.languageButton")}
          aria-haspopup="menu"
          aria-expanded={languageMenuOpen}
          aria-controls="language-selector-menu"
          aria-describedby={languageMenuOpen ? undefined : "language-selector-tooltip"}
          data-testid="language-selector"
          onClick={() => setLanguageMenuOpen((open) => !open)}
          onKeyDown={(event) => {
            if (event.key === "ArrowUp" || event.key === "ArrowDown") {
              event.preventDefault();
              setLanguageMenuOpen(true);
            }
          }}
        >
          <Languages size={18} aria-hidden="true" />
          <span aria-hidden="true">{activeLanguage.toUpperCase()}</span>
        </button>
        {!languageMenuOpen ? (
          <span id="language-selector-tooltip" role="tooltip" className="utility-tooltip">{t("utility.languageButton")}</span>
        ) : null}
        {languageMenuOpen ? (
          <div
            id="language-selector-menu"
            className="utility-language-menu popover-motion"
            role="menu"
            aria-label={t("utility.languageMenu")}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault();
                focusLanguage(event.key === "ArrowDown" ? 1 : -1);
              }
              if (event.key === "Home" || event.key === "End") {
                event.preventDefault();
                const items = languageControlRef.current?.querySelectorAll<HTMLElement>('[role="menuitemradio"]');
                items?.[event.key === "Home" ? 0 : items.length - 1]?.focus();
              }
            }}
          >
            {languageOptions.map((option) => (
              <button
                key={option.code}
                type="button"
                role="menuitemradio"
                aria-checked={activeLanguage === option.code}
                data-language={option.code}
                onClick={() => void selectLanguage(option.code)}
              >
                <span>{t(option.labelKey)}</span>
                {activeLanguage === option.code ? <Check size={15} aria-hidden="true" /> : null}
              </button>
            ))}
          </div>
        ) : null}
      </div>
      <div className="utility-control-with-tooltip">
        <button
          type="button"
          className="utility-icon-button"
          aria-label={themeLabel}
          aria-describedby="theme-toggle-tooltip"
          data-testid="theme-toggle"
          onClick={() => onThemeChange(nextTheme)}
        >
          <Icon size={19} aria-hidden="true" />
        </button>
        <span id="theme-toggle-tooltip" role="tooltip" className="utility-tooltip">{themeLabel}</span>
      </div>
    </aside>
  );
}

export default GlobalUtilityDock;
