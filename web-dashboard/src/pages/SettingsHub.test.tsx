import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import ProfilePage from "./ProfilePage";
import ReportSettingsPage from "./ReportSettingsPage";
import SettingsPage from "./SettingsPage";

describe("Settings Hub pages", () => {
  it("renders report settings with disabled save and dependent deck selector initially", () => {
    const markup = renderToStaticMarkup(<ReportSettingsPage />);

    expect(markup).toContain("Страница «Сегодня» всегда показывает текущий локальный день");
    expect(markup).toContain("Отчёт Anki");
    expect(markup).toMatch(/id="dashboard-decks"[^>]*disabled/);
    expect(markup).toMatch(/disabled=""[^>]*>Сохранить изменения|disabled[^>]*>Сохранить изменения/);
  });

  it("disables session timeout fields while tracking is off", () => {
    const markup = renderToStaticMarkup(<SettingsPage report={null} />);

    expect(markup).toContain(">Данные</h1>");
    expect(markup).toMatch(/id="session-idle"[^>]*disabled/);
    expect(markup).toMatch(/id="session-gap"[^>]*disabled/);
    expect(markup).toContain("Перестроить кэш");
  });

  it("renders the Profile MVP fallback without transitional settings copy", () => {
    const markup = renderToStaticMarkup(<ProfilePage report={null} />);

    expect(markup).toContain("Пользователь Anki");
    expect(markup).toContain("Локальный профиль");
    expect(markup).toContain("Изменить дату начала");
    expect(markup).not.toContain("переходный read-only экран");
    expect(markup).not.toContain('href="#/settings"');
  });
});
