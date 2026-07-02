import { useEffect, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "anki-study-report-theme";
const THEME_CHANGE_EVENT = "anki-study-report-theme-change";

export function isThemeMode(value: unknown): value is ThemeMode {
  return value === "light" || value === "dark" || value === "system";
}

export function getStoredThemeMode(): ThemeMode {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemeMode(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

export function getSystemTheme(): ResolvedTheme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function resolveTheme(mode: ThemeMode): ResolvedTheme {
  return mode === "system" ? getSystemTheme() : mode;
}

export function applyTheme(resolvedTheme: ResolvedTheme): void {
  document.documentElement.dataset.theme = resolvedTheme;
  document.documentElement.style.colorScheme = resolvedTheme;
}

export function useThemePreference(): {
  themeMode: ThemeMode;
  resolvedTheme: ResolvedTheme;
  setThemeMode: (mode: ThemeMode) => void;
} {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => getStoredThemeMode());
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => resolveTheme(getStoredThemeMode()));

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const syncMode = () => {
      const nextMode = getStoredThemeMode();
      setThemeModeState(nextMode);
      const resolved = resolveTheme(nextMode);
      setResolvedTheme(resolved);
      applyTheme(resolved);
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key === THEME_STORAGE_KEY) {
        syncMode();
      }
    };
    const update = () => {
      const resolved = resolveTheme(themeMode);
      setResolvedTheme(resolved);
      applyTheme(resolved);
    };
    update();
    media.addEventListener("change", update);
    window.addEventListener(THEME_CHANGE_EVENT, syncMode);
    window.addEventListener("storage", onStorage);
    return () => {
      media.removeEventListener("change", update);
      window.removeEventListener(THEME_CHANGE_EVENT, syncMode);
      window.removeEventListener("storage", onStorage);
    };
  }, [themeMode]);

  const setThemeMode = (mode: ThemeMode) => {
    setThemeModeState(mode);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, mode);
    } catch {
      // The dashboard still applies the selected theme for this session.
    }
    const resolved = resolveTheme(mode);
    setResolvedTheme(resolved);
    applyTheme(resolved);
    window.dispatchEvent(new CustomEvent(THEME_CHANGE_EVENT));
  };

  return { themeMode, resolvedTheme, setThemeMode };
}
