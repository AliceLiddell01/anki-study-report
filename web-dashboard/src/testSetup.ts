import { beforeEach } from "vitest";
import i18n from "./i18n";

beforeEach(async () => {
  await i18n.changeLanguage("ru");
  if (typeof window !== "undefined") window.localStorage.clear();
});
