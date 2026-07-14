import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en";
import ru from "./locales/ru";
import {
  applyDocumentLanguage,
  normalizeLanguage,
  persistLanguagePreference,
  readLanguagePreference,
  subscribeLanguagePreference,
  type AppLanguage,
} from "./language";

export const resources = { ru, en } as const;

void i18n.use(initReactI18next).init({
  resources,
  lng: readLanguagePreference(),
  fallbackLng: "ru",
  defaultNS: "common",
  supportedLngs: ["ru", "en"],
  interpolation: { escapeValue: false },
  initAsync: false,
  returnNull: false,
});

function syncDocument(language: string) {
  const normalized = normalizeLanguage(language);
  applyDocumentLanguage(normalized, i18n.getFixedT(normalized, "common")("app.title"));
}

syncDocument(i18n.language);
i18n.on("languageChanged", syncDocument);
subscribeLanguagePreference((language) => {
  if (normalizeLanguage(i18n.language) !== language) void i18n.changeLanguage(language);
});

export function changeAppLanguage(language: AppLanguage): Promise<unknown> {
  persistLanguagePreference(language);
  return i18n.changeLanguage(language);
}

export function currentAppLanguage(): AppLanguage {
  return normalizeLanguage(i18n.resolvedLanguage || i18n.language);
}

export default i18n;
