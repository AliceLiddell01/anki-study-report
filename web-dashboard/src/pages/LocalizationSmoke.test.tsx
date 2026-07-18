// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import i18n from "../i18n";
import { mockReport } from "../data/mockReport";
import CardsPage from "./CardsPage";
import ActionsPage from "./ActionsPage";
import CalendarPage from "./CalendarPage";
import DecksPage from "./DecksPage";
import FsrsStatisticsPage from "./FsrsStatisticsPage";
import HomePage from "./HomePage";
import ProfilePage from "./ProfilePage";
import StatisticsPage from "./StatisticsPage";

describe("representative localized pages", () => {
  it("renders Russian product labels without known English residue", async () => {
    await i18n.changeLanguage("ru");
    const today = renderToStaticMarkup(<HomePage report={mockReport} loadState="ready" />);
    const activity = renderToStaticMarkup(<CalendarPage report={mockReport} loadState="ready" />);
    const decks = renderToStaticMarkup(<DecksPage report={mockReport} loadState="ready" />);

    expect(today).toContain("Успешно/Ошибка");
    expect(today).toContain("Перепланирование:");
    expect(today).toContain("Автораспределение:");
    expect(today).not.toContain(">Pass<");
    expect(today).not.toContain(">Fail<");
    expect(today).not.toContain("reschedule ");
    expect(today).not.toContain("auto disperse");
    expect(activity).toContain("Успешно");
    expect(activity).toContain("Ошибка");
    expect(decks).toContain("Успешно");
  });

  it("renders English shell copy on Today, Statistics, and Cards", async () => {
    await i18n.changeLanguage("en");
    const today = renderToStaticMarkup(<HomePage report={mockReport} loadState="ready" />);
    const statistics = renderToStaticMarkup(<StatisticsPage report={mockReport} loadState="ready" section="overview" />);
    const cards = renderToStaticMarkup(<CardsPage report={mockReport} loadState="ready" />);

    expect(today).toContain("Today");
    expect(today).toContain("Answer quality");
    expect(today).toContain("estimated from revlog");
    expect(statistics).toContain("Personal analytics center");
    expect(statistics).toContain("Key metrics");
    expect(cards).toContain("Cards");
    expect(cards).toContain("Cards needing attention");
    expect(cards).toContain("Attention queue");
  });

  it("renders English copy on Activity, Decks, Profile, Tools, and FSRS", async () => {
    await i18n.changeLanguage("en");
    const activity = renderToStaticMarkup(<CalendarPage report={mockReport} loadState="ready" />);
    const decks = renderToStaticMarkup(<DecksPage report={mockReport} loadState="ready" />);
    const profile = renderToStaticMarkup(<ProfilePage report={mockReport} />);
    const actions = renderToStaticMarkup(<ActionsPage report={mockReport} loadState="ready" />);
    const fsrs = renderToStaticMarkup(<FsrsStatisticsPage report={mockReport} loadState="ready" section="overview" />);

    expect(activity).toContain("Activity");
    expect(decks).toContain("Decks");
    expect(profile).toContain("Learning journey");
    expect(profile).toContain("Local profile");
    expect(profile).not.toContain("Локальный профиль");
    expect(actions).toContain("Tools");
    expect(fsrs).toContain("How is FSRS working for me right now?");
    expect(fsrs).toContain("Open deck options");
    expect(fsrs).not.toContain("shell.fsrs");
  });
});
