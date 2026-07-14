export const LANGUAGE_STORAGE_KEY = "anki-study-report-language";
export const LANGUAGE_CHANGE_EVENT = "anki-study-report-language-change";

export const supportedLanguages = ["ru", "en"] as const;
export type AppLanguage = (typeof supportedLanguages)[number];

export function normalizeLanguage(value: unknown): AppLanguage {
  return value === "en" || value === "ru" ? value : "ru";
}

export function readLanguagePreference(): AppLanguage {
  if (typeof window === "undefined") return "ru";
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    const language = normalizeLanguage(stored);
    if (stored !== null && stored !== language) window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    return language;
  } catch {
    return "ru";
  }
}

export function persistLanguagePreference(language: AppLanguage): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    // The active i18n instance still changes for this browser session.
  }
  window.dispatchEvent(new CustomEvent(LANGUAGE_CHANGE_EVENT, { detail: language }));
}

export function applyDocumentLanguage(language: AppLanguage, title: string): void {
  if (typeof document === "undefined") return;
  document.documentElement.lang = language;
  document.documentElement.dir = "ltr";
  document.title = title;
}

export function subscribeLanguagePreference(callback: (language: AppLanguage) => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  const onStorage = (event: StorageEvent) => {
    if (event.key === LANGUAGE_STORAGE_KEY) callback(normalizeLanguage(event.newValue));
  };
  const onCustom = (event: Event) => callback(normalizeLanguage((event as CustomEvent).detail));
  window.addEventListener("storage", onStorage);
  window.addEventListener(LANGUAGE_CHANGE_EVENT, onCustom);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(LANGUAGE_CHANGE_EVENT, onCustom);
  };
}

export function localeForLanguage(language: string): "ru-RU" | "en-US" {
  return normalizeLanguage(language) === "en" ? "en-US" : "ru-RU";
}
