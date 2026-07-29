import i18n from "../i18n";
import type { CardDisplayIdentity } from "../types/search";

const FALLBACKS = {
  ru: {
    media_only: "Карточка только с медиа",
    unavailable: "Текст карточки недоступен",
  },
  en: {
    media_only: "Card with media only",
    unavailable: "Card text unavailable",
  },
} as const;

export function cardDisplayText(identity: CardDisplayIdentity): string {
  if (identity.displayStatus === "available") return identity.displayText;
  const language = String(i18n.resolvedLanguage || i18n.language).toLowerCase().startsWith("en") ? "en" : "ru";
  return FALLBACKS[language][identity.displayStatus];
}
